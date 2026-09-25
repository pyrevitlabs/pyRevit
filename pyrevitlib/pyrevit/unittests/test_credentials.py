# -*- coding: utf-8 -*-
"""Tests for :mod:`pyrevit.coreutils.credentials`, the extension credential store.

Covers the config contract and the crypto contract separately; the module
docstring explains why that split matters.

Two things are under test and they are deliberately kept apart:

* **The config contract** - which key a credential lives under, that setting one
  removes the legacy plaintext keys, that clearing one leaves nothing behind, and
  above all that a failure never deletes a working token. A dict-backed fake
  ``IConfiguration`` models the C# side exactly as ``test_config_roundtrip`` does,
  so these run identically under IronPython 2/3 and CPython and never touch the
  user's real config.

* **The crypto** - that a sealed value really round-trips, and that every way a
  stored value can be unusable is reported as *unreadable* rather than as
  *absent*. These need Windows DPAPI, so they skip where it is unavailable
  instead of passing vacuously.

The distinction the second group protects is the one that turns a stale token
into a confusing libgit2 error about a missing authentication callback, so a
silent-skip here would hide a real regression.

Run from Revit via the pyRevit DevTools "Credentials Module Tests" button.
"""

import json
import unittest

from pyrevit.coreutils import credentials
from pyrevit.coreutils.configparser import ConfigSections


class _FakeConfiguration(object):
    """In-memory stand-in for the C# IConfiguration, as in test_config_roundtrip.

    Raw strings in, ``None`` only for a missing key, so the JSON encode/decode
    the real backend performs is exercised on the way through.
    """

    def __init__(self):
        self._store = {}
        self._sections = []

    def GetRawValueOrDefault(self, section, key, default=None):
        return self._store.get((section, key), default)

    def SetRawValue(self, section, key, raw):
        self.AddSection(section)
        self._store[(section, key)] = raw

    def RemoveOption(self, section, key):
        if (section, key) in self._store:
            del self._store[(section, key)]
            return True
        return False

    def HasSectionKey(self, section, key):
        return (section, key) in self._store

    def HasSection(self, section):
        return section in self._sections

    def AddSection(self, section):
        if section in self._sections:
            return False
        self._sections.append(section)
        return True

    def RemoveSection(self, section):
        for key in [k for k in self._store if k[0] == section]:
            del self._store[key]
        if section in self._sections:
            self._sections.remove(section)
            return True
        return False

    def GetSectionNames(self):
        return list(self._sections)

    def GetSectionOptionNames(self, section):
        return [key for (sec, key) in self._store if sec == section]

    def SaveConfiguration(self):
        pass


class _FakeConfigurationService(object):
    def __init__(self, configuration, read_only=False):
        self.Configuration = configuration
        self.ReadOnly = read_only


class _FakeUserConfig(object):
    """Stand-in for ``pyrevit.userconfig.user_config``.

    Only the surface ``credentials`` actually touches, backed by the real
    ``ConfigSections`` so the section access semantics - notably that
    ``get_section`` raises for a missing section - are the production ones.
    """

    def __init__(self, read_only=False):
        self._config = _FakeConfiguration()
        self._service = _FakeConfigurationService(self._config, read_only=read_only)
        self.config_sections = ConfigSections(self._service)
        self.save_count = 0

    @property
    def is_readonly(self):
        return self._service.ReadOnly

    def __iter__(self):
        return self.config_sections.__iter__()

    def has_section(self, name):
        return self.config_sections.has_section(name)

    def add_section(self, name):
        return self.config_sections.add_section(name)

    def get_section(self, name):
        return self.config_sections.get_section(name)

    def save_changes(self):
        self.save_count += 1

    # test helpers
    def raw(self, section, key):
        return self._config.GetRawValueOrDefault(section, key)

    def put_raw(self, section, key, value):
        self._config.SetRawValue(section, key, value)


class _CredentialsTestCase(unittest.TestCase):
    """Base case that swaps in a fake user_config for the duration of a test."""

    def setUp(self):
        import pyrevit.userconfig as userconfig

        self._real_user_config = userconfig.user_config
        self.user_config = _FakeUserConfig()
        userconfig.user_config = self.user_config

    def tearDown(self):
        import pyrevit.userconfig as userconfig

        userconfig.user_config = self._real_user_config

    def seed_plaintext(self, section, **keys):
        """Write keys the way a pre-sealing pyRevit would have."""
        self.user_config.add_section(section)
        for key, value in keys.items():
            self.user_config.put_raw(section, key, json.dumps(value))


class AbsentCredentialTests(_CredentialsTestCase):
    """No stored credential is a normal state, not a failure."""

    def test_missing_section_reports_no_credential(self):
        self.assertIsNone(credentials.get_credential("NotInstalled.extension"))

    def test_section_without_credential_key_reports_no_credential(self):
        self.user_config.add_section("Public.extension")
        self.user_config.put_raw("Public.extension", "disabled", "true")
        self.assertIsNone(credentials.get_credential("Public.extension"))

    def test_has_credential_is_false_when_absent(self):
        self.assertFalse(credentials.has_credential("Nothing.extension"))

    def test_builtin_private_repo_flag_is_not_a_credential(self):
        """A shipped extension gets private_repo=True with no credential at all.

        Reading the flag as "needs auth" is what used to send public repos down
        an authenticated path, so it has to stay independent of the store.
        """
        self.user_config.add_section("pyRevitCore.extension")
        self.user_config.put_raw("pyRevitCore.extension", "private_repo", "true")
        self.assertIsNone(credentials.get_credential("pyRevitCore.extension"))
        self.assertFalse(credentials.has_credential("pyRevitCore.extension"))


class SealingTests(_CredentialsTestCase):
    """The crypto contract, against real Windows DPAPI where available."""

    def setUp(self):
        _CredentialsTestCase.setUp(self)
        if not credentials.is_available():
            self.skipTest("Windows DPAPI is not available on this runtime")

    def test_round_trip_restores_the_credential(self):
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_abc123")
        stored = credentials.get_credential("MyTool.extension")
        self.assertEqual("oauth2", stored.username)
        self.assertEqual("ghp_abc123", stored.secret)
        self.assertEqual("token", stored.kind)

    def test_round_trip_restores_a_password_credential(self):
        credentials.set_credential(
            "MyTool.extension", "alex", "s3cret", kind="password"
        )
        stored = credentials.get_credential("MyTool.extension")
        self.assertEqual("alex", stored.username)
        self.assertEqual("s3cret", stored.secret)
        self.assertEqual("password", stored.kind)

    def test_stored_value_does_not_contain_the_secret(self):
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_supersecret")
        raw = self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        self.assertNotIn("ghp_supersecret", raw)

    def test_repr_does_not_leak_the_secret(self):
        cred = credentials.ExtensionCredential("oauth2", "ghp_supersecret")
        self.assertNotIn("ghp_supersecret", repr(cred))

    def test_two_seals_of_the_same_credential_differ(self):
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_abc123")
        first = self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_abc123")
        second = self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        self.assertNotEqual(first, second)

    def test_blank_username_is_rejected(self):
        self.assertRaises(
            credentials.PyRevitCredentialError,
            credentials.set_credential,
            "MyTool.extension",
            "  ",
            "ghp_abc123",
        )

    def test_blank_secret_is_rejected(self):
        self.assertRaises(
            credentials.PyRevitCredentialError,
            credentials.set_credential,
            "MyTool.extension",
            "oauth2",
            "",
        )

    def test_rejected_write_leaves_nothing_behind(self):
        self.assertRaises(
            credentials.PyRevitCredentialError,
            credentials.set_credential,
            "MyTool.extension",
            "oauth2",
            "",
        )
        self.assertIsNone(credentials.get_credential("MyTool.extension"))


class UnreadableCredentialTests(_CredentialsTestCase):
    """A stored value that will not decrypt must not look like no credential."""

    def setUp(self):
        _CredentialsTestCase.setUp(self)
        if not credentials.is_available():
            self.skipTest("Windows DPAPI is not available on this runtime")

    def _store_garbage(self, section="MyTool.extension"):
        self.user_config.add_section(section)
        self.user_config.put_raw(section, credentials.CONFIG_KEY, "not-a-sealed-blob")

    def test_undecryptable_value_raises_unavailable(self):
        self._store_garbage()
        self.assertRaises(
            credentials.PyRevitCredentialUnavailable,
            credentials.get_credential,
            "MyTool.extension",
        )

    def test_undecryptable_value_still_counts_as_configured(self):
        """A stored value counts as configured even when it cannot be read.

        That is the difference between "re-enter your token" and "you never had
        one", and only the first is actionable.
        """
        self._store_garbage()
        self.assertTrue(credentials.has_credential("MyTool.extension"))

    def test_tampered_value_raises_unavailable(self):
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_abc123")
        stored = self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        # Flip a character in the middle of the base64 body.
        index = len(stored) // 2
        flipped = "A" if stored[index] != "A" else "B"
        self.user_config.put_raw(
            "MyTool.extension",
            credentials.CONFIG_KEY,
            stored[:index] + flipped + stored[index + 1 :],
        )
        self.assertRaises(
            credentials.PyRevitCredentialUnavailable,
            credentials.get_credential,
            "MyTool.extension",
        )


class DeleteCredentialTests(_CredentialsTestCase):
    """Clearing a credential must leave nothing that looks like one."""

    def setUp(self):
        _CredentialsTestCase.setUp(self)
        if not credentials.is_available():
            self.skipTest("Windows DPAPI is not available on this runtime")

    def test_delete_removes_the_credential_key(self):
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_abc123")
        self.assertTrue(credentials.delete_credential("MyTool.extension"))
        self.assertFalse(
            self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        )
        self.assertIsNone(credentials.get_credential("MyTool.extension"))

    def test_delete_clears_the_private_repo_flag(self):
        """A cleared credential must not leave the flag claiming one."""
        credentials.set_credential("MyTool.extension", "oauth2", "ghp_abc123")
        credentials.delete_credential("MyTool.extension")
        self.assertIs(
            False,
            self.user_config.get_section("MyTool.extension").get_option("private_repo"),
        )

    def test_delete_on_a_section_without_a_credential_reports_nothing_removed(self):
        self.user_config.add_section("Public.extension")
        self.assertFalse(credentials.delete_credential("Public.extension"))

    def test_delete_on_a_missing_section_reports_nothing_removed(self):
        self.assertFalse(credentials.delete_credential("Gone.extension"))


class ReadOnlyConfigTests(_CredentialsTestCase):
    """An admin-locked config must refuse loudly, not accept and drop."""

    def setUp(self):
        _CredentialsTestCase.setUp(self)
        self.user_config = _FakeUserConfig(read_only=True)
        import pyrevit.userconfig as userconfig

        userconfig.user_config = self.user_config

    def test_set_refuses_on_a_read_only_config(self):
        self.assertRaises(
            credentials.PyRevitCredentialStoreReadOnly,
            credentials.set_credential,
            "MyTool.extension",
            "oauth2",
            "ghp_abc123",
        )

    def test_delete_refuses_on_a_read_only_config(self):
        self.assertRaises(
            credentials.PyRevitCredentialStoreReadOnly,
            credentials.delete_credential,
            "MyTool.extension",
        )

    def test_is_available_is_false_on_a_read_only_config(self):
        self.assertFalse(credentials.is_available())


class MigrationTests(_CredentialsTestCase):
    """One-time sealing of the plaintext credentials older pyRevit wrote."""

    def setUp(self):
        _CredentialsTestCase.setUp(self)
        if not credentials.is_available():
            self.skipTest("Windows DPAPI is not available on this runtime")

    def test_token_only_section_is_migrated(self):
        self.seed_plaintext("MyTool.extension", token="ghp_abc123")
        self.assertEqual(1, credentials.migrate_legacy_credentials())

        stored = credentials.get_credential("MyTool.extension")
        self.assertEqual("ghp_abc123", stored.secret)
        self.assertEqual("oauth2", stored.username)
        self.assertIsNone(self.user_config.raw("MyTool.extension", "token"))

    def test_password_section_keeps_its_username(self):
        """A real username/password pair must survive the migration."""
        self.seed_plaintext("MyTool.extension", username="alex", password="s3cret")
        self.assertEqual(1, credentials.migrate_legacy_credentials())

        stored = credentials.get_credential("MyTool.extension")
        self.assertEqual("alex", stored.username)
        self.assertEqual("s3cret", stored.secret)
        self.assertEqual("password", stored.kind)
        self.assertIsNone(self.user_config.raw("MyTool.extension", "username"))
        self.assertIsNone(self.user_config.raw("MyTool.extension", "password"))

    def test_cli_style_token_section_is_migrated(self):
        """--persist-credentials wrote token plus an oauth2/password mirror."""
        self.seed_plaintext(
            "MyTool.extension",
            token="ghp_abc123",
            username="oauth2",
            password="ghp_abc123",
        )
        self.assertEqual(1, credentials.migrate_legacy_credentials())
        stored = credentials.get_credential("MyTool.extension")
        self.assertEqual("ghp_abc123", stored.secret)
        for key in ("token", "username", "password"):
            self.assertIsNone(self.user_config.raw("MyTool.extension", key))

    def test_builtin_section_with_no_credential_is_left_alone(self):
        """private_repo=True on a shipped extension is not a credential."""
        self.seed_plaintext("pyRevitCore.extension", private_repo=True, disabled=False)
        self.assertEqual(0, credentials.migrate_legacy_credentials())
        self.assertIsNone(
            self.user_config.raw("pyRevitCore.extension", credentials.CONFIG_KEY)
        )

    def test_username_without_a_secret_is_not_migrated(self):
        """Sealing a username with no secret is refused.

        A usable-looking entry that can never authenticate is worse than no entry.
        """
        self.seed_plaintext("MyTool.extension", username="alex")
        self.assertEqual(0, credentials.migrate_legacy_credentials())
        self.assertIsNone(
            self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        )

    def test_already_migrated_section_is_idempotent(self):
        self.seed_plaintext("MyTool.extension", token="ghp_abc123")
        self.assertEqual(1, credentials.migrate_legacy_credentials())
        self.assertEqual(0, credentials.migrate_legacy_credentials())

        first = self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        self.assertEqual(0, credentials.migrate_legacy_credentials())
        self.assertEqual(
            first, self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        )

    def test_non_extension_sections_are_ignored(self):
        self.seed_plaintext("core", token="ghp_abc123")
        self.assertEqual(0, credentials.migrate_legacy_credentials())
        self.assertEqual('"ghp_abc123"', self.user_config.raw("core", "token"))

    def test_migration_covers_a_section_for_an_uninstalled_extension(self):
        """The migration walks the config, not the installed packages.

        A token for something temporarily uninstalled would otherwise stay in the
        clear indefinitely, because the extension manager never sees it.
        """
        self.seed_plaintext("Removed.extension", token="ghp_abc123")
        self.assertEqual(1, credentials.migrate_legacy_credentials())
        self.assertEqual(
            "ghp_abc123", credentials.get_credential("Removed.extension").secret
        )

    def test_multiple_sections_are_all_migrated(self):
        self.seed_plaintext("A.extension", token="ghp_a")
        self.seed_plaintext("B.lib", username="alex", password="pw_b")
        self.assertEqual(2, credentials.migrate_legacy_credentials())
        self.assertEqual("ghp_a", credentials.get_credential("A.extension").secret)
        self.assertEqual("pw_b", credentials.get_credential("B.lib").secret)


class MigrationNoDataLossTests(_CredentialsTestCase):
    """A migration that cannot seal must keep the plaintext it could not replace."""

    def setUp(self):
        _CredentialsTestCase.setUp(self)
        self._real_seal = credentials._seal
        self._seal_fails = True

        def failing_seal(username, secret, kind):
            if self._seal_fails:
                raise credentials.PyRevitCredentialError("sealing is unavailable")
            return self._real_seal(username, secret, kind)

        credentials._seal = failing_seal

    def tearDown(self):
        credentials._seal = self._real_seal
        _CredentialsTestCase.tearDown(self)

    def test_plaintext_survives_a_failed_seal(self):
        """A failed seal must leave the plaintext credential in place.

        Clearing the legacy keys before the sealed value is verified destroys the
        only usable copy of a working token.
        """
        self.seed_plaintext("MyTool.extension", token="ghp_abc123")
        credentials.migrate_legacy_credentials()

        self.assertEqual(
            '"ghp_abc123"', self.user_config.raw("MyTool.extension", "token")
        )
        self.assertIsNone(
            self.user_config.raw("MyTool.extension", credentials.CONFIG_KEY)
        )

    def test_migration_reports_nothing_migrated_when_sealing_fails(self):
        self.seed_plaintext("MyTool.extension", token="ghp_abc123")
        self.assertEqual(0, credentials.migrate_legacy_credentials())

    def test_a_failing_section_does_not_stop_the_others(self):
        """One bad section must not strand every other extension's token."""
        self.seed_plaintext("Good.extension", token="ghp_good")

        real_set = credentials.set_credential

        def selective_set(section_name, username, secret, kind="token"):
            if section_name == "Bad.extension":
                raise credentials.PyRevitCredentialError("sealing is unavailable")
            return real_set(section_name, username, secret, kind)

        credentials.set_credential = selective_set
        self.seed_plaintext("Bad.extension", token="ghp_bad")

        credentials.migrate_legacy_credentials()
        credentials.set_credential = real_set

        self.assertEqual(
            "ghp_good", credentials.get_credential("Good.extension").secret
        )
        self.assertEqual('"ghp_bad"', self.user_config.raw("Bad.extension", "token"))
