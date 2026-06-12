# -*- coding: utf-8 -*-
"""Secure per-extension Git token storage using Windows DPAPI (CurrentUser scope).

Each extension stores its own encrypted token inside its own config section
(the same section that holds `disabled`, `private_repo`, etc.). Plaintext
never touches disk.

Public API:
    get_token(section_name)     -- decrypt and return token, or None
    set_token(section_name, token) -- encrypt and persist token
    delete_token(section_name)  -- remove token

`section_name` is the extension folder name, e.g. ``MyTool.extension``.
For an ExtensionPackage object this is ``extpkg.config_section_name``.
For a RepoInfo object (updater) this is ``repo_info.name``.

Note: DPAPI blobs are bound to the Windows user profile and cannot be
recovered after an OS reinstall without profile backup. If decryption fails,
get_token() returns None and the user must re-enter the token.
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

# Key written into each extension's own config section
_KEY_ENCRYPTED = "token_dpapi"

# Legacy plaintext keys that old install code wrote into extension sections
_LEGACY_PLAINTEXT_KEYS = ("token", "password", "username")


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

def _get_or_create_section(section_name):
    try:
        return user_config.get_section(section_name)
    except AttributeError:
        return user_config.add_section(section_name)


def _read_config(key, section_name, fallback=None):
    try:
        section = user_config.get_section(section_name)
        return section.get_option(key, fallback)
    except Exception:
        return fallback


def _write_config(key, value, section_name):
    section = _get_or_create_section(section_name)
    section.set_option(key, value)
    user_config.save_changes()


def _delete_config(key, section_name):
    try:
        section = user_config.get_section(section_name)
        if section.has_option(key):
            section.remove_option(key)
            user_config.save_changes()
    except Exception:
        pass


# ------------------------------------------------------------------
# Migration
# ------------------------------------------------------------------

def migrate_legacy_token():
    """Encrypt plaintext token/password keys in extension config sections.

    Old install code wrote ``token`` or ``password`` directly into each
    extension's config section alongside ``private_repo = True``. This
    encrypts those values in-place and removes the plaintext keys.
    """
    try:
        from pyrevit.extensions import extpackages
        pkgs = extpackages.get_ext_packages(authorized_only=False)
    except Exception:
        return

    changed = False
    for pkg in pkgs:
        try:
            cfg = pkg.config
            if not cfg.private_repo:
                continue
            if not cfg.has_option(_KEY_ENCRYPTED):
                pwd = cfg.get_option("password", None) \
                      or cfg.get_option("token", None)
                if pwd:
                    try:
                        cfg.set_option(_KEY_ENCRYPTED, _encrypt(pwd))
                        changed = True
                    except Exception as ex:
                        mlogger.warning(
                            "credentials: failed to encrypt token for [%s]: %s",
                            pkg.config_section_name, ex
                        )
            for key in _LEGACY_PLAINTEXT_KEYS:
                if cfg.has_option(key):
                    cfg.remove_option(key)
                    changed = True
        except Exception as ex:
            mlogger.warning("credentials: error migrating extension token: %s", ex)

    if changed:
        try:
            user_config.save_changes()
        except Exception as ex:
            mlogger.warning(
                "credentials: failed to save config after migration: %s", ex
            )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def get_token(section_name):
    """Return the decrypted token for an extension, or None.

    Args:
        section_name (str): Extension config section name, e.g.
            ``extpkg.config_section_name`` or ``repo_info.name``.

    Returns:
        str or None: Decrypted token, or None if not set or unrecoverable.
    """
    b64 = _read_config(_KEY_ENCRYPTED, section_name)
    if b64:
        try:
            return _decrypt(b64)
        except Exception as ex:
            mlogger.warning(
                "credentials: failed to decrypt token for [%s]: %s",
                section_name, ex
            )
    return None


def set_token(section_name, token):
    """Encrypt and persist the token for an extension.

    Args:
        section_name (str): Extension config section name.
        token (str): PAT or password to encrypt and store.

    Raises:
        Exception: Propagates DPAPI failures so the caller can prompt the user.
    """
    if not token:
        delete_token(section_name)
        return
    _write_config(_KEY_ENCRYPTED, _encrypt(token), section_name)
    for key in _LEGACY_PLAINTEXT_KEYS:
        _delete_config(key, section_name)


def delete_token(section_name):
    """Remove the stored token for an extension.

    Args:
        section_name (str): Extension config section name.
    """
    _delete_config(_KEY_ENCRYPTED, section_name)
