# -*- coding: utf-8 -*-
"""Store extension repository credentials so no secret reaches the config in the clear.

One extension has one credential, and this module is the only thing that reads or
writes it. It lives in the extension's own config section (``MyTool.extension``)
under a single key:

.. code-block:: ini

    [MyTool.extension]
    private_repo = true
    credential = "<base64 of a DPAPI-sealed blob>"

Examples:
    ```python
    from pyrevit.coreutils import credentials

    credentials.set_credential("MyTool.extension", "oauth2", token)
    cred = credentials.get_credential("MyTool.extension")
    git.git_clone(url, dest, username=cred.username, password=cred.secret)
    ```

Why a single key, and why the username inside it: the alternative - a plaintext
``token``/``password``/``username`` triple per extension - is what a migration has
to clear up, and every way of doing that can remove a secret while leaving the
username that gave it meaning, which breaks authentication permanently and
silently. One blob means clearing a credential is always one key removal, and
there is no half-migrated state to reason about.

**The crypto lives in C#, not here.** This module owns the config contract and
the migration; the sealing itself is
``pyRevitLabs.Configurations.Security.ExtensionCredentialProtector``, in the
assembly that already backs the user config service. The only thing the two
sides share is the *stored format*: three base64 fields joined with ``'.'``, a
separator the base64 alphabet cannot contain, UTF-8 encoded and sealed with DPAPI
against the current Windows user under a fixed entropy. That is what lets the
out-of-Revit CLI store a credential the in-Revit extension manager can read, and
the reverse. Changing the format on one side alone orphans every stored
credential, so the two must change together.

**Scope is the current Windows user.** The blob survives pyRevit upgrades and
config backups, and is unreadable after an OS reinstall without a profile
backup, on another machine, and under another account. That is the trade for a
secret that is not sitting in a file every local user can read: a lost profile
means re-entering the token. :func:`get_credential` therefore reports that case
as :class:`PyRevitCredentialUnavailable` rather than returning ``None``, so a
caller can tell "re-enter your token" from "this extension needs no token" and
fail with a message about the credential instead of letting libgit2 fall back to
an anonymous fetch.

Note:
    Nothing here is reachable from a non-Windows runtime; :func:`is_available`
    reports whether sealing works, and every entry point degrades to a logged
    no-op rather than raising at import time, so importing this module from
    :mod:`pyrevit.versionmgr.updater` can never take the updater down.
"""

from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)

__all__ = [
    "ExtensionCredential",
    "PyRevitCredentialError",
    "PyRevitCredentialUnavailable",
    "PyRevitCredentialStoreReadOnly",
    "delete_credential",
    "get_credential",
    "has_credential",
    "is_available",
    "migrate_legacy_credentials",
    "set_credential",
]

#: Config key the sealed blob is stored under. Mirrors
#: ``ExtensionCredentialProtector.ConfigKeyName``.
CONFIG_KEY = "credential"

#: Plaintext keys written by pyRevit before credentials were sealed. Read only by
#: :func:`migrate_legacy_credentials`, which removes each one only after the
#: sealed value is stored and verified.
LEGACY_CREDENTIAL_KEYS = ("token", "password", "username")

#: Config sections belonging to an extension, by folder postfix.
EXTENSION_SECTION_POSTFIXES = (".extension", ".lib")

DEFAULT_TOKEN_USERNAME = "oauth2"

#: The credential shapes this module can store. Mirrors
#: ``ExtensionCredentialKind`` on the C# side; anything else is rejected on write
#: rather than coerced, so a password can never be recorded as a token.
CREDENTIAL_KINDS = ("token", "password")

#: The C# protector and the types it needs, resolved once.
_CRYPTO_HANDLES = None
_CRYPTO_LOAD_FAILED = False


# -----------------------------------------------------------------------------
# exceptions
# -----------------------------------------------------------------------------
class PyRevitCredentialError(Exception):
    """A credential could not be read or stored."""


class PyRevitCredentialUnavailable(PyRevitCredentialError):
    """A stored credential exists but cannot be decrypted.

    Important: never treat this as "no credential is configured". A fetch that
    answers with ``None`` here falls back to an anonymous request and surfaces as
    a libgit2 error about a missing authentication callback, which points at the
    wrong problem. The user has to re-enter their token; no local action recovers
    it.
    """


class PyRevitCredentialStoreReadOnly(PyRevitCredentialError):
    """A credential write was aimed at a read-only (admin-locked) config.

    Raised instead of silently dropping the value, because
    ``user_config.save_changes()`` is a no-op on a read-only config: reporting
    success there would leave the user believing a token is stored when it is not.
    """


class ExtensionCredential(object):
    """A username and secret for a private repository, recovered from storage.

    Attributes:
        username (str): account name to send with the secret
        secret (str): personal access token or password
        kind (str): ``"token"`` or ``"password"``, as stored
    """

    __slots__ = ("username", "secret", "kind")

    def __init__(self, username, secret, kind="token"):
        """Build a credential.

        Args:
            username (str): account name
            secret (str): token or password
            kind (str): ``"token"`` or ``"password"``
        """
        self.username = username
        self.secret = secret
        self.kind = kind

    def __repr__(self):
        # The secret is never rendered: this object ends up in tracebacks and log
        # lines, and a repr that leaked it would undo the whole module.
        return "ExtensionCredential(username={!r}, secret=<hidden>, kind={!r})".format(
            self.username, self.kind
        )


# -----------------------------------------------------------------------------
# crypto
# -----------------------------------------------------------------------------
def _load_crypto():
    """Resolve the C# protector, or None when sealing is unavailable.

    The crypto itself is not reimplemented here. It lives once, in
    ``ExtensionCredentialProtector``, which ships in
    ``pyRevitLabs.Configurations`` - the same assembly that backs the user config
    service, so it is already loaded by the time anything can store a
    credential. Reimplementing the Win32 DPAPI call in Python would mean a
    second copy of the byte-level format to keep in step with the first, and
    ``DATA_BLOB`` marshalling from IronPython is exactly the kind of thing that
    silently differs between engines.

    Cached because the lookup is process-wide and a failed one must not be
    retried per call.

    Returns:
        tuple or None: ``(protector, credential_type, kind_type)``
    """
    global _CRYPTO_HANDLES, _CRYPTO_LOAD_FAILED
    if _CRYPTO_HANDLES is not None or _CRYPTO_LOAD_FAILED:
        return _CRYPTO_HANDLES

    handles = _resolve_protector()
    if handles is None:
        _CRYPTO_LOAD_FAILED = True
        mlogger.warning(
            "credentials: the credential protector is not available on this "
            "runtime. Extension tokens will not be stored encrypted."
        )
        return None

    _CRYPTO_HANDLES = handles
    return _CRYPTO_HANDLES


def _resolve_protector():
    try:
        from pyrevit.framework import clr
    except Exception as load_err:
        mlogger.debug("credentials: no .NET runtime available (%s)", load_err)
        return None

    # Already loaded through the config service, so this is a no-op in practice;
    # it is here for the case where something imports this module first.
    try:
        clr.AddReference("pyRevitLabs.Configurations")
    except Exception as ref_err:
        mlogger.debug(
            "credentials: can not reference pyRevitLabs.Configurations (%s)", ref_err
        )

    try:
        from pyRevitLabs.Configurations.Security import (
            ExtensionCredential as NetCredential,
            ExtensionCredentialKind,
            ExtensionCredentialProtector,
        )
    except Exception as type_err:
        mlogger.debug(
            "credentials: ExtensionCredentialProtector is not loadable (%s)", type_err
        )
        return None

    return ExtensionCredentialProtector, NetCredential, ExtensionCredentialKind


def is_available():
    """Whether this runtime can seal and unseal a credential.

    Returns:
        (bool): False when the config is read-only, or when the DPAPI assembly
            could not be loaded. Callers that only need to *read* a credential
            should still try :func:`get_credential`; a False here is the common
            cause of a token silently never being stored.
    """
    if _load_crypto() is None:
        return False
    return not _is_readonly()


def _seal(username, secret, kind):
    """Seal a credential into a config value.

    Everything here stays in .NET types on purpose: ``str`` to ``byte[]`` goes
    through ``Encoding.UTF8.GetBytes`` and base64 through ``Convert``, because
    round-tripping a Python ``bytearray`` through IronPython 2's ``bytes`` yields
    the repr rather than the bytes.

    Args:
        username (str): account name
        secret (str): token or password
        kind (str): ``"token"`` or ``"password"``

    Returns:
        str: base64 config value

    Raises:
        PyRevitCredentialError: DPAPI is unavailable, or the fields are empty
    """
    handles = _load_crypto()
    if handles is None:
        raise PyRevitCredentialError(
            "Windows DPAPI is not available, so the credential cannot be encrypted."
        )
    protector, net_credential, kind_type = handles

    if not username or not str(username).strip():
        raise PyRevitCredentialError(
            "A credential username is required; every forge authenticates with a "
            "username and secret pair."
        )
    if not secret or not str(secret).strip():
        raise PyRevitCredentialError(
            "A credential secret is required; use delete_credential() to clear a "
            "stored one instead."
        )

    if kind not in CREDENTIAL_KINDS:
        # Silently defaulting to a token would store a password labelled as a
        # token, which is exactly the mislabelling the field exists to prevent.
        raise PyRevitCredentialError(
            "Unknown credential kind {!r}; expected one of {}.".format(
                kind, ", ".join(sorted(CREDENTIAL_KINDS))
            )
        )

    kind_enum = (
        getattr(kind_type, "Password")
        if kind == "password"
        else getattr(kind_type, "Token")
    )

    try:
        return protector.Protect(net_credential(str(username), str(secret), kind_enum))
    except Exception as seal_err:
        raise PyRevitCredentialError(
            "Could not encrypt the credential: {}".format(seal_err)
        )


def _unseal(stored_value):
    """Recover a credential from a config value.

    Args:
        stored_value (str): base64 config value

    Returns:
        ExtensionCredential: the recovered credential

    Raises:
        PyRevitCredentialUnavailable: the value cannot be turned back into a
            usable credential, for any reason
    """
    handles = _load_crypto()
    if handles is None:
        raise PyRevitCredentialUnavailable(
            "Windows DPAPI is not available on this runtime, so the stored "
            "extension credential cannot be read. Re-enter the access token."
        )
    protector, _net_credential, kind_type = handles

    if not stored_value or not str(stored_value).strip():
        raise PyRevitCredentialUnavailable(
            "No stored credential value to decrypt. Re-enter the access token."
        )

    try:
        recovered = protector.Unprotect(str(stored_value))
    except Exception as seal_err:
        raise PyRevitCredentialUnavailable(
            "The stored extension credential could not be decrypted. It was "
            "encrypted for a different Windows user or a different pyRevit "
            "version, or the config value was altered. Re-enter the access token "
            "for this extension. ({})".format(seal_err)
        )

    # Compare against the resolved enum member, not a substring of the CLR value's
    # string form. Some interop paths stringify an enum numerically, and a
    # substring test would then read every credential back as a token with nothing
    # failing.
    return ExtensionCredential(
        recovered.Username,
        recovered.Secret,
        "password" if recovered.Kind == kind_type.Password else "token",
    )


# -----------------------------------------------------------------------------
# config access
# -----------------------------------------------------------------------------
def _is_readonly():
    try:
        from pyrevit.userconfig import user_config

        return bool(user_config is not None and user_config.is_readonly)
    except Exception:
        return False


def _get_section(section_name, create=False):
    """Get an extension's config section.

    Args:
        section_name (str): extension config section name
        create (bool): create the section when it does not exist yet

    Returns:
        ConfigSection or None: the section, or None when it is absent and
            ``create`` is False
    """
    from pyrevit.userconfig import user_config

    if user_config is None:
        return None
    try:
        return user_config.get_section(section_name)
    except AttributeError:
        # get_section raises AttributeError for a missing section, which is also
        # how it reports a genuinely broken config; only creating is safe to
        # attempt, and only when asked.
        if create:
            return user_config.add_section(section_name)
        return None


def _save():
    from pyrevit.userconfig import user_config

    user_config.save_changes()


def _config_file_path():
    """Path of the config file the user config writes to, or None."""
    try:
        from pyrevit.userconfig import user_config

        return user_config.config_file
    except Exception:
        return None


def _read_from_disk(section_name):
    """Read the stored credential back off disk, bypassing the in-memory store.

    ``user_config.save_changes`` deliberately swallows a write failure and only
    logs it, so reading through the same in-memory ``ConfigSection`` that wrote
    the value proves nothing about durability: it would return the value even
    after the flush was dropped. Reopening the file is the only way to know the
    bytes actually landed, and that is the question a credential write has to
    answer before any plaintext is removed.

    Args:
        section_name (str): extension config section name

    Returns:
        str or None: the raw stored value, or None when the file definitively
        does not hold one.

    Raises:
        PyRevitCredentialError: the config file path could not be resolved or
            the file could not be opened. Reported separately from "absent" so an
            unreadable config is never mistaken for a missing credential, which
            would make a working write look like a failed one.

    Note:
        This cannot distinguish a file that does not exist from one that exists
        and holds nothing, because the INI backend yields an empty config rather
        than failing for a missing or unparsable file. Both come back as None.
        That is the safe direction: the caller treats it as "not stored", keeps
        the legacy keys, and surfaces a write-failure message.
    """
    from pyrevit.coreutils.configparser import open_config_file

    config_path = _config_file_path()
    if not config_path:
        raise PyRevitCredentialError(
            "The pyRevit config file path could not be resolved, so the stored "
            "credential cannot be verified against the file."
        )
    try:
        sections = open_config_file(config_path, read_only=True)
    except Exception as open_err:
        raise PyRevitCredentialError(
            "The pyRevit config file {} could not be reopened to verify the "
            "stored credential: {}".format(config_path, open_err)
        )

    try:
        section = sections.get_section(section_name)
    except AttributeError:
        # No such section in the file, which is a definite answer rather than a
        # failure to look: get_section raises for a missing section.
        return None

    if not section.has_option(CONFIG_KEY):
        return None
    return section.get_option(CONFIG_KEY, None)


def _read_raw(section_name):
    section = _get_section(section_name)
    if section is None:
        return None
    try:
        if not section.has_option(CONFIG_KEY):
            return None
        return section.get_option(CONFIG_KEY, None)
    except Exception as read_err:
        mlogger.warning(
            "credentials: can not read the stored credential for [%s]: %s",
            section_name,
            read_err,
        )
        return None


def _remove_key(section, key):
    """Remove a config key if present. Returns whether anything was removed."""
    try:
        if section is None or not section.has_option(key):
            return False
        section.remove_option(key)
        return True
    except Exception as remove_err:
        mlogger.warning("credentials: can not remove key [%s]: %s", key, remove_err)
        return False


def _is_stored_credential(stored_value, username, secret, kind):
    """Whether a raw config value decrypts to exactly this credential.

    Compares the recovered fields rather than the stored text: the INI backend is
    free to re-encode a value on the way through, and a credential that decrypts
    to what the caller asked for is stored no matter how it is spelled in the file.

    Args:
        stored_value (str): the raw value read back from the config file, or None
        username (str): account name that was written
        secret (str): token or password that was written
        kind (str): ``"token"`` or ``"password"``

    Returns:
        bool: whether the file holds this credential
    """
    if stored_value is None:
        return False
    try:
        recovered = _unseal(stored_value)
    except PyRevitCredentialUnavailable:
        return False
    return (
        recovered.username == username
        and recovered.secret == secret
        and recovered.kind == kind
    )


def _restore_stored_value(section, stored_value):
    """Roll the in-memory credential back to what the config file holds.

    A write that never reached the file must not leave the store advertising a
    credential that only exists until Revit restarts, or ``get_credential``
    answers with a value the next session will not have.

    Args:
        section (ConfigSection): the section the failed write went to
        stored_value (str): the raw value the file holds, or None when it holds
            no credential for this section
    """
    if stored_value is None:
        _remove_key(section, CONFIG_KEY)
        return
    try:
        section.set_option(CONFIG_KEY, stored_value)
    except Exception as restore_err:
        mlogger.warning(
            "credentials: could not restore the stored credential after a failed "
            "write: %s",
            restore_err,
        )


# -----------------------------------------------------------------------------
# public API
# -----------------------------------------------------------------------------
def has_credential(section_name):
    """Whether a sealed credential is stored for this extension.

    True for a stored value that will not decrypt - that is still a configured
    credential, and the difference matters to the user, who has a token to
    re-enter. Use :func:`get_credential` to find out whether it is usable.

    Args:
        section_name (str): extension config section name

    Returns:
        (bool): whether the credential key is present
    """
    return _read_raw(section_name) is not None


def get_credential(section_name):
    """Recover the stored credential for an extension.

    Args:
        section_name (str): extension config section name, e.g.
            ``extpkg.config_section_name`` or ``repo_info.name``. For an
            installed extension both are the extension folder name including its
            ``.extension`` / ``.lib`` postfix.

    Returns:
        (ExtensionCredential): the credential, or None when none is stored

    Raises:
        PyRevitCredentialUnavailable: one is stored but cannot be decrypted. This
            is deliberately not reported as None - see the module docstring.
    """
    stored = _read_raw(section_name)
    if stored is None:
        return None
    return _unseal(stored)


def set_credential(section_name, username, secret, kind="token"):
    """Seal a credential and store it in the extension's config section.

    The new value is read back from the config file and matched against what was
    written before anything else is touched, so a failure part-way through leaves
    the working credential in place instead of deleting it. That is the one
    ordering that cannot lose a token: the alternative - clearing the old keys
    first - destroys the only usable copy whenever sealing then fails.

    Note:
        A flush that does not land is reported as a failure even when the section
        already held a credential, because the file would then still hold the old
        one. The in-memory value is rolled back to match the file, so what
        ``get_credential`` reports is what the next session will see.

    Args:
        section_name (str): extension config section name
        username (str): account name. Pass ``DEFAULT_TOKEN_USERNAME`` for a
            GitHub token; the value is stored inside the sealed blob.
        secret (str): token or password
        kind (str): ``"token"`` or ``"password"``

    Raises:
        PyRevitCredentialStoreReadOnly: the config is admin-locked, so the value
            would have been dropped silently
        PyRevitCredentialError: the credential is empty, or DPAPI is unavailable
        PyRevitCredentialUnavailable: the value could not be verified after being
            written
    """
    if _is_readonly():
        raise PyRevitCredentialStoreReadOnly(
            "The pyRevit config is admin-locked (read-only), so a credential for "
            "[{}] cannot be stored. Unlock the config or set the token on every "
            "command line.".format(section_name)
        )

    sealed = _seal(username, secret, kind)

    section = _get_section(section_name, create=True)
    if section is None:
        raise PyRevitCredentialError(
            "Can not open the config section [{}] to store a credential.".format(
                section_name
            )
        )

    try:
        section.set_option(CONFIG_KEY, sealed)
        _save()
    except Exception as write_err:
        raise PyRevitCredentialError(
            "Can not store the credential for [{}]: {}".format(section_name, write_err)
        )

    # Verify against the file, not the in-memory store: save_changes swallows a
    # failed flush, so only a re-read of the file can tell a stored credential
    # from an accepted-and-dropped one. The file has to hold *this* value, not
    # merely some value: a rotation whose flush was dropped still leaves the
    # previous credential readable, and accepting that would report success while
    # a restart goes on using the old token. Nothing is removed until this passes.
    stored = _read_from_disk(section_name)
    if not _is_stored_credential(stored, username, secret, kind):
        _restore_stored_value(section, stored)
        raise PyRevitCredentialUnavailable(
            "The credential for [{}] was not stored: the config file does not "
            "hold the value that was just written. The file may be read-only or "
            "the write may have been refused, so the credential that was already "
            "in place has been kept.".format(section_name)
        )

    if _remove_legacy_keys(section):
        _save()

    mlogger.info("credentials: stored an encrypted credential for [%s]", section_name)


def delete_credential(section_name):
    """Remove the stored credential for an extension.

    Also clears ``private_repo``, which would otherwise be left claiming a
    credential that no longer exists.

    Args:
        section_name (str): extension config section name

    Returns:
        (bool): whether anything was removed
    """
    if _is_readonly():
        raise PyRevitCredentialStoreReadOnly(
            "The pyRevit config is admin-locked (read-only), so the credential for "
            "[{}] cannot be cleared.".format(section_name)
        )

    section = _get_section(section_name)
    if section is None:
        return False

    removed = _remove_key(section, CONFIG_KEY)
    removed = _remove_legacy_keys(section) or removed
    if removed:
        try:
            section.set_option("private_repo", False)
            _save()
        except Exception as flag_err:
            mlogger.warning(
                "credentials: removed the credential for [%s] but could not clear "
                "its private_repo flag: %s",
                section_name,
                flag_err,
            )
            return True

    mlogger.info("credentials: cleared the stored credential for [%s]", section_name)
    return removed


def _remove_legacy_keys(section):
    removed = False
    for key in LEGACY_CREDENTIAL_KEYS:
        removed = _remove_key(section, key) or removed
    return removed


# -----------------------------------------------------------------------------
# migration
# -----------------------------------------------------------------------------
def migrate_legacy_credentials():
    """Seal any plaintext credential still sitting in an extension config section.

    Older pyRevit wrote ``token`` / ``password`` / ``username`` straight into the
    config file, and the CLI still could until ``--persist-credentials`` learned
    to seal. This runs once per session from
    :func:`pyrevit.versionmgr.upgrade.upgrade_existing_pyrevit`.

    Every ``*.extension`` / ``*.lib`` section is considered, not just the
    extensions currently installed and authorized: a credential for an extension
    that is temporarily uninstalled, or sits in a path that fails authorization,
    would otherwise stay in the clear indefinitely.

    A section is only cleared after the sealed value is stored **and** verified
    by decrypting it back. A section that fails to seal keeps its plaintext and
    is reported, because losing a working token is worse than leaving it where it
    was.

    Returns:
        (int): how many sections were migrated
    """
    from pyrevit.userconfig import user_config

    if user_config is None:
        return 0

    # Checked once, up front: on an admin-locked config nothing can be sealed, and
    # walking every section first would emit the same refusal per extension.
    if _is_readonly():
        mlogger.warning(
            "credentials: the pyRevit config is admin-locked (read-only), so "
            "plaintext extension credentials can not be encrypted. They are left "
            "as they are."
        )
        return 0

    try:
        section_names = list(user_config)
    except Exception as iter_err:
        mlogger.warning("credentials: can not enumerate config sections: %s", iter_err)
        return 0

    migrated = 0
    for section_name in section_names:
        if not section_name.endswith(EXTENSION_SECTION_POSTFIXES):
            continue
        try:
            if _migrate_legacy_section(section_name):
                migrated += 1
        except Exception as section_err:
            mlogger.warning(
                "credentials: could not migrate [%s]: %s", section_name, section_err
            )

    if migrated:
        try:
            _save()
        except Exception as save_err:
            mlogger.warning(
                "credentials: migrated %s section(s) but could not save the config: %s",
                migrated,
                save_err,
            )
        mlogger.info(
            "credentials: encrypted %s plaintext extension credential(s)", migrated
        )

    return migrated


def _migrate_legacy_section(section_name):
    """Seal one section's plaintext credential. Returns whether it changed.

    Returns:
        bool: whether the section now holds a sealed credential
    """
    section = _get_section(section_name)
    if section is None:
        return False

    legacy = {}
    for key in LEGACY_CREDENTIAL_KEYS:
        try:
            if section.has_option(key):
                value = section.get_option(key, None)
                if value is not None and str(value).strip():
                    legacy[key] = value
        except Exception as read_err:
            mlogger.debug(
                "credentials: can not read legacy key [%s] in [%s]: %s",
                key,
                section_name,
                read_err,
            )

    if not legacy:
        return False

    username = legacy.get("username")
    secret = legacy.get("password") or legacy.get("token")
    if not secret:
        # A username with no secret was never a usable credential, and sealing
        # one would create a config entry that looks configured but always fails.
        mlogger.info(
            "credentials: [%s] has a username but no secret; leaving it alone",
            section_name,
        )
        return False

    # A `token` key means a token, even when `password` also holds the same value.
    # Every legacy writer mirrored the token into `password` "for backwards compat",
    # so preferring `password` would label every migrated GitHub token as a
    # password. A section with only `password` is a real username/password pair.
    if legacy.get("token"):
        secret = legacy["token"]
        kind = "token"
        if legacy.get("password") and legacy["password"] != legacy["token"]:
            mlogger.warning(
                "credentials: [%s] held different token and password values; "
                "keeping the token and removing both",
                section_name,
            )
    else:
        secret = legacy["password"]
        kind = "password"

    if not username and kind == "token":
        # Both legacy writers stored a token against the oauth2 username. A
        # password without one is not that case, and defaulting it to oauth2 would
        # seal a basic-auth credential that can never authenticate.
        username = DEFAULT_TOKEN_USERNAME

    set_credential(section_name, username, secret, kind)
    mlogger.info(
        "credentials: encrypted the plaintext credential in [%s]", section_name
    )
    return True
