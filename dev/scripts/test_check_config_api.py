"""Regression tests for the config API naming contract checker.

The checker in :mod:`check_config_api` is the enforcement half of the contract
in ``docs/config-api.md``. A checker that silently stopped detecting anything
would be worse than no checker, so every finding code is exercised here against
a synthetic violation, and the real tree is asserted clean.

Run with any CPython 3::

    pipenv run test-config-api

No pyRevit, no Revit, and no labs assemblies are needed; everything here is
source analysis.
"""

import ast
import tempfile
import unittest
from pathlib import Path

try:
    from . import check_config_api
except ImportError:
    import check_config_api

SCHEMA = {
    "core": {
        "BrandNew",
        "Debug",
        "MinHostDriveFreeSpace",
        "OutputStyleSheet",
        "RocketMode",
    },
    "routes": {"Host", "Port", "RoutesPort", "Status"},
    "telemetry": {"AppTelemetryStatus", "TelemetryUseUtcTimeStamps"},
}

CORE_SECTION_SOURCE = (
    '[SectionName("core")]\n'
    "public sealed record CoreSection\n"
    "{\n"
    '    [KeyName("rocketmode")]\n'
    "    public bool? RocketMode { get; set; }\n"
    '    [KeyName("minhostdrivefreespace")]\n'
    "    public long? MinHostDriveFreeSpace { get; set; }\n"
    "}\n"
)


def _config_source(body):
    """Wrap property definitions in a minimal PyRevitConfig class."""
    return "class PyRevitConfig(object):\n" + "".join(
        "    {}\n".format(line) for line in body
    )


def _classify(body):
    """Return classify_config_class output for a synthetic PyRevitConfig."""
    return check_config_api.classify_config_class(ast.parse(_config_source(body)))


def _codes(findings):
    """Return the finding codes of a list of findings."""
    return [f.code for f in findings]


def _codes_for(findings, alias):
    """Return the finding codes that concern one alias.

    A synthetic PyRevitConfig declares a handful of properties, so a full-
    contract run also reports every other documented alias as missing. Each test
    narrows to the alias it is about rather than restating the whole inventory
    as fixture data.
    """
    marker = "user_config.{} ".format(alias)
    return [f.code for f in findings if marker in f.message]


def _message_for(findings, alias):
    """Return the finding message concerning one alias, or None."""
    marker = "user_config.{} ".format(alias)
    for finding in findings:
        if marker in finding.message:
            return finding.message
    return None


def _alias_codes(bare, static, alias, derived=None, dynamic_dispatch=True):
    """Run the alias checks over a synthetic mapping and narrow to one alias."""
    findings = check_config_api._check_aliases(
        SCHEMA, bare, static, derived or set(), dynamic_dispatch, {}
    )
    return _codes_for(findings, alias)


def _write_source(source, name="tool.py"):
    """Write source into a throwaway directory and return the directory."""
    directory = Path(tempfile.mkdtemp())
    (directory / name).write_text(source, encoding="utf-8")
    return directory


def _core_schema():
    """Return the schema parsed from a minimal [core] section file."""
    return check_config_api.load_section_schema(
        _write_source(CORE_SECTION_SOURCE, "CoreSection.cs")
    )


class PascalCaseRuleTests(unittest.TestCase):
    """The mechanical rule that covers 20 of the 31 bare delegations."""

    def test_single_segment_name_is_capitalized(self):
        """A one-word alias converts by capitalizing its only part."""
        self.assertEqual("RocketMode", check_config_api.pascal_case("rocket_mode"))

    def test_multi_segment_name_capitalizes_every_part(self):
        """Underscore-separated parts each contribute a capitalized segment."""
        self.assertEqual(
            "UserCanConfig", check_config_api.pascal_case("user_can_config")
        )

    def test_already_cased_segment_keeps_its_inner_capital(self):
        """PascalCase cannot recover a segment boundary.

        This is why the mechanical rule covers 20 of the 31 delegations and
        not the other 11.
        """
        self.assertEqual(
            "MinHostDrivefreespace",
            check_config_api.pascal_case("min_host_drivefreespace"),
        )

    def test_contract_counts_match_the_documented_inventory(self):
        """31 bare delegations split 20 mechanical / 11 renames.

        These are the numbers issue #3645 states, so drift here means the
        published page and the code disagree.
        """
        mechanical = [
            alias
            for alias, (_section, prop) in check_config_api.BARE_DELEGATIONS.items()
            if prop == check_config_api.pascal_case(alias)
        ]
        self.assertEqual(31, len(check_config_api.BARE_DELEGATIONS))
        self.assertEqual(11, len(check_config_api.RENAMED_ALIASES))
        self.assertEqual(20, len(mechanical))

    def test_flat_alias_total_is_thirty_five(self):
        """31 delegations plus 2 section-derived plus 2 non-section aliases."""
        self.assertEqual(35, len(check_config_api.FLAT_ALIASES))

    def test_every_documented_rename_still_needs_an_explicit_mapping(self):
        """A rename whose target is now mechanical is a stale entry.

        Listing the 11 marks exactly the ones a spelling rule cannot derive, so
        a retargeted alias has to change this list too.
        """
        for alias in check_config_api.RENAMED_ALIASES:
            _section, prop = check_config_api.BARE_DELEGATIONS[alias]
            self.assertNotEqual(
                check_config_api.pascal_case(alias),
                prop,
                "user_config.{} no longer needs an explicit mapping".format(alias),
            )

    def test_rename_set_matches_what_the_code_actually_needs(self):
        """The rename set is derived, not trusted.

        Recomputing it from the code is what keeps the constant and the mapping
        from drifting apart.
        """
        needed = frozenset(
            alias
            for alias, (_section, prop) in check_config_api.BARE_DELEGATIONS.items()
            if prop != check_config_api.pascal_case(alias)
        )
        self.assertEqual(check_config_api.RENAMED_ALIASES, needed)

    def test_derived_aliases_are_not_renames(self):
        """log_level and output_close_mode_enum compute rather than delegate.

        No spelling rule applies to them.
        """
        for alias in check_config_api.SECTION_DERIVED_ALIASES:
            self.assertNotIn(alias, check_config_api.RENAMED_ALIASES)


class SchemaParseTests(unittest.TestCase):
    """The C# side of the contract is read from the section schema files."""

    def test_section_attribute_becomes_the_ini_section_key(self):
        """The schema is keyed by section, not by file name.

        The Python alias names the section, so the key has to be that string.
        """
        self.assertIn("core", _core_schema())

    def test_properties_are_collected_by_declared_name(self):
        """Targets are compared by C# property name.

        That is the whole point of cross-referencing the two sides.
        """
        self.assertEqual(
            {"RocketMode", "MinHostDriveFreeSpace"}, _core_schema()["core"]
        )

    def test_record_declaration_is_not_mistaken_for_a_property(self):
        """The type name has the same shape as a property line.

        The pattern must not match it.
        """
        self.assertNotIn("CoreSection", _core_schema()["core"])

    def test_section_without_a_name_attribute_is_skipped(self):
        """ExtensionSection carries no [SectionName].

        It is resolved per extension, so it is not part of this contract.
        """
        source = (
            "public sealed record ExtensionSection\n"
            "{\n"
            "    public bool? Disabled { get; set; }\n"
            "}\n"
        )
        schema = check_config_api.load_section_schema(
            _write_source(source, "ExtensionSection.cs")
        )
        self.assertEqual({}, schema)

    def test_missing_directory_raises(self):
        """An empty schema must not read as a clean run.

        Returning one silently would make every alias check pass for the wrong
        reason.
        """
        with self.assertRaises(FileNotFoundError):
            check_config_api.load_section_schema(Path(tempfile.gettempdir()) / "nope")

    def test_typed_sections_without_a_schema_are_reported(self):
        """A directory holding only [core] leaves routes and telemetry unvalidated.

        That has to be said rather than compared against nothing.
        """
        directory = _write_source(CORE_SECTION_SOURCE, "CoreSection.cs")
        _schema, findings = check_config_api._check_schema(directory)
        self.assertEqual(["SCHEMA-MISSING", "SCHEMA-MISSING"], _codes(findings))


class BareDelegationTests(unittest.TestCase):
    """Only a single-expression getter counts as a bare delegation."""

    def test_bare_return_is_a_delegation(self):
        """The 31 delegations are exactly this shape."""
        _line, bare, _static, _derived, _dyn = _classify(
            ["@property", "def rocket_mode(self):", "    return self.core.RocketMode"]
        )
        self.assertEqual({"rocket_mode": ("core", "RocketMode")}, bare)

    def test_docstring_does_not_defeat_detection(self):
        """Every alias in the tree carries a docstring.

        One that hid the return would empty the whole mapping.
        """
        _line, bare, _static, _derived, _dyn = _classify(
            [
                "@property",
                "def rocket_mode(self):",
                '    """Whether to enable rocket mode."""',
                "    return self.core.RocketMode",
            ]
        )
        self.assertIn("rocket_mode", bare)

    def test_converted_read_is_derived_not_a_bare_delegation(self):
        """output_close_mode_enum wraps its property in a converter.

        That makes it a computed alias and not a naming case.
        """
        _line, bare, static, derived, _dyn = _classify(
            [
                "@property",
                "def output_close_mode_enum(self):",
                "    return PyRevit.PyRevitConfigs.ToCloseOutputMode("
                "self.core.CloseOutputMode)",
            ]
        )
        self.assertEqual({}, bare)
        self.assertIn("output_close_mode_enum", derived)
        self.assertIn("output_close_mode_enum", static)

    def test_two_property_read_is_derived(self):
        """log_level derives from Debug and Verbose.

        No single property can be its target.
        """
        _line, _bare, _static, derived, _dyn = _classify(
            [
                "@property",
                "def log_level(self):",
                "    return PyRevit.PyRevitConfigs.ToLoggingLevel("
                "self.core.Debug, self.core.Verbose)",
            ]
        )
        self.assertIn("log_level", derived)

    def test_identity_property_is_neither_delegation_nor_derived(self):
        """is_readonly exposes the service's own state.

        Treating it as a section alias would be a category error.
        """
        _line, bare, static, derived, _dyn = _classify(
            [
                "@property",
                "def is_readonly(self):",
                "    return self.config_service.ReadOnly",
            ]
        )
        self.assertEqual({}, bare)
        self.assertIn("is_readonly", static)
        self.assertNotIn("is_readonly", derived)

    def test_private_property_is_excluded_from_the_public_surface(self):
        """A private helper is not a published spelling.

        Policing it as one would put the module internals under the frozen
        alias policy.
        """
        _line, _bare, static, _derived, _dyn = _classify(
            ["@property", "def _secret(self):", "    return self.core.RocketMode"]
        )
        self.assertNotIn("_secret", static)

    def test_plain_method_is_not_a_property(self):
        """get_ext_root_dirs and friends are methods.

        Folding them into the property surface would make the contract
        unreadable.
        """
        _line, _bare, static, _derived, _dyn = _classify(
            ["def get_ext_root_dirs(self):", "    return []"]
        )
        self.assertNotIn("get_ext_root_dirs", static)

    def test_getattr_is_reported_as_dynamic_dispatch(self):
        """PyRevitConfig defines __getattr__ for sections.

        That is what makes a non-declared alias ambiguous rather than simply
        absent.
        """
        _line, _bare, _static, _derived, dyn = _classify(
            [
                "def __getattr__(self, name):",
                "    return self.config_sections.__getattr__(name)",
            ]
        )
        self.assertTrue(dyn)

    def test_missing_class_raises(self):
        """A missing class raises rather than reporting 35 aliases gone.

        Renaming PyRevitConfig would otherwise turn every alias into a
        disappearance, which reads as 35 findings rather than one cause.
        """
        with self.assertRaises(ValueError):
            check_config_api.classify_config_class(
                ast.parse("class Other(object):\n    pass\n")
            )


class AliasContractTests(unittest.TestCase):
    """Each alias finding code fires on the violation it names."""

    def test_current_tree_satisfies_the_contract(self):
        """The gate itself: if this fails, the contract and the code disagree."""
        source = (
            check_config_api.REPO_ROOT / check_config_api.USERCONFIG_REL
        ).read_text(encoding="utf-8")
        schema = check_config_api.load_section_schema(
            check_config_api.REPO_ROOT / check_config_api.SECTIONS_REL
        )
        line_of, bare, static, derived, dyn = check_config_api.classify_config_class(
            ast.parse(source)
        )
        findings = check_config_api._check_aliases(
            schema, bare, static, derived, dyn, line_of
        )
        self.assertEqual([], _codes(findings))

    def test_mechanical_delegation_is_accepted(self):
        """The 20 aliases the rule covers must not raise.

        Otherwise the check is unusable as a gate.
        """
        codes = _alias_codes(
            {"rocket_mode": ("core", "RocketMode")}, {"rocket_mode"}, "rocket_mode"
        )
        self.assertEqual([], codes)

    def test_documented_rename_is_accepted(self):
        """routes_port -> routes.Port is one of the 11 renames.

        The checker has to know that, or the cheapest correct alias looks like a
        defect.
        """
        codes = _alias_codes(
            {"routes_port": ("routes", "Port")}, {"routes_port"}, "routes_port"
        )
        self.assertEqual([], codes)

    def test_target_absent_from_the_schema_is_reported(self):
        """A C# rename nobody propagated leaves the alias reading nothing.

        Nothing else in the build would notice.
        """
        codes = _alias_codes(
            {"rocket_mode": ("core", "Gone")}, {"rocket_mode"}, "rocket_mode"
        )
        self.assertEqual(["ALIAS-SCHEMA"], codes)

    def test_schema_miss_explains_the_silent_failure(self):
        """The wrapper falls back to a raw option.

        A stale target therefore degrades to a missing setting rather than an
        error, and a reviewer has to learn that without reading userconfig.py.
        """
        findings = check_config_api._check_aliases(
            SCHEMA, {"rocket_mode": ("core", "Gone")}, {"rocket_mode"}, set(), True, {}
        )
        self.assertIn(
            "falls back to a raw option", _message_for(findings, "rocket_mode")
        )

    def test_schema_miss_suggests_the_mechanical_spelling(self):
        """Nearly every miss is a casing slip, and the fix is mechanical."""
        findings = check_config_api._check_aliases(
            SCHEMA,
            {"rocket_mode": ("core", "Rocketmode")},
            {"rocket_mode"},
            set(),
            True,
            {},
        )
        self.assertIn("RocketMode", _message_for(findings, "rocket_mode"))

    def test_undocumented_hand_mapping_is_reported(self):
        """Retargeting an alias is a naming decision.

        So is adding a new non-mechanical one, and both have to be written down
        like any other.
        """
        codes = _alias_codes(
            {"rocket_mode": ("core", "Debug")}, {"rocket_mode"}, "rocket_mode"
        )
        self.assertEqual(["ALIAS-RENAME"], codes)

    def test_rename_that_became_mechanical_is_reported(self):
        """A routes.Port rename upstream would make the documented entry redundant.

        The contract then needs updating rather than drifting.
        """
        codes = _alias_codes(
            {"routes_port": ("routes", "RoutesPort")}, {"routes_port"}, "routes_port"
        )
        self.assertEqual(["ALIAS-RENAME"], codes)

    def test_removed_alias_is_reported_as_dynamic(self):
        """PyRevitConfig defines __getattr__.

        A removed alias can therefore only resolve through it, which is the more
        precise verdict because it names the tooling cost.
        """
        self.assertEqual(["ALIAS-DYNAMIC"], _alias_codes({}, set(), "rocket_mode"))

    def test_dynamic_verdict_names_the_tooling_cost(self):
        """A dynamic alias is a removal in practice because tooling cannot see it.

        The message has to say so.
        """
        findings = check_config_api._check_aliases(SCHEMA, {}, set(), set(), True, {})
        self.assertIn("autocomplete", _message_for(findings, "rocket_mode"))

    def test_removed_alias_without_getattr_is_reported_as_gone(self):
        """With no __getattr__ there is no ambiguity: the alias is simply gone."""
        codes = _alias_codes({}, set(), "rocket_mode", dynamic_dispatch=False)
        self.assertEqual(["ALIAS-GONE"], codes)

    def test_identity_and_derived_properties_are_reported_as_gone(self):
        """Neither group can fall through __getattr__.

        Their disappearance is therefore unambiguous.
        """
        for alias in ("is_readonly", "log_level", "config_file"):
            self.assertEqual(["ALIAS-GONE"], _alias_codes({}, set(), alias), alias)

    def test_transformation_added_to_a_getter_is_reported(self):
        """A getter that stops being a bare read keeps answering the same way.

        Nothing else would flag that the contract changed.
        """
        codes = _alias_codes({}, {"rocket_mode"}, "rocket_mode")
        self.assertEqual(["ALIAS-SCHEMA"], codes)

    def test_undocumented_new_alias_is_reported(self):
        """A new alias is a new published spelling.

        The frozen policy is what makes that a finding rather than a
        preference.
        """
        codes = _alias_codes(
            {"brand_new": ("core", "BrandNew")}, {"brand_new"}, "brand_new"
        )
        self.assertEqual(["ALIAS-NEW"], codes)

    def test_dynamic_section_accessor_is_reported(self):
        """The typed-section surface has to stay explicit.

        That is what makes PascalCase discoverable.
        """
        findings = check_config_api._check_aliases(SCHEMA, {}, set(), set(), True, {})
        self.assertIn("SECTION-DYNAMIC", _codes(findings))


class EscapeHatchTests(unittest.TestCase):
    """The documented ways to reach a non-schema key stay declared."""

    def _trees(self):
        """Parse the two files that carry the escape hatches."""
        trees = {}
        for rel in (check_config_api.USERCONFIG_REL, check_config_api.CONFIGPARSER_REL):
            path = check_config_api.REPO_ROOT / rel
            trees[rel] = ast.parse(path.read_text(encoding="utf-8"))
        return trees

    def test_current_tree_declares_every_escape_hatch(self):
        """The contract promises these methods.

        Losing one is a breaking change even though no alias references it.
        """
        self.assertEqual(
            [], _codes(check_config_api._check_escape_hatches(self._trees()))
        )

    def test_missing_member_is_reported(self):
        """A half-declared hatch is still a contract break.

        Only get_option surviving would leave set_option callers with a
        read-only escape hatch.
        """
        source = ast.parse(
            "class ConfigSection(object):\n    def get_option(self, n):\n        pass\n"
        )
        findings = check_config_api._check_escape_hatches(
            {check_config_api.CONFIGPARSER_REL: source}
        )
        self.assertIn("ESCAPE-HATCH", _codes(findings))

    def test_missing_class_is_reported(self):
        """A renamed section class is a finding, not an empty pass.

        Renaming ConfigSection would otherwise leave the sections looking intact
        and empty.
        """
        findings = check_config_api._check_escape_hatches(
            {check_config_api.CONFIGPARSER_REL: ast.parse("x = 1\n")}
        )
        self.assertIn("ESCAPE-HATCH", _codes(findings))

    def test_missing_file_is_reported(self):
        """A moved module has to be a finding, not an empty pass."""
        findings = check_config_api._check_escape_hatches({})
        self.assertIn("ESCAPE-HATCH", _codes(findings))


class NamingTranslatorTests(unittest.TestCase):
    """A case translator in the bridge is the shape #3645 rejected."""

    MAPPING = (
        "PROPERTY_MAP = {\n"
        '    "rocket_mode": "RocketMode",\n'
        '    "routes_host": "Host",\n'
        "}\n"
    )

    def test_current_bridge_has_no_translator(self):
        """The decision is one spelling per setting.

        A translator would mint a second and hide both from tooling.
        """
        source = (
            check_config_api.REPO_ROOT / check_config_api.USERCONFIG_REL
        ).read_text(encoding="utf-8")
        self.assertEqual(
            [], _codes(check_config_api._check_no_naming_translator(ast.parse(source)))
        )

    def test_mapping_table_is_reported(self):
        """The table is the cheap version of the rejected option.

        Its typos are runtime AttributeErrors.
        """
        findings = check_config_api._check_no_naming_translator(ast.parse(self.MAPPING))
        self.assertEqual(["NAMING-TRANSLATOR"], _codes(findings))

    def test_conversion_helper_is_reported(self):
        """__getattr__-based conversion is the other rejected shape.

        It usually arrives as a helper first.
        """
        source = "def to_pascal_case(name):\n    return name.title()\n"
        findings = check_config_api._check_no_naming_translator(ast.parse(source))
        self.assertEqual(["NAMING-TRANSLATOR"], _codes(findings))

    def test_unrelated_dict_is_not_reported(self):
        """Ordinary config code must not trip the rule.

        A snake_case-keyed dict of plain defaults is neither half of a case
        translation.
        """
        source = 'DEFAULTS = {"host": "127.0.0.1", "port": 48884}\n'
        self.assertEqual(
            [], _codes(check_config_api._check_no_naming_translator(ast.parse(source)))
        )

    def test_all_caps_constant_is_not_reported(self):
        """Module constants are conventionally upper case.

        Matching them would make every constant in the file a finding.
        """
        source = "DEFAULT_CSV_SEPARATOR = ','\n"
        self.assertEqual(
            [], _codes(check_config_api._check_no_naming_translator(ast.parse(source)))
        )


class CallSiteTests(unittest.TestCase):
    """snake_case on a typed section silently stores a raw option."""

    def _scan(self, source):
        """Run the call-site check over a throwaway file."""
        directory = _write_source(source)
        return check_config_api.check_call_sites([directory], directory)

    def test_snake_case_attribute_on_a_typed_section_is_reported(self):
        """This is the footgun the contract documents.

        The write succeeds, does not raise, and never reaches the typed
        property.
        """
        findings = self._scan("user_config.core.rocket_mode = True\n")
        self.assertEqual(["SECTION-SNAKE"], _codes(findings))
        self.assertIn("raw option", findings[0].message)

    def test_pascal_case_attribute_is_accepted(self):
        """The canonical spelling has to stay clean or the gate is unusable."""
        self.assertEqual([], _codes(self._scan("user_config.core.RocketMode = True\n")))

    def test_documented_escape_hatch_methods_are_accepted(self):
        """get_option and set_option are snake_case by necessity.

        They mirror ConfigSection, and they are the sanctioned way to write a
        raw key.
        """
        source = (
            "user_config.core.get_option('userextensions')\n"
            "user_config.core.set_option('userextensions', [])\n"
        )
        self.assertEqual([], _codes(self._scan(source)))

    def test_bare_section_access_is_accepted(self):
        """Reading the section object itself is not a spelling mistake."""
        self.assertEqual([], _codes(self._scan("user_config.core.RocketMode\n")))

    def test_commented_out_line_is_ignored(self):
        """Commented code does not run, so it is not a live footgun."""
        self.assertEqual([], _codes(self._scan("# user_config.core.rocket_mode = 1\n")))

    def test_docstring_showing_the_antipattern_is_ignored(self):
        """Documenting the bad spelling is not using it.

        The contract page and the tests that pin it both have to show it.
        """
        source = '"""Example.\n\n    user_config.core.rocket_mode = True\n"""\n'
        self.assertEqual([], _codes(self._scan(source)))

    def test_call_sharing_a_line_with_a_string_argument_is_still_seen(self):
        """A call next to a string argument is still a call.

        Blanking the whole line instead of the literal would hide a real call that
        happens to sit beside a message string.
        """
        source = 'logger.info("Rocket mode", user_config.core.rocket_mode)\n'
        self.assertEqual(["SECTION-SNAKE"], _codes(self._scan(source)))

    def test_unparseable_source_does_not_raise(self):
        """A syntax error is another tool's problem to report.

        This check must not abort the whole scan.
        """
        directory = _write_source("def broken(:\n")
        findings = check_config_api.check_call_sites([directory], directory)
        self.assertEqual([], _codes(findings))

    def test_line_numbers_survive_blanking(self):
        """A finding that points at the wrong line is not actionable in review."""
        source = 'x = 1\n"""doc\n\n    more\n"""\nuser_config.core.rocket_mode = True\n'
        self.assertEqual([6], [f.line for f in self._scan(source)])

    def test_custom_section_is_ignored(self):
        """A script's own section is permissive by design.

        Only the three built-in typed sections have a schema to be strict about.
        """
        self.assertEqual([], _codes(self._scan("user_config.mytool.some_option = 1\n")))

    def test_current_tree_has_no_such_call_site(self):
        """The gate for the call-site half of the contract."""
        findings = check_config_api.check_call_sites(
            [Path(p) for p in check_config_api.DEFAULT_SCAN_ROOTS],
            check_config_api.REPO_ROOT,
        )
        self.assertEqual([], _codes(findings))


class CensusTests(unittest.TestCase):
    """The census separates reads from writes.

    A deprecation decision weighs the two differently: writes are the half that
    breaks silently.
    """

    def _census(self, source):
        """Run the census over a throwaway file."""
        directory = _write_source(source)
        return check_config_api.census_call_sites([directory], directory)

    def test_read_is_counted_as_a_read(self):
        """A read-only use site is the cheap half of a migration."""
        reads, writes = self._census("if user_config.rocket_mode:\n    pass\n")
        self.assertEqual({"rocket_mode": 1}, reads)
        self.assertEqual({}, writes)

    def test_write_is_counted_as_a_write(self):
        """A write is the half that has to keep working after any rename."""
        _reads, writes = self._census("user_config.rocket_mode = True\n")
        self.assertEqual({"rocket_mode": 1}, writes)

    def test_equality_comparison_is_a_read_not_a_write(self):
        """A second equals sign is a comparison.

        Counting it as a write would overstate the migration cost.
        """
        reads, writes = self._census("x = user_config.rocket_mode == 1\n")
        self.assertEqual({"rocket_mode": 1}, reads)
        self.assertEqual({}, writes)

    def test_unknown_attribute_is_not_counted(self):
        """The census feeds a deprecation estimate.

        Inventing entries for names that do not exist would inflate it.
        """
        reads, writes = self._census("user_config.whatever = 1\n")
        self.assertEqual({}, reads)
        self.assertEqual({}, writes)

    def test_current_tree_touches_every_alias_but_one(self):
        """cpython_engine_version is reached through self.

        The census naming the full first-party surface is therefore 34 of 35.
        """
        reads, writes = check_config_api.census_call_sites(
            [Path(p) for p in check_config_api.DEFAULT_SCAN_ROOTS],
            check_config_api.REPO_ROOT,
        )
        untouched = set(check_config_api.FLAT_ALIASES) - set(reads) - set(writes)
        self.assertEqual({"cpython_engine_version"}, untouched)


class FindingTests(unittest.TestCase):
    """A finding renders as one reviewable line."""

    def test_renders_path_line_code_and_message(self):
        """Reviewers act on this string, so its shape is part of the tool."""
        finding = check_config_api.Finding("ALIAS-NEW", "a/b.py", 12, "why")
        self.assertEqual("a/b.py:12: [ALIAS-NEW] why", str(finding))


if __name__ == "__main__":
    unittest.main()
