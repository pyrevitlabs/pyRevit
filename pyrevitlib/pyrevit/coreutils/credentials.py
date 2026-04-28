# -*- coding: utf-8 -*-
"""Secure Git token storage using Windows DPAPI (CurrentUser scope).

Tokens are encrypted with ProtectedData and stored as base64 in the pyRevit
config, keyed by Git host. Plaintext never touches disk.

Works with any Git hosting platform: GitHub, GitLab, Gitbucket, self-hosted
Gitea, etc.

Note: DPAPI blobs are bound to the Windows user profile and cannot be
recovered after an OS reinstall without profile backup. If decryption fails,
get_token() returns None and the user must re-enter the token.

Note: The C# CLI (PyRevitCLI.cs:TryGetCredentials) reads tokens from --token
CLI arguments only. Bridging stored tokens to CLI commands is not yet
implemented.
"""
import clr

# System.Security.Cryptography.ProtectedData is a standalone assembly on
# .NET Core (Revit 2025+); on .NET Framework it lives in System.Security.
try:
    clr.AddReference("System.Security.Cryptography.ProtectedData")
except Exception:
    clr.AddReference("System.Security")

from System import Convert
from System.Security.Cryptography import ProtectedData, DataProtectionScope
from System.Text import Encoding

from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config

mlogger = get_logger(__name__)

_SECTION = "git_credentials"
_KEY_SUFFIX = "_token_dpapi"

# Legacy section/keys written by the first version of this module
_LEGACY_SECTION = "github"
_LEGACY_KEY_ENCRYPTED = "token_dpapi"
_LEGACY_KEY_PLAINTEXT = "token"

# Keys written by old install code into per-extension config sections
_EXT_PLAINTEXT_KEYS = ("token", "username", "password")


# ------------------------------------------------------------------
# URL / host helpers
# ------------------------------------------------------------------

def _url_to_key_prefix(url):
    """Return a config-safe prefix derived from the host of a git URL.

    Examples:
        https://github.com/owner/repo.git  -> github_com
        git@gitlab.com:owner/repo.git      -> gitlab_com
        https://git.corp.io/owner/repo     -> git_corp_io
    """
    if not url:
        return "unknown"
    host = url
    if host.startswith("git@"):
        # git@host:path
        host = host[4:].split(":")[0]
    elif "://" in host:
        # https://host/path  or  http://user:pass@host/path
        host = host.split("://", 1)[1].split("/")[0]
        if "@" in host:
            host = host.split("@", 1)[1]
        # Strip port
        host = host.split(":")[0]
    else:
        host = host.split("/")[0]
    # Replace non-alphanumeric chars with underscores; collapse consecutive _
    safe = "".join(c if c.isalnum() else "_" for c in host.lower())
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("_") or "unknown"


def _config_key(url):
    return _url_to_key_prefix(url) + _KEY_SUFFIX


# ------------------------------------------------------------------
# DPAPI helpers
# ------------------------------------------------------------------

def _encrypt(plaintext):
    """Encrypt a string with DPAPI (CurrentUser scope). Returns base64 string."""
    data = Encoding.UTF8.GetBytes(plaintext)
    protected = ProtectedData.Protect(data, None, DataProtectionScope.CurrentUser)
    # Use System.Convert to stay in .NET types and avoid the IronPython 2
    # bytes(bytearray(...)) pitfall where that yields repr, not raw bytes.
    return Convert.ToBase64String(protected)


def _decrypt(b64_ciphertext):
    """Decrypt a base64 DPAPI blob. Returns plaintext string."""
    # FromBase64String returns a .NET byte[] directly -- no Python bytearray needed.
    raw = Convert.FromBase64String(b64_ciphertext)
    decrypted = ProtectedData.Unprotect(raw, None, DataProtectionScope.CurrentUser)
    return Encoding.UTF8.GetString(decrypted)


# ------------------------------------------------------------------
# Config helpers
# ------------------------------------------------------------------

def _get_or_create_section(section_name=None):
    name = section_name or _SECTION
    try:
        return user_config.get_section(name)
    except AttributeError:
        return user_config.add_section(name)


def _read_config(key, section_name=None, fallback=None):
    try:
        section = user_config.get_section(section_name or _SECTION)
        return section.get_option(key, fallback)
    except Exception:
        return fallback


def _write_config(key, value, section_name=None):
    section = _get_or_create_section(section_name)
    section.set_option(key, value)
    user_config.save_changes()


def _delete_config(key, section_name=None):
    try:
        section = user_config.get_section(section_name or _SECTION)
        if section.has_option(key):
            section.remove_option(key)
            user_config.save_changes()
    except Exception:
        pass


# ------------------------------------------------------------------
# Migration
# ------------------------------------------------------------------

def migrate_legacy_token():
    """Migrate any old-format tokens to the new per-host DPAPI storage.

    Handles:
    1. [github].token_dpapi (encrypted by the first version of this module)
       -> re-keyed as github_com_token_dpapi under [git_credentials]
    2. [github].token (plaintext from even older code)
       -> encrypted and stored as github_com_token_dpapi under [git_credentials]
    3. Per-extension plaintext token/password (private_repo=True)
       -> encrypted and stored by host under [git_credentials]

    Safe to call on every startup -- no-op when nothing to migrate.
    Failures are logged as warnings and never propagate to the caller.
    """
    github_key = "github_com" + _KEY_SUFFIX

    # Case 1: already-encrypted token in the old [github] section
    legacy_encrypted = _read_config(_LEGACY_KEY_ENCRYPTED, section_name=_LEGACY_SECTION)
    if legacy_encrypted:
        if not _read_config(github_key):
            try:
                plaintext = _decrypt(legacy_encrypted)
                _write_config(github_key, _encrypt(plaintext))
            except Exception as ex:
                mlogger.warning("credentials: could not re-encrypt legacy token: %s", ex)
        if _read_config(github_key):
            _delete_config(_LEGACY_KEY_ENCRYPTED, section_name=_LEGACY_SECTION)
        return

    # Case 2: plaintext token in the old [github] section
    legacy_plaintext = _read_config(_LEGACY_KEY_PLAINTEXT, section_name=_LEGACY_SECTION)
    if legacy_plaintext:
        if not _read_config(github_key):
            try:
                _write_config(github_key, _encrypt(legacy_plaintext))
            except Exception as ex:
                mlogger.warning("credentials: failed to encrypt legacy plaintext token: %s", ex)
        if _read_config(github_key):
            _delete_config(_LEGACY_KEY_PLAINTEXT, section_name=_LEGACY_SECTION)
        return

    # Case 3: per-extension plaintext tokens (private_repo=True with token/password key)
    _migrate_extension_plaintext_tokens()


def _migrate_extension_plaintext_tokens():
    """Encrypt per-extension plaintext tokens and remove them from config.

    Old install code wrote token/username/password directly into each
    extension's config section. This reads installed extensions, finds those
    with a private_repo flag and a plaintext credential, encrypts the
    credential by host, then strips the plaintext keys.
    """
    try:
        from pyrevit.extensions import extpackages
        pkgs = extpackages.get_ext_packages(authorized_only=False)
    except Exception:
        return

    changed = False
    for pkg in pkgs:
        if not pkg.url:
            continue
        try:
            cfg = pkg.config
            if not cfg.private_repo:
                continue
            pwd = cfg.get_option("password", None)
            if not pwd:
                pwd = cfg.get_option("token", None)
            if pwd:
                try:
                    set_token(pkg.url, pwd)
                except Exception as ex:
                    mlogger.warning(
                        "credentials: failed to encrypt token for %s: %s", pkg.url, ex
                    )
            for key in _EXT_PLAINTEXT_KEYS:
                try:
                    if cfg.has_option(key):
                        cfg.remove_option(key)
                        changed = True
                except Exception:
                    pass
        except Exception as ex:
            mlogger.warning("credentials: error migrating extension token: %s", ex)

    if changed:
        try:
            user_config.save_changes()
        except Exception as ex:
            mlogger.warning("credentials: failed to save config after migration: %s", ex)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def get_token(url):
    """Return the decrypted token for the given git URL/host, or None.

    Args:
        url (str): Any git URL (https://, http://, git@host:path).
                   The hostname is extracted to look up the stored token.

    Returns:
        str or None: Decrypted token, or None if not set or unrecoverable.
    """
    key = _config_key(url)
    b64 = _read_config(key)
    if b64:
        try:
            return _decrypt(b64)
        except Exception as ex:
            mlogger.warning("credentials: failed to decrypt token for %s: %s",
                            _url_to_key_prefix(url), ex)
    return None


def set_token(url, token):
    """Encrypt and persist the token for the given git URL/host.

    Args:
        url (str): Any git URL; the hostname is used as the storage key.
        token (str): PAT or password to encrypt and store.

    Raises:
        Exception: Propagates DPAPI failures so the caller can prompt the user.
    """
    if not token:
        delete_token(url)
        return
    key = _config_key(url)
    _write_config(key, _encrypt(token))


def delete_token(url):
    """Remove the stored token for the given git URL/host.

    Args:
        url (str): Any git URL; the hostname is used as the storage key.
    """
    _delete_config(_config_key(url))
