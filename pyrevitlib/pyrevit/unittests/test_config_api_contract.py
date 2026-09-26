# -*- coding: utf-8 -*-
"""Runtime tests for the Python config API contract.

Pins the behavior clauses of ``docs/config-api.md`` that source analysis
cannot see, all of them on a typed section reached through
``user_config.core``:

* a declared C# property wins over a raw option of the same name, on read and
  on write;
* a name that is not a declared property is stored as a raw option rather than
  rejected - which is what makes ``user_config.core.set_option()`` necessary
  and what makes the snake_case spelling silently ineffective;
* the escape hatches are symmetric with ``ConfigSection``, so a value written
  through one reads back through the other.

The typed-property/raw-option precedence is the sharp edge called out in the
contract: ``user_config.core.rocket_mode = True`` succeeds, writes a key no
reader looks at, and leaves ``RocketMode`` alone. These tests make that
explicit so adopting strictness later is a visible diff rather than a silent
behavior change.

The fakes model the C# contract - the wrapper asks the section's CLR type
whether a name belongs to the schema, and writes declared names through the
service while undeclared ones become raw options. They are hermetic: no user
config, no disk, no labs assemblies, so this runs identically under IronPython
2/3 and CPython.

Run from Revit via the pyRevit DevTools "Config Module Tests" button.
"""

import json
import unittest

from pyrevit.userconfig import _SectionCompatWrapper


class _FakeConfiguration(object):
    """In-memory stand-in for the C# IConfiguration.

    Returns the supplied default (None for a missing key) exactly as the real
    backend does, so the wrapper's decode and fallback branches are exercised
    without the labs assemblies.
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


class _FakeTypedSection(object):
    """Stand-in for a typed C# section, modelling a small schema.

    The wrapper resolves a name against ``GetType().GetProperty`` to decide
    typed versus raw, so declaring the real property names is what lets the
    tests distinguish the two paths.

    Class-level ``None`` defaults model the C# record: ``type(section)()`` is how
    the wrapper builds the pending record for a write, and every unassigned
    property reads back as null there rather than raising.
    """

    DECLARED = ("RocketMode", "UserLocale", "OutputStyleSheet")
    KEYS = {
        "RocketMode": "rocketmode",
        "UserLocale": "user_locale",
        "OutputStyleSheet": "outputstylesheet",
    }

    RocketMode = None
    UserLocale = None
    OutputStyleSheet = None

    def __init__(self, **values):
        for name, value in values.items():
            if name not in self.DECLARED:
                raise AttributeError(name)
            setattr(self, name, value)

    class _Type(object):
        def GetProperty(self, name):
            return name if name in _FakeTypedSection.DECLARED else None

    def GetType(self):
        return self._Type()


class _FakeService(object):
    """Service that keeps the last applied record and writes it to the store.

    Modeling the write-through matters: a typed-property write is supposed to
    land in the backing config under the section's key name, which is the only
    way a raw reader can see the same value.
    """

    def __init__(self, configuration, typed_section, read_only=False):
        self.Configuration = configuration
        self.ReadOnly = read_only
        self._typed = typed_section
        self.applied = []

    def ApplySection(self, pending):
        self.applied.append(pending)
        for name in _FakeTypedSection.DECLARED:
            value = getattr(pending, name, None)
            setattr(self._typed, name, value)
            if value is not None:
                self.Configuration.SetRawValue(
                    "core",
                    _FakeTypedSection.KEYS[name],
                    json.dumps(value, separators=(",", ":"), ensure_ascii=False),
                )


class TypedSectionContractTests(unittest.TestCase):
    """A declared property wins over a raw option of the same name."""

    def setUp(self):
        """Build a writable [core] wrapper over a fake typed section."""
        self.config = _FakeConfiguration()
        self.typed = _FakeTypedSection(RocketMode=False)
        self.service = _FakeService(self.config, self.typed)
        self.core = _SectionCompatWrapper("core", self.typed, self.config, self.service)

    def test_typed_property_is_read_from_the_section(self):
        """PascalCase is the canonical spelling, so it must resolve to the schema."""
        self.assertIs(False, self.core.RocketMode)

    def test_typed_property_write_reaches_the_service(self):
        """A typed write is not a raw-option write; it has to reach the store."""
        self.core.RocketMode = True
        self.assertIs(True, self.typed.RocketMode)
        self.assertIs(True, self.core.get_option("rocketmode"))

    def test_typed_property_beats_a_raw_option_of_the_same_name(self):
        """A stale raw key from a hand-edited file must not shadow the schema."""
        self.config.SetRawValue("core", "RocketMode", "true")
        self.assertIs(False, self.core.RocketMode)

    def test_typed_property_write_does_not_create_a_raw_option(self):
        """Nothing lands under the property name; the key on disk is the section's."""
        self.core.RocketMode = True
        self.assertFalse(self.core.has_option("RocketMode"))

    def test_snake_case_spelling_is_stored_as_a_raw_option(self):
        """The sharp edge: the write succeeds silently and never reaches RocketMode."""
        self.core.rocket_mode = True
        self.assertIs(True, self.core.rocket_mode)
        self.assertIs(False, self.typed.RocketMode)
        self.assertTrue(self.core.has_option("rocket_mode"))

    def test_unknown_attribute_read_raises_only_when_no_raw_option_exists(self):
        """Absence is the only raise; permissiveness is what makes the hatch work."""
        with self.assertRaises(AttributeError):
            self.core.notakey

    def test_raw_option_is_readable_by_attribute(self):
        """A stored raw option answers to attribute access, as a script expects."""
        self.core.set_option("custom", "value")
        self.assertEqual("value", self.core.custom)

    def test_raw_option_write_bypasses_the_service(self):
        """A raw write is stored verbatim and never applied as a section record."""
        self.core.custom = "value"
        self.assertEqual([], self.service.applied)
        self.assertEqual("value", self.core.get_option("custom"))


class EscapeHatchParityTests(unittest.TestCase):
    """A typed section and a ConfigSection share one decode and one store."""

    def setUp(self):
        """Pair a [core] wrapper with a ConfigSection over the same store."""
        from pyrevit.coreutils.configparser import ConfigSection

        self.config = _FakeConfiguration()
        self.typed = _FakeTypedSection(RocketMode=True)
        self.service = _FakeService(self.config, self.typed)
        self.core = _SectionCompatWrapper("core", self.typed, self.config, self.service)
        self.section = ConfigSection("core", self.config)

    def test_value_written_through_one_reads_through_the_other(self):
        """Extensions hold whichever of the two a given entry point handed them."""
        self.core.set_option("custom", {"a": 1})
        self.assertEqual({"a": 1}, self.section.get_option("custom"))

    def test_value_written_through_a_section_reads_through_the_typed_section(self):
        """A script's own section and a built-in section cannot diverge."""
        self.section.set_option("custom", [1, 2])
        self.assertEqual([1, 2], self.core.get_option("custom"))

    def test_typed_property_write_is_visible_to_the_raw_reader(self):
        """A typed write lands under the section key, so a raw reader sees it."""
        self.core.RocketMode = True
        self.assertIs(True, self.section.get_option("rocketmode"))

    def test_legacy_bool_reads_the_same_through_both(self):
        """One decoder serves both, so neither reports a legacy False as truthy."""
        self.config.SetRawValue("core", "custom", "False")
        self.assertIs(False, self.core.get_option("custom"))
        self.assertIs(False, self.section.get_option("custom"))


class ReadOnlyContractTests(unittest.TestCase):
    """An admin-locked config drops writes rather than reporting a false success."""

    def setUp(self):
        """Build a read-only [core] wrapper over a fake typed section."""
        self.config = _FakeConfiguration()
        self.typed = _FakeTypedSection(RocketMode=False)
        self.service = _FakeService(self.config, self.typed, read_only=True)
        self.core = _SectionCompatWrapper("core", self.typed, self.config, self.service)

    def test_typed_property_write_is_skipped(self):
        """save_changes skips the flush, so a write accepted here would be a lie."""
        self.core.RocketMode = True
        self.assertEqual([], self.service.applied)
        self.assertIs(False, self.typed.RocketMode)

    def test_snake_case_write_is_skipped_too(self):
        """The raw fallback is a write path too, so it is dropped by the same guard."""
        self.core.rocket_mode = True
        self.assertFalse(self.core.has_option("rocket_mode"))

    def test_existing_values_still_read(self):
        """Read-only means writes are dropped, not that the config goes dark."""
        self.config.SetRawValue("core", "custom", "true")
        self.assertIs(True, self.core.get_option("custom"))


if __name__ == "__main__":
    unittest.main()
