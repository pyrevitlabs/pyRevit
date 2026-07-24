# -*- coding: utf-8 -*-
"""Round-trip tests for the pyRevit Python config bridge.

Exercises the encode/decode logic in :mod:`pyrevit.coreutils.configparser`
(``ConfigSection`` / ``ConfigSections``), which every script touches through
``script.get_config()``. The C# store already has parity/encoding coverage; the
untested risk lives in the Python side: the JSON round-trip, the legacy
single-quote fallback, and the missing-key-vs-stored-empty-string distinction.

A dict-backed fake ``IConfiguration`` models the C# contract (raw strings in,
``None`` only for a missing key) so the tests are hermetic: they never touch the
user's real config file, disk, or install-scope detection, and run identically
under IronPython 2/3 and CPython.

Run from Revit via the pyRevit DevTools "Config Module Tests" button.
"""

import unittest

from pyrevit.coreutils.configparser import ConfigSection, ConfigSections


class _FakeConfiguration(object):
    """In-memory stand-in for the C# IConfiguration used by ConfigSection.

    Stores raw string values keyed by (section, key) and returns the supplied
    default (``None`` for a missing key) exactly as the real backend does, so
    the Python decode branches are exercised without the labs assemblies.
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
        removed = [k for k in self._store if k[0] == section]
        for key in removed:
            del self._store[key]
        if section in self._sections:
            self._sections.remove(section)
            return True
        return False

    def GetSectionNames(self):
        return list(self._sections)

    def GetSectionOptionNames(self, section):
        return [key for (sec, key) in self._store if sec == section]


class _FakeConfigurationService(object):
    """Minimal service that hands every configuration name the same config."""

    DefaultConfigurationName = "Default"

    def __init__(self, configuration):
        self._configuration = configuration

    def __getitem__(self, _configuration_name):
        return self._configuration


class ConfigSectionRoundTripTests(unittest.TestCase):
    """Typed values survive a set_option/get_option round-trip unchanged."""

    def setUp(self):
        self.config = _FakeConfiguration()
        self.section = ConfigSection("core", self.config)

    def _roundtrip(self, value):
        self.section.set_option("key", value)
        return self.section.get_option("key")

    def test_string_round_trips(self):
        self.assertEqual("hello", self._roundtrip("hello"))

    def test_int_round_trips(self):
        self.assertEqual(10, self._roundtrip(10))

    def test_bool_true_round_trips(self):
        self.assertIs(True, self._roundtrip(True))

    def test_bool_false_round_trips(self):
        self.assertIs(False, self._roundtrip(False))

    def test_list_round_trips(self):
        value = [r"C:\Tools\ext1", r"D:\ext2"]
        self.assertEqual(value, self._roundtrip(value))

    def test_dict_round_trips(self):
        value = {"master": r"C:\Users\u\pyRevit-Master"}
        self.assertEqual(value, self._roundtrip(value))

    def test_unicode_round_trips(self):
        # ensure_ascii=False must preserve non-ASCII rather than \uXXXX-escaping
        # or mangling it (guards against the known IPY3 stdout mojibake class).
        value = u"café"
        self.assertEqual(value, self._roundtrip(value))

    def test_string_is_stored_as_canonical_compact_json(self):
        # Matches the C# symmetric-JSON encoding: quoted, no incidental spaces.
        self.section.set_option("key", "hello")
        self.assertEqual('"hello"', self.config.GetRawValueOrDefault("core", "key"))

    def test_dict_is_stored_as_compact_json(self):
        self.section.set_option("key", {"a": 1})
        self.assertEqual('{"a":1}', self.config.GetRawValueOrDefault("core", "key"))


class ConfigSectionToleranceTests(unittest.TestCase):
    """Legacy/bare values decode without raising, per the documented fallback."""

    def setUp(self):
        self.config = _FakeConfiguration()
        self.section = ConfigSection("core", self.config)

    def test_legacy_single_quoted_string_is_decoded(self):
        self.config.SetRawValue("core", "key", "'hello'")
        self.assertEqual("hello", self.section.get_option("key"))

    def test_legacy_single_quoted_list_is_decoded(self):
        self.config.SetRawValue("core", "key", "['a','b']")
        self.assertEqual(["a", "b"], self.section.get_option("key"))

    def test_bare_windows_path_returned_as_is(self):
        raw = r"C:\Tools\ext"
        self.config.SetRawValue("core", "key", raw)
        self.assertEqual(raw, self.section.get_option("key"))

    def test_bare_python_bool_token_returned_as_string(self):
        # A non-JSON "True" is tolerated as the raw string rather than crashing;
        # it is intentionally not coerced to a Python bool.
        self.config.SetRawValue("core", "key", "True")
        self.assertEqual("True", self.section.get_option("key"))


class ConfigSectionMissingVsEmptyTests(unittest.TestCase):
    """Only a missing key falls back to the default; a stored value never does."""

    def setUp(self):
        self.config = _FakeConfiguration()
        self.section = ConfigSection("core", self.config)

    def test_missing_key_returns_default(self):
        self.assertIsNone(self.section.get_option("absent"))

    def test_missing_key_returns_supplied_default(self):
        self.assertEqual(
            "fallback", self.section.get_option("absent", default_value="fallback")
        )

    def test_stored_empty_string_is_a_real_value_not_default(self):
        self.section.set_option("key", "")
        self.assertEqual("", self.section.get_option("key", default_value="fallback"))

    def test_raw_empty_string_is_not_treated_as_missing(self):
        # A key present with an empty raw value is a real value; it must not
        # collapse to the default the way an absent key does.
        self.config.SetRawValue("core", "key", "")
        self.assertEqual("", self.section.get_option("key", default_value="fallback"))


class ConfigSectionMutationTests(unittest.TestCase):
    """has_option / remove_option reflect the backing store."""

    def setUp(self):
        self.config = _FakeConfiguration()
        self.section = ConfigSection("core", self.config)

    def test_has_option_true_after_set(self):
        self.section.set_option("key", "value")
        self.assertTrue(self.section.has_option("key"))

    def test_remove_option_removes_the_key(self):
        self.section.set_option("key", "value")
        self.assertTrue(self.section.remove_option("key"))
        self.assertFalse(self.section.has_option("key"))

    def test_remove_missing_option_returns_false(self):
        self.assertFalse(self.section.remove_option("absent"))


class ConfigSectionsTests(unittest.TestCase):
    """The section container resolves and manages sections on the default config."""

    def setUp(self):
        self.config = _FakeConfiguration()
        self.service = _FakeConfigurationService(self.config)
        self.sections = ConfigSections(self.service)

    def test_get_section_round_trips_a_value(self):
        section = self.sections.add_section("mytool")
        section.set_option("enabled", True)
        self.assertIs(True, self.sections.get_section("mytool").get_option("enabled"))

    def test_has_section_reflects_stored_keys(self):
        self.sections.add_section("mytool").set_option("enabled", True)
        self.assertTrue(self.sections.has_section("mytool"))
        self.assertFalse(self.sections.has_section("other"))

    def test_added_section_is_visible_before_any_option_is_set(self):
        self.sections.add_section("mytool")
        self.assertTrue(self.sections.has_section("mytool"))
        self.assertEqual("mytool", self.sections.get_section("mytool").header)

    def test_remove_section_clears_all_its_keys(self):
        section = self.sections.add_section("mytool")
        section.set_option("a", 1)
        section.set_option("b", 2)
        self.sections.remove_section("mytool")
        self.assertFalse(self.sections.has_section("mytool"))

    def test_get_missing_section_raises(self):
        # A missing section must not resolve to an empty section object, so
        # callers can tell "absent" from "present but empty".
        self.assertRaises(AttributeError, self.sections.get_section, "absent")

    def test_attribute_access_returns_an_existing_section(self):
        self.sections.add_section("mytool").set_option("x", "y")
        self.assertEqual("y", self.sections.mytool.get_option("x"))

    def test_attribute_access_to_missing_section_raises(self):
        # getattr-with-default and hasattr rely on __getattr__ raising.
        self.assertRaises(AttributeError, getattr, self.sections, "absent")
        self.assertEqual("fallback", getattr(self.sections, "absent", "fallback"))
        self.assertFalse(hasattr(self.sections, "absent"))
