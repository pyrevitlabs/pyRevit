# -*- coding: utf-8 -*-
"""Secure GitHub token storage using Windows DPAPI (CurrentUser scope).

Tokens are encrypted with ProtectedData and stored as base64 in the pyRevit
config. Plaintext never touches disk.

Note: DPAPI blobs are bound to the Windows user profile and cannot be
recovered after an OS reinstall without profile backup. If decryption fails,
get_github_token() returns None and the user must re-enter the token.

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

_SECTION = "github"
_KEY_TOKEN = "token_dpapi"
_KEY_TOKEN_LEGACY = "token"  # plaintext key used before this implementation

# Keys written by old install code into per-extension config sections
_EXT_PLAINTEXT_KEYS = ("token", "username", "password")


# ------------------------------------------------------------------
# DPAPI helpers
# ------------------------------------------------------------------

def _encrypt(plaintext):
    """Encrypt a string using DPAPI (CurrentUser scope). Returns base64 string."""
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

def _get_or_create_section():
    """Return the github config section, creating it if absent."""
    try:
        return user_config.get_section(_SECTION)
    except AttributeError:
        return user_config.add_section(_SECTION)


def _read_config(key, fallback=None):
    try:
        section = user_config.get_section(_SECTION)
        return section.get_option(key, fallback)
    except Exception:
        return fallback


def _write_config(key, value):
    section = _get_or_create_section()
    section.set_option(key, value)
    user_config.save_changes()


def _delete_config(key):
    try:
        section = user_config.get_section(_SECTION)
        if section.has_option(key):
            section.remove_option(key)
            user_config.save_changes()
    except Exception:
        pass


# ------------------------------------------------------------------
# Migration
# ------------------------------------------------------------------

def _cleanup_extension_plaintext_keys(save=True):
    """Remove token/username/password keys from all per-extension sections."""
    changed = False
    for section in user_config:
        if not section.has_option("private_repo"):
            continue
        for key in _EXT_PLAINTEXT_KEYS:
            try:
                if section.has_option(key):
                    section.remove_option(key)
                    changed = True
            except Exception:
                pass
    if changed and save:
        try:
            user_config.save_changes()
        except Exception as ex:
            mlogger.warning("credentials: failed to save config after cleanup: %s", ex)


def _migrate_extension_plaintext_tokens():
    """Find a plaintext token in per-extension sections and encrypt it globally.

    Old install code wrote token/username/password into the extension's own
    config section. This helper reads the first one found, stores it as the
    global DPAPI token, then strips the plaintext keys from all sections.
    """
    already_encrypted = bool(_read_config(_KEY_TOKEN))

    if not already_encrypted:
        for section in user_config:
            if not section.has_option("private_repo"):
                continue
            pwd = section.get_option("password", None)
            if not pwd:
                pwd = section.get_option("token", None)
            if pwd:
                try:
                    set_github_token(pwd)
                    already_encrypted = True
                except Exception as ex:
                    mlogger.warning(
                        "credentials: failed to encrypt extension token: %s", ex
                    )
                break  # one global token is enough

    if already_encrypted:
        _cleanup_extension_plaintext_keys()


def migrate_legacy_token():
    """Re-encrypt any plaintext GitHub token found in config with DPAPI.

    Handles both the legacy [github].token key and per-extension sections
    written by old install code (private_repo=True with token/password).
    Safe to call on every startup -- no-op when nothing to migrate.
    If migration fails the plaintext token is left untouched.
    """
    # Case 1: [github].token plaintext key (original legacy path)
    legacy_token = _read_config(_KEY_TOKEN_LEGACY)
    if legacy_token:
        existing = _read_config(_KEY_TOKEN)
        if existing:
            # Already migrated -- verify blob before removing plaintext.
            try:
                _decrypt(existing)
                _delete_config(_KEY_TOKEN_LEGACY)
            except Exception as ex:
                mlogger.warning(
                    "credentials: encrypted token unreadable, keeping legacy: %s", ex
                )
        else:
            try:
                set_github_token(legacy_token)
                _delete_config(_KEY_TOKEN_LEGACY)
            except Exception as ex:
                mlogger.warning("credentials: failed to migrate legacy token: %s", ex)
        return

    # Case 2: per-extension plaintext token written by old install code
    _migrate_extension_plaintext_tokens()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def get_github_token():
    """Return the decrypted GitHub token, or None if not set or unrecoverable."""
    b64 = _read_config(_KEY_TOKEN)
    if b64:
        try:
            return _decrypt(b64)
        except Exception as ex:
            mlogger.warning("credentials: failed to decrypt token: %s", ex)
            # Fall back to legacy plaintext so existing setups survive a
            # corrupt encrypted blob.
            return _read_config(_KEY_TOKEN_LEGACY) or None
    # Pre-migration fallback: return plaintext legacy token if present.
    return _read_config(_KEY_TOKEN_LEGACY) or None


def set_github_token(token):
    """Encrypt and persist the GitHub token.

    Raises on DPAPI failure -- caller should catch and prompt the user to
    retry rather than silently losing the token.
    """
    if not token:
        delete_github_token()
        return
    encrypted = _encrypt(token)
    _write_config(_KEY_TOKEN, encrypted)
    # Remove legacy plaintext immediately rather than waiting for next startup.
    _delete_config(_KEY_TOKEN_LEGACY)


def delete_github_token():
    """Remove the stored token entirely (both encrypted and legacy keys)."""
    _delete_config(_KEY_TOKEN)
    _delete_config(_KEY_TOKEN_LEGACY)
