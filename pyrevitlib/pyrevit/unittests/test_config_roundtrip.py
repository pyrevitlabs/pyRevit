# -*- coding: utf-8 -*-
"""Round-trip tests for the pyRevit Python config bridge.

Exercises the encode/decode logic in :mod:`pyrevit.coreutils.configparser`
(``ConfigSection`` / ``ConfigSections``), which every script touches through
``script.get_config()``, and the matching surface on
``userconfig._SectionCompatWrapper``, which extensions reach through
``user_config.core``. Covers the Python side of the bridge: the JSON
round-trip, the legacy single-quote fallback, and the
missing-key-vs-stored-empty-string distinction.

A dict-backed fake ``IConfiguration`` models the C# contract (raw strings in,
``None`` only for a missing key) so most of these tests are hermetic: they never
touch the user's real config file, disk, or install-scope detection, and run
identically under IronPython 2/3 and CPython.

``RealBackendContractTests`` is the exception. It runs the same assertions
against the real INI backend over a temp file, so the fake cannot drift from the
contract it claims to model without something failing. It skips when the labs
assemblies are not loadable.

Run from Revit via the pyRevit DevTools "Config Module Tests" button.
"""

import os
import tempfile
import unittest

from pyrevit.coreutils.configparser import ConfigSection, ConfigSections
from pyrevit.userconfig import _SectionCompatWrapper


def _load_ini_backend():
    """Return the real IniConfiguration type, or None when it cannot be loaded."""
    try:
        from pyrevit.framework import clr

        clr.AddReference("pyRevitLabs.Configurations.Ini")
        from pyRevitLabs.Configurations.Ini import IniConfiguration

        return IniConfiguration
    except Exception:
        # An unavailable backend must skip the contract tests, not error the module.
        return None


_INI_BACKEND = _load_ini_backend()


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


class _FakeTypedSection(object):
    """Stand-in for a typed C# section, modelling a one-property schema.

    The wrapper asks the section's CLR type whether a name belongs to the
    schema, then writes declared names through the service and undeclared ones
    as raw options. Declaring exactly one name exercises both branches without
    the labs assemblies.
    """

    DECLARED = ("RocketMode",)

    class _Type(object):
        def GetProperty(self, name):
            return name if name in _FakeTypedSection.DECLARED else None

    def GetType(self):
        return self._Type()


class _FakeConfigurationService(object):
    """Minimal service that hands every configuration name the same config."""

    DefaultConfigurationName = "Default"

    def __init__(self, configuration, read_only=False):
        self._configuration = configuration
        self.ReadOnly = read_only
        self.applied = []

    def __getitem__(self, _configuration_name):
        return self._configuration

    def ApplySection(self, configuration_name, section_value):
        self.applied.append((configuration_name, section_value))


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


class ConfigSectionReloadTests(unittest.TestCase):
    """A section keeps writing to the live store after a reload swaps it.

    ``script.get_config()`` hands a section to a script, which may hold it
    across an unrelated ``user_config.reload()``. If the section stayed bound
    to the replaced store, its edits would be flushed from the wrong object
    and silently lost.
    """

    def setUp(self):
        self.config = _FakeConfiguration()
        self.service = _FakeConfigurationService(self.config)
        self.sections = ConfigSections(lambda: self.service)

    def _reload(self):
        """Swap in a fresh store the way PyRevitConfig.reload does."""
        self.config = _FakeConfiguration()
        self.service = _FakeConfigurationService(self.config)

    def test_section_writes_reach_the_store_that_replaced_the_original(self):
        section = self.sections.add_section("mytool")
        self._reload()
        section.set_option("enabled", True)
        self.assertEqual("true", self.config.GetRawValueOrDefault("mytool", "enabled"))

    def test_section_reads_see_the_replacing_store(self):
        section = self.sections.add_section("mytool")
        section.set_option("enabled", True)
        self._reload()
        self.config.SetRawValue("mytool", "enabled", "false")
        self.assertIs(False, section.get_option("enabled"))

    def test_subsection_also_follows_the_reload(self):
        subsection = self.sections.add_section("mytool").add_subsection("sub")
        self._reload()
        subsection.set_option("enabled", True)
        self.assertEqual(
            "true", self.config.GetRawValueOrDefault("mytool.sub", "enabled")
        )

    def test_direct_configuration_still_supported(self):
        # ConfigSection must still accept a plain configuration object, which is
        # what the C# service hands it outside the reload-aware path.
        config = _FakeConfiguration()
        section = ConfigSection("core", config)
        section.set_option("key", "value")
        self.assertEqual("value", section.get_option("key"))


class ConfigSubsectionTests(unittest.TestCase):
    """A subsection is discoverable as soon as it is added."""

    def setUp(self):
        self.config = _FakeConfiguration()
        self.section = ConfigSection("core", self.config)

    def test_added_subsection_is_visible_before_any_option_is_set(self):
        self.section.add_subsection("sub")
        self.assertTrue(self.section.has_subsection("sub"))
        self.assertEqual(
            ["core.sub"], [str(s) for s in self.section.get_subsections()]
        )

    def test_added_subsection_round_trips_a_value(self):
        self.section.add_subsection("sub").set_option("enabled", True)
        self.assertIs(
            True, self.section.get_subsection("sub").get_option("enabled")
        )


class SectionCompatWrapperTests(unittest.TestCase):
    """The typed-section wrapper decodes like ConfigSection does.

    Extensions hold whichever of the two a given entry point handed them, so a
    value stored through one must read back identically through the other.
    """

    def setUp(self):
        self.config = _FakeConfiguration()
        self.service = _FakeConfigurationService(self.config)
        self.wrapper = _SectionCompatWrapper(
            "core", _FakeTypedSection(), self.config, self.service, "Default"
        )
        self.section = ConfigSection("core", self.config)

    def test_bool_round_trips_as_bool(self):
        self.wrapper.set_option("key", False)
        self.assertIs(False, self.wrapper.get_option("key"))

    def test_legacy_python_bool_is_returned_as_is(self):
        # Matches the ConfigSection ladder: a bare, non-JSON value is passed
        # through rather than guessed at.
        self.config.SetRawValue("core", "key", "False")
        self.assertEqual("False", self.wrapper.get_option("key"))

    def test_list_round_trips(self):
        self.wrapper.set_option("key", ["a", "b"])
        self.assertEqual(["a", "b"], self.wrapper.get_option("key"))

    def test_missing_key_returns_default_value(self):
        self.assertEqual(
            "fallback", self.wrapper.get_option("absent", default_value="fallback")
        )

    def test_stored_empty_string_is_not_the_default(self):
        self.wrapper.set_option("key", "")
        self.assertEqual("", self.wrapper.get_option("key", default_value="fallback"))

    def test_matches_config_section_decoding(self):
        self.section.set_option("key", False)
        self.assertIs(
            self.section.get_option("key"), self.wrapper.get_option("key")
        )

    def test_typed_property_is_written_through_the_service(self):
        self.wrapper.RocketMode = True
        self.assertEqual(1, len(self.service.applied))
        _config_name, pending = self.service.applied[0]
        self.assertIs(True, pending.RocketMode)

    def test_typed_property_assigned_none_is_ignored(self):
        # None reaches neither the store nor the snapshot the service caches
        # process-wide; remove_option is how a stored key gets cleared.
        self.wrapper.RocketMode = None
        self.assertEqual([], self.service.applied)


class SectionCompatWrapperReadOnlyTests(unittest.TestCase):
    """An admin-locked config drops writes instead of reporting a false success.

    save_changes() skips the flush for a read-only config, so a write accepted
    here would be reported to the caller and then silently lost.
    """

    def setUp(self):
        self.config = _FakeConfiguration()
        self.service = _FakeConfigurationService(self.config, read_only=True)
        self.wrapper = _SectionCompatWrapper(
            "core", _FakeTypedSection(), self.config, self.service, "Default"
        )

    def test_typed_property_assignment_is_skipped(self):
        self.wrapper.RocketMode = True
        self.assertEqual([], self.service.applied)

    def test_set_option_stores_nothing(self):
        self.wrapper.set_option("key", "value")
        self.assertIsNone(self.wrapper.get_option("key"))

    def test_unknown_attribute_assignment_stores_nothing(self):
        self.wrapper.notaschemakey = "value"
        self.assertIsNone(self.wrapper.get_option("notaschemakey"))

    def test_remove_option_reports_no_removal(self):
        self.config.SetRawValue("core", "key", '"value"')
        self.assertIs(False, self.wrapper.remove_option("key"))
        self.assertEqual("value", self.wrapper.get_option("key"))


class RealBackendContractTests(unittest.TestCase):
    """Pins the IConfiguration behaviors that _FakeConfiguration models.

    The fake is hand-written, so nothing otherwise stops it from drifting from
    the real backend while every test above keeps passing. Each case here
    corresponds to a branch the Python decode ladder depends on.
    """

    def setUp(self):
        if _INI_BACKEND is None:
            self.skipTest("pyRevitLabs.Configurations.Ini is not loadable")
        handle, self.path = tempfile.mkstemp(suffix=".ini")
        os.close(handle)
        self.config = _INI_BACKEND.Create(self.path)

    def tearDown(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_missing_key_returns_the_supplied_default(self):
        self.assertEqual(
            "fallback", self.config.GetRawValueOrDefault("core", "absent", "fallback")
        )

    def test_stored_empty_value_is_not_the_default(self):
        self.config.SetRawValue("core", "key", "")
        self.assertEqual(
            "", self.config.GetRawValueOrDefault("core", "key", "fallback")
        )

    def test_raw_value_round_trips_verbatim(self):
        # Python owns its own encoding, so the backend must store the text as
        # handed over rather than re-encoding it.
        raw = '["C:\\\\Tools\\\\ext1"]'
        self.config.SetRawValue("core", "key", raw)
        self.assertEqual(raw, self.config.GetRawValueOrDefault("core", "key"))

    def test_set_raw_value_creates_the_section(self):
        self.assertFalse(self.config.HasSection("mytool"))
        self.config.SetRawValue("mytool", "key", "1")
        self.assertTrue(self.config.HasSection("mytool"))

    def test_remove_missing_option_returns_false(self):
        self.assertFalse(self.config.RemoveOption("core", "absent"))

    def test_config_section_round_trips_against_the_real_backend(self):
        section = ConfigSection("core", self.config)
        for value in (10, "hello", ["a", "b"], {"k": "v"}):
            section.set_option("key", value)
            self.assertEqual(value, section.get_option("key"))

    def test_bools_stay_bools_against_the_real_backend(self):
        # assertIs rather than assertEqual: True == 1, so an equality check
        # would accept a decode that handed back an int.
        section = ConfigSection("core", self.config)
        section.set_option("key", True)
        self.assertIs(True, section.get_option("key"))
        section.set_option("key", False)
        self.assertIs(False, section.get_option("key"))
