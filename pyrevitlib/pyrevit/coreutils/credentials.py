"""Secure GitHub token storage using Windows DPAPI (CurrentUser scope).

Tokens are encrypted with ProtectedData and stored as base64 in the pyRevit
config. Plaintext never touches disk.

Note: DPAPI blobs are bound to the Windows user profile and cannot be
recovered after an OS reinstall without profile backup. If decryption fails,
get_github_token() returns None and the user must re-enter the token.

Note: Extension repo passwords in versionmgr/updater.py remain plaintext;
only the GitHub token is encrypted here.

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


# ------------------------------------------------------------------
# DPAPI helpers
# ------------------------------------------------------------------

def _encrypt(plaintext):
    """Encrypt a string using DPAPI (CurrentUser scope). Returns base64 string."""
    data = Encoding.UTF8.GetBytes(plaintext)
    protected = ProtectedData.Protect(data, None, DataProtectionScope.CurrentUser)
    # Use System.Convert throughout to stay in .NET types and avoid
    # IronPython 2 bytes(bytearray(...)) pitfall (gives repr, not raw bytes).
    return Convert.ToBase64String(protected)


def _decrypt(b64_ciphertext):
    """Decrypt a base64 DPAPI blob. Returns plaintext string."""
    # FromBase64String returns a .NET byte[] directly — no Python bytearray needed.
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

def migrate_legacy_token():
    """Re-encrypt a plaintext 'token' config key with DPAPI.

    Safe to call on every startup — no-op if already migrated or absent.
    If migration fails the legacy plaintext token is left untouched so the
    user is not locked out.
    """
    legacy_token = _read_config(_KEY_TOKEN_LEGACY)
    if not legacy_token:
        return
    # Already migrated — verify the blob is still decryptable before removing legacy.
    existing = _read_config(_KEY_TOKEN)
    if existing:
        try:
            _decrypt(existing)
            _delete_config(_KEY_TOKEN_LEGACY)
        except Exception as ex:
            mlogger.warning(
                "credentials: encrypted token unreadable, keeping legacy: %s", ex
            )
        return
    try:
        set_github_token(legacy_token)
        _delete_config(_KEY_TOKEN_LEGACY)
    except Exception as ex:
        mlogger.warning("credentials: failed to migrate legacy token: %s", ex)


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
            # Fall back to legacy plaintext rather than returning None so
            # existing setups are not broken by a corrupt encrypted blob.
            return _read_config(_KEY_TOKEN_LEGACY) or None
    # Pre-migration fallback: return plaintext legacy token if present.
    return _read_config(_KEY_TOKEN_LEGACY) or None


def set_github_token(token):
    """Encrypt and persist the GitHub token.

    Raises on DPAPI failure — caller should catch and prompt the user to
    retry rather than silently losing the token.
    """
    if not token:
        delete_github_token()
        return
    encrypted = _encrypt(token)
    _write_config(_KEY_TOKEN, encrypted)
    # remove legacy plaintext immediately so it is not left behind until
    # the next startup migration run
    _delete_config(_KEY_TOKEN_LEGACY)


def delete_github_token():
    """Remove the stored token entirely (both encrypted and legacy keys)."""
    _delete_config(_KEY_TOKEN)
    _delete_config(_KEY_TOKEN_LEGACY)
