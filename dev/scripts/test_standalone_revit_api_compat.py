"""Tests for the Revit API compatibility checker and its catalog builder."""

import io
import json
import shutil
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

try:
    from . import build_revit_api_catalog as builder
    from . import check_revit_api_compat as checker
except ImportError:
    import build_revit_api_catalog as builder
    import check_revit_api_compat as checker

YEARS = list(range(2021, 2028))

GENERATED = {
    "years": YEARS,
    "types": {
        "Autodesk.Revit.DB.ElementId": {
            "kind": "class",
            "members": {
                "IntegerValue": {
                    "kind": "property",
                    "avail": [[2021, 2025]],
                    "obsolete": {
                        "since": 2024,
                        "message": "This property is deprecated in Revit 2024. "
                        "Please use the Value property instead.",
                    },
                },
                "Value": {"kind": "property", "avail": [[2024, 2027]]},
            },
        },
        "Autodesk.Revit.DB.DisplayUnitType": {"kind": "enum", "avail": [[2021, 2021]]},
        "Autodesk.Revit.DB.BuiltInParameterGroup": {
            "kind": "enum",
            "avail": [[2021, 2024]],
            "obsolete": {"since": 2024, "message": "Please use GroupTypeId instead."},
        },
        "Autodesk.Revit.DB.BindingMap": {
            "kind": "class",
            "members": {
                "Insert": {
                    "kind": "method",
                    "overload_params": {
                        "Autodesk.Revit.DB.BuiltInParameterGroup": [[2021, 2024]]
                    },
                }
            },
        },
        "Autodesk.Revit.DB.ColorFillScheme": {"kind": "class", "avail": [[2022, 2027]]},
        "Autodesk.Revit.DB.Mechanical.Zone": {
            "kind": "class",
            "members": {"Spaces": {"kind": "property", "avail": [[2021, 2026]]}},
        },
    },
    "instance_members": {
        "IntegerValue": {"avail": [[2021, 2025]], "obsolete_years": [[2024, 2025]]},
        "GetDataType": {"avail": [[2022, 2027]]},
        "ShowDialog": {"avail": [[2023, 2027]], "bcl": True},
        "Insert": {
            "overload_params": {
                "Autodesk.Revit.DB.BuiltInParameterGroup": [[2021, 2024]]
            },
            "bcl": True,
        },
    },
}

OVERRIDES = {
    "instance_members": {
        "IntegerValue": {"receiver_exempt": "(?i)(workset|field)(_?id)?$"}
    },
    "namespaces": {
        "System.Web.Script.Serialization": {"avail": [[2021, 2024]], "code": "DOTNET"}
    },
    "engine": {"cpython_unavailable_modules": {"wpf": "load XAML another way"}},
}


class _TempTree(unittest.TestCase):
    """Writes files into a throwaway directory and lints them."""

    def setUp(self):
        """Create an empty tree and the synthetic catalog."""
        self.root = Path(tempfile.mkdtemp(prefix="revit-api-compat-test-"))
        self.catalog = checker.Catalog(GENERATED, OVERRIDES)

    def tearDown(self):
        """Remove the tree."""
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, relative, text):
        """Write dedented text to a file under the tree and return its path."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
        return path

    def lint(self, source, relative="lib/module.py"):
        """Lint source written at relative; returns its findings."""
        path = self.write(relative, source)
        bundles = checker.BundleRanges(self.catalog.universe)
        return checker.check_file(path, self.catalog, bundles) + bundles.problems

    def codes(self, source, relative="lib/module.py"):
        """(code, severity) pairs for linted source."""
        return [(f.code, f.severity) for f in self.lint(source, relative)]


class MatchingTests(_TempTree):
    """References resolve to catalog entries through imports and aliases."""

    def test_qualified_removed_type_is_an_error(self):
        """A DB-qualified removed type is an exact match, hence an error."""
        findings = self.lint(
            "from pyrevit import DB\nx = DB.DisplayUnitType.DUT_METERS\n"
        )
        self.assertEqual(["API-MISSING"], [f.code for f in findings])
        self.assertIn("removed in Revit 2022", findings[0].message)
        self.assertEqual(checker.ERROR, findings[0].severity)

    def test_default_db_alias_without_import(self):
        """`DB` resolves even where a module receives it without an import."""
        self.assertEqual(
            [("API-MISSING", "error")], self.codes("x = DB.ColorFillScheme\n")
        )

    def test_import_of_removed_type_is_flagged_at_the_import(self):
        """The import itself fails in the missing years, so it is reported."""
        findings = self.lint("from Autodesk.Revit.DB import DisplayUnitType\n")
        self.assertEqual([1], [f.line for f in findings])

    def test_aliased_namespace_import(self):
        """`import Autodesk.Revit.DB as X` aliases resolve."""
        source = "import Autodesk.Revit.DB as RDB\nRDB.ColorFillScheme\n"
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_star_import_resolves_bare_names(self):
        """Bare names resolve through `from Autodesk.Revit.DB import *`."""
        source = "from Autodesk.Revit.DB import *\nDisplayUnitType\n"
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_locally_bound_name_is_not_resolved_by_star_import(self):
        """A local binding shadows a star-imported API name."""
        source = (
            "from Autodesk.Revit.DB import *\nDisplayUnitType = 1\nDisplayUnitType\n"
        )
        self.assertEqual([], self.codes(source))

    def test_nested_namespace_member(self):
        """Sub-namespaces such as DB.Mechanical resolve to their types."""
        source = "from pyrevit import DB\nDB.Mechanical.Zone.Spaces\n"
        findings = self.lint(source)
        self.assertEqual(["API-MISSING"], [f.code for f in findings])
        self.assertIn("Zone.Spaces", findings[0].message)

    def test_pyrevit_revit_reexport(self):
        """`revit.DB` from pyrevit is the Revit DB namespace."""
        source = "from pyrevit import revit\nrevit.DB.ColorFillScheme\n"
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_instance_member_reported_when_no_type_has_it(self):
        """A bare attribute no Revit type has in some year is reported."""
        self.assertEqual(
            [("API-MISSING", "error")],
            self.codes("def f(d):\n    return d.GetDataType()\n"),
        )

    def test_instance_name_shared_with_dotnet_is_skipped(self):
        """Names that .NET types share are too ambiguous to report."""
        self.assertEqual([], self.codes("def f(dialog):\n    dialog.ShowDialog()\n"))

    def test_receiver_exemption(self):
        """receiver_exempt skips WorksetId-like receivers, not ElementId-like ones."""
        self.assertEqual(
            [], self.codes("def f(workset):\n    workset.Id.IntegerValue\n")
        )
        self.assertEqual(
            ["API-MISSING"],
            [c for c, _ in self.codes("def f(sheet):\n    sheet.Id.IntegerValue\n")],
        )

    def test_receiver_exemption_needs_the_name_to_end_in_the_keyword(self):
        """A receiver merely containing "field" is still an ElementId."""
        self.assertEqual(
            [], self.codes("def f(field_id):\n    field_id.IntegerValue\n")
        )
        self.assertEqual(
            ["API-MISSING"],
            [
                c
                for c, _ in self.codes(
                    "def f(field_element):\n    field_element.Id.IntegerValue\n"
                )
            ],
        )

    def test_own_class_attributes_are_not_api_inside_the_class(self):
        """Attributes a class defines are not Revit API uses within that class."""
        source = """
        class Wrapper(object):
            def GetDataType(self):
                return 1

            def same(self, other):
                return other.GetDataType()
        """
        self.assertEqual([], self.codes(source))

    def test_own_class_attributes_are_not_api_on_its_instances(self):
        """An instance built from the module's own class keeps its attributes."""
        source = """
        class Wrapper(object):
            def GetDataType(self):
                return 1

        def f():
            w = Wrapper()
            return w.GetDataType()
        """
        self.assertEqual([], self.codes(source))

    def test_own_class_attribute_does_not_hide_other_receivers(self):
        """A class declaring a name does not hide its use on a Revit object."""
        source = """
        class Wrapper(object):
            def GetDataType(self):
                return 1

        def f(definition):
            return definition.GetDataType()
        """
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_getattr_with_literal_name_and_no_default_counts_as_access(self):
        """A getattr with a literal name and no default is a plain access."""
        self.assertEqual(
            ["API-MISSING"],
            [c for c, _ in self.codes("def f(e):\n    getattr(e, 'IntegerValue')\n")],
        )

    def test_removed_overload_reported_once(self):
        """A removed overload is one finding, not one per argument type use."""
        source = """
        from pyrevit import DB
        def f(bmap, d, b):
            bmap.Insert(d, b, DB.BuiltInParameterGroup.PG_DATA)
        """
        findings = self.lint(source)
        self.assertEqual(["API-OVERLOAD"], [f.code for f in findings])
        self.assertIn("removed in Revit 2025", findings[0].message)

    def test_dotnet_namespace(self):
        """An import from a .NET-Framework-only namespace is one DOTNET finding."""
        source = "from System.Web.Script.Serialization import JavaScriptSerializer\n"
        self.assertEqual([("DOTNET", "error")], self.codes(source))


class VersionGuardTests(_TempTree):
    """Runtime version checks narrow the years a use can execute in."""

    def assertGuarded(self, source):
        """Assert source produces no findings."""
        self.assertEqual([], self.codes(textwrap.dedent(source)))

    def assertFlagged(self, source, count=1):
        """Assert source produces count findings."""
        self.assertEqual(count, len(self.codes(textwrap.dedent(source))))

    def test_is_newer_than_branches(self):
        """is_newer_than narrows the body to later years and else to earlier."""
        self.assertGuarded(
            """
            from pyrevit import HOST_APP, DB
            if HOST_APP.is_newer_than(2021):
                x = DB.ColorFillScheme
            else:
                y = DB.DisplayUnitType
            """
        )

    def test_is_newer_than_or_equal(self):
        """or_equal, positional or keyword, includes the year itself."""
        self.assertGuarded(
            "if HOST_APP.is_newer_than(2022, or_equal=True):\n    DB.ColorFillScheme\n"
        )
        self.assertGuarded(
            "if HOST_APP.is_newer_than(2022, True):\n    DB.ColorFillScheme\n"
        )
        self.assertFlagged("if HOST_APP.is_newer_than(2020):\n    DB.ColorFillScheme\n")

    def test_is_older_than_and_is_exactly(self):
        """is_older_than/is_exactly narrow; a negated is_exactly does not help."""
        self.assertGuarded("if HOST_APP.is_older_than(2022):\n    DB.DisplayUnitType\n")
        self.assertGuarded("if HOST_APP.is_exactly(2021):\n    DB.DisplayUnitType\n")
        self.assertFlagged(
            "if not HOST_APP.is_exactly(2021):\n    DB.DisplayUnitType\n"
        )

    def test_ternary_and_boolean_chain(self):
        """Ternaries and and/or short-circuits narrow their operands."""
        self.assertGuarded(
            "def f(e):\n"
            "    return e.Value if HOST_APP.is_newer_than(2023) else e.IntegerValue\n"
        )
        self.assertGuarded(
            "def f(d):\n    return HOST_APP.is_newer_than(2021) and d.GetDataType()\n"
        )
        self.assertGuarded(
            "def f(d):\n    return HOST_APP.is_older_than(2022) or d.GetDataType()\n"
        )

    def test_version_comparisons(self):
        """Comparisons of version-like values with years narrow; others do not."""
        self.assertGuarded("if revit_version > 2022:\n    DB.ColorFillScheme\n")
        self.assertGuarded(
            "if 2022 <= int(HOST_APP.version):\n    DB.ColorFillScheme\n"
        )
        self.assertGuarded(
            "if app.VersionNumber in ('2021',):\n    DB.DisplayUnitType\n"
        )
        self.assertGuarded("if 2021 < rvt_year < 2027:\n    DB.ColorFillScheme\n")
        self.assertFlagged("if python_version > 2022:\n    DB.ColorFillScheme\n")

    def test_version_flag_variable(self):
        """A name bound once to a version test narrows like the test."""
        self.assertGuarded(
            """
            IS_2022 = HOST_APP.is_newer_than(2021)
            def f():
                if IS_2022:
                    return DB.ColorFillScheme
            """
        )

    def test_netcore_flag(self):
        """NETFRAMEWORK/NETCORE map to Revit years before/after 2025."""
        self.assertGuarded(
            "from pyrevit.compat import NETCORE\n"
            "if not NETCORE:\n"
            "    from System.Web.Script.Serialization import JavaScriptSerializer\n"
        )

    def test_early_exit_narrows_the_rest_of_the_block(self):
        """return, script.exit() and exitscript=True alerts narrow what follows."""
        self.assertGuarded(
            """
            def f(e):
                if HOST_APP.is_older_than(2024):
                    return None
                return e.Value
            """
        )
        self.assertGuarded(
            """
            if HOST_APP.is_older_than(2022):
                forms.alert("needs 2022", exitscript=True)
            x = DB.ColorFillScheme
            """
        )
        self.assertGuarded(
            "if HOST_APP.is_older_than(2022):\n    script.exit()\nDB.ColorFillScheme\n"
        )

    def test_unrelated_condition_does_not_guard(self):
        """An arbitrary condition is not a version guard."""
        self.assertFlagged("if selection:\n    DB.ColorFillScheme\n")


class FeatureGuardTests(_TempTree):
    """hasattr/getattr probes and try/except fallbacks protect both paths."""

    def test_hasattr_guards_both_branches(self):
        """A hasattr probe narrows both branches to the probed API's years."""
        self.assertEqual(
            [],
            self.codes(
                "def f(e):\n"
                "    if hasattr(e, 'Value'):\n"
                "        return e.Value\n"
                "    return e.IntegerValue\n"
            ),
        )

    def test_feature_probe_variable(self):
        """A variable holding a getattr probe acts as a feature guard."""
        source = """
        def f(e):
            probe = getattr(e, "GetDataType", None)
            if probe is None:
                raise RuntimeError("unsupported")
            return e.GetDataType()
        """
        self.assertEqual([], self.codes(source))

    def test_try_attribute_error_guards_body_and_handler(self):
        """A handler runs only in the years its try body fails."""
        source = """
        def f(e):
            try:
                return e.Value
            except AttributeError:
                return e.IntegerValue
        """
        self.assertEqual([], self.codes(source))

    def test_unrelated_handler_does_not_guard(self):
        """A handler that cannot catch a missing member is no guard."""
        source = """
        def f(d):
            try:
                return d.GetDataType()
            except ValueError:
                return None
        """
        self.assertEqual(1, len(self.codes(source)))

    def test_code_after_failed_attempt_is_a_fallback(self):
        """Code after a returning try with a swallowing handler is a fallback."""
        source = """
        def f(e):
            try:
                return e.IntegerValue
            except AttributeError:
                pass
            return e.Value
        """
        self.assertEqual([], self.codes(source))


class DeprecationTests(_TempTree):
    """Deprecations warn only where the author has not branched on version."""

    def test_deprecated_member_warns(self):
        """A deprecated, still present member is a warning."""
        path = self.write(
            "Ext.extension/T.tab/P.panel/B.pushbutton/script.py",
            "def f(e):\n    return e.IntegerValue\n",
        )
        self.write("Ext.extension/bundle.yaml", "max_revit_version: 2025\n")
        found = checker.check_file(
            path, self.catalog, checker.BundleRanges(self.catalog.universe)
        )
        self.assertEqual(
            [("API-DEPRECATED", "warning")], [(f.code, f.severity) for f in found]
        )

    def test_version_branch_silences_deprecation(self):
        """Deprecations inside a version branch are already handled."""
        source = "if HOST_APP.is_older_than(2025):\n    BuiltInParameterGroup = DB.BuiltInParameterGroup\n"
        self.assertEqual([], self.codes(source))


class BundleRangeTests(_TempTree):
    """Effective ranges mirror the C# loader's precedence and intersection."""

    BUTTON = "Ext.extension/T.tab/P.panel/B.pushbutton/script.py"

    def years(self, relative):
        """Effective years and bundle problems for a file."""
        bundles = checker.BundleRanges(self.catalog.universe)
        years, _ = bundles.years_for(self.root / relative)
        return sorted(years), bundles.problems

    def test_bundle_caps_the_script(self):
        """max_revit_version in bundle.yaml removes the failing years."""
        self.write(self.BUTTON, "DB.DisplayUnitType\n")
        self.write(
            "Ext.extension/T.tab/P.panel/B.pushbutton/bundle.yaml",
            "max_revit_version: 2021\n",
        )
        self.assertEqual([], self.codes("DB.DisplayUnitType\n", self.BUTTON))

    def test_script_dunder_applies_when_bundle_is_silent(self):
        """__min_revit_ver__ applies when bundle.yaml has no value."""
        self.write(self.BUTTON, "__min_revit_ver__ = 2022\n")
        self.assertEqual(list(range(2022, 2028)), self.years(self.BUTTON)[0])

    def test_bundle_wins_over_script_dunder(self):
        """bundle.yaml takes precedence over the script dunder."""
        self.write(self.BUTTON, "__min_revit_ver__ = 2022\n")
        self.write(
            "Ext.extension/T.tab/P.panel/B.pushbutton/bundle.yaml",
            "min_revit_version: '2024'\n",
        )
        self.assertEqual(list(range(2024, 2028)), self.years(self.BUTTON)[0])

    def test_parent_ranges_intersect(self):
        """Extension, panel and button ranges intersect."""
        self.write(self.BUTTON, "pass\n")
        self.write("Ext.extension/bundle.yaml", "min_revit_version: 2023 # gate\n")
        self.write(
            "Ext.extension/T.tab/P.panel/bundle.yaml", "max_revit_version: 2025\n"
        )
        self.assertEqual([2023, 2024, 2025], self.years(self.BUTTON)[0])

    def test_extension_root_gates_its_lib(self):
        """The extension root bundle gates code under its lib/."""
        self.write("Ext.extension/lib/helpers.py", "pass\n")
        self.write("Ext.extension/bundle.yaml", "min_revit_version: 2026\n")
        self.assertEqual([2026, 2027], self.years("Ext.extension/lib/helpers.py")[0])

    def test_plain_folder_bundle_is_ignored(self):
        """The loader ignores bundle.yaml outside component folders."""
        self.write("Ext.extension/lib/helpers.py", "pass\n")
        self.write("Ext.extension/lib/bundle.yaml", "min_revit_version: 2026\n")
        self.assertEqual(YEARS, self.years("Ext.extension/lib/helpers.py")[0])

    def test_nested_yaml_keys_are_ignored(self):
        """Only top-level min/max keys count."""
        self.write(self.BUTTON, "pass\n")
        self.write(
            "Ext.extension/T.tab/P.panel/B.pushbutton/bundle.yaml",
            "engine:\n  min_revit_version: 2026\n",
        )
        self.assertEqual(YEARS, self.years(self.BUTTON)[0])

    def test_invalid_version_hides_the_component(self):
        """An unparseable year hides the component and is reported."""
        self.write(self.BUTTON, "pass\n")
        self.write(
            "Ext.extension/T.tab/P.panel/B.pushbutton/bundle.yaml",
            "min_revit_version: soon\n",
        )
        years, problems = self.years(self.BUTTON)
        self.assertEqual([], years)
        self.assertEqual(["BUNDLE"], [p.code for p in problems])

    def test_fix_mentions_bundle_only_inside_bundles(self):
        """bundle.yaml fixes are offered only for code inside bundles."""
        inside = self.lint("DB.DisplayUnitType\n", self.BUTTON)[0].fix
        outside = self.lint("DB.DisplayUnitType\n", "lib/module.py")[0].fix
        self.assertIn("max_revit_version: 2021", inside)
        self.assertIn("HOST_APP.is_older_than(2022)", outside)
        self.assertNotIn("max_revit_version", outside)


class SuppressionTests(_TempTree):
    """compat-ignore needs a reason and must be used."""

    def test_justified_suppression(self):
        """A justified pragma suppresses the finding on its line."""
        source = "DB.ColorFillScheme  # compat-ignore: only imported on 2022+\n"
        self.assertEqual([], self.codes(source))

    def test_suppression_on_statement_first_line(self):
        """A pragma on the statement's first line covers later lines."""
        source = "x = (  # compat-ignore: only imported on 2022+\n    DB.ColorFillScheme\n)\n"
        self.assertEqual([], self.codes(source))

    def test_pragma_survives_formatter_wrapped_header(self):
        """A pragma anywhere in a wrapped class header still applies."""
        source = (
            "class Handler(\n"
            "    DB.ColorFillScheme\n"
            "):  # compat-ignore: only imported on 2022+\n"
            "    pass\n"
        )
        self.assertEqual([], self.codes(source))

    def test_id_scoped_suppression(self):
        """An id list limits the pragma to those codes."""
        kept = self.codes(
            "DB.ColorFillScheme  # compat-ignore[API-OVERLOAD]: wrong id\n"
        )
        self.assertEqual(
            sorted([("API-MISSING", "error"), ("SUPPRESS", "warning")]), sorted(kept)
        )

    def test_missing_justification_is_an_error(self):
        """A pragma without a reason is itself an error."""
        self.assertIn(
            ("SUPPRESS", "error"), self.codes("DB.ColorFillScheme  # compat-ignore\n")
        )

    def test_unused_suppression_warns(self):
        """A pragma that suppresses nothing is reported as stale."""
        self.assertEqual(
            [("SUPPRESS", "warning")], self.codes("x = 1  # compat-ignore: stale\n")
        )


class EngineTests(_TempTree):
    """IronPython-only modules are flagged in CPython scripts."""

    def test_wpf_in_cpython_script(self):
        """`wpf` is IronPython-only, so a CPython script cannot import it."""
        self.assertEqual([("ENGINE", "error")], self.codes("#! python3\nimport wpf\n"))

    def test_wpf_in_ironpython_script(self):
        """IronPython scripts may import `wpf`."""
        self.assertEqual([], self.codes("import wpf\n"))

    def test_wpf_behind_ironpython_check(self):
        """An IRONPY branch never runs on CPython."""
        self.assertEqual([], self.codes("#! python3\nif IRONPY:\n    import wpf\n"))

    def test_python2_syntax_is_not_analyzed(self):
        """Unparseable files warn, and error when they claim CPython."""
        self.assertEqual([("PARSE", "warning")], self.codes("print 'hi'\n"))
        self.assertEqual([("PARSE", "error")], self.codes("#! python3\nprint 'hi'\n"))


class CliTests(_TempTree):
    """Exit codes and baseline round trip."""

    def run_main(self, *argv):
        """Run the CLI against the synthetic catalog; returns (code, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        catalog_path = self.root / "catalog.json"
        overrides_path = self.root / "overrides.json"
        catalog_path.write_text(json.dumps(GENERATED), encoding="utf-8")
        overrides_path.write_text(json.dumps(OVERRIDES), encoding="utf-8")
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(
                list(argv)
                + ["--catalog", str(catalog_path), "--overrides", str(overrides_path)]
            )
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes(self):
        """0 clean, 1 findings, 2 bad path."""
        clean = self.write("clean/a.py", "x = 1\n")
        dirty = self.write("dirty/a.py", "DB.DisplayUnitType\n")
        self.assertEqual(0, self.run_main(str(clean.parent))[0])
        self.assertEqual(1, self.run_main(str(dirty.parent))[0])
        self.assertEqual(2, self.run_main(str(self.root / "missing"))[0])

    def test_strict_fails_on_warnings(self):
        """Warnings pass unless --strict."""
        self.write("warn/Ext.extension/bundle.yaml", "max_revit_version: 2024\n")
        target = self.write(
            "warn/Ext.extension/lib/a.py", "x = DB.BuiltInParameterGroup\n"
        )
        self.assertEqual(0, self.run_main(str(target.parent))[0])
        self.assertEqual(1, self.run_main(str(target.parent), "--strict")[0])

    def test_baseline_round_trip(self):
        """Baselined findings pass; an extra occurrence fails."""
        target = self.write("dirty/a.py", "DB.DisplayUnitType\nDB.DisplayUnitType\n")
        baseline = self.root / "baseline.json"
        code, _, _ = self.run_main(
            str(target.parent), "--baseline", str(baseline), "--update-baseline"
        )
        self.assertEqual(0, code)
        self.assertEqual(
            0, self.run_main(str(target.parent), "--baseline", str(baseline))[0]
        )
        target.write_text("DB.DisplayUnitType\n" * 3, encoding="utf-8")
        self.assertEqual(
            1, self.run_main(str(target.parent), "--baseline", str(baseline))[0]
        )

    def test_json_and_github_formats(self):
        """Machine formats carry the findings."""
        target = self.write("dirty/a.py", "DB.DisplayUnitType\n")
        _, out, _ = self.run_main(str(target.parent), "--format", "json")
        findings = json.loads(out)["targets"][0]["findings"]
        self.assertEqual("API-MISSING", findings[0]["code"])
        _, out, _ = self.run_main(str(target.parent), "--format", "github")
        self.assertTrue(out.startswith("::error file="))

    def test_old_python_is_refused(self):
        """An interpreter older than the analysis floor exits 2 without linting."""
        target = self.write("dirty/a.py", "DB.DisplayUnitType\n")
        with mock.patch.object(checker.sys, "version_info", (3, 9, 0)):
            code, _, err = self.run_main(str(target.parent))
        self.assertEqual(2, code)
        self.assertIn("3.10", err)

    def test_update_baseline_needs_a_baseline_file(self):
        """--update-baseline alone is a usage error."""
        target = self.write("dirty/a.py", "x = 1\n")
        code, _, err = self.run_main(str(target.parent), "--update-baseline")
        self.assertEqual(2, code)
        self.assertIn("--baseline", err)

    def test_revit_years_restrict_the_universe(self):
        """--revit-years limits which years an unconstrained script must support."""
        target = self.write("dirty/a.py", "DB.DisplayUnitType\n")
        self.assertEqual(1, self.run_main(str(target.parent))[0])
        self.assertEqual(
            0, self.run_main(str(target.parent), "--revit-years", "2021")[0]
        )
        self.assertEqual(
            2, self.run_main(str(target.parent), "--revit-years", "1999")[0]
        )

    def test_revit_years_parser(self):
        """YEAR and YEAR-YEAR parse; malformed or empty ranges are rejected."""
        self.assertEqual(frozenset({2024}), checker._parse_year_range("2024"))
        self.assertEqual(
            frozenset({2023, 2024, 2025}), checker._parse_year_range(" 2023-2025 ")
        )
        for text in ("24", "2025-2023", "2023-", "abc"):
            with self.assertRaises(checker.argparse.ArgumentTypeError, msg=text):
                checker._parse_year_range(text)

    def test_exclude_skips_matching_files(self):
        """--exclude drops files matching the glob before linting."""
        target = self.write("dirty/skip_me.py", "DB.DisplayUnitType\n")
        self.assertEqual(1, self.run_main(str(target.parent))[0])
        code, _, err = self.run_main(str(target.parent), "--exclude", "*/skip_me.py")
        self.assertEqual(2, code)
        self.assertIn("scanned 0 files", err)

    def test_errors_only_hides_warnings(self):
        """--errors-only leaves warnings out of the report."""
        self.write("warn/Ext.extension/bundle.yaml", "max_revit_version: 2024\n")
        target = self.write(
            "warn/Ext.extension/lib/a.py", "x = DB.BuiltInParameterGroup\n"
        )
        _, out, _ = self.run_main(str(target.parent))
        self.assertIn("API-DEPRECATED", out)
        _, out, _ = self.run_main(str(target.parent), "--errors-only")
        self.assertNotIn("API-DEPRECATED", out)

    def test_remote_extensions_are_cloned_and_failures_reported(self):
        """--extensions all lints each clone and reports the ones that fail."""
        listing = self.root / "extensions.json"
        listing.write_text(
            json.dumps(
                {
                    "extensions": [
                        {"name": "Good", "url": "https://example.test/good.git"},
                        {"name": "Gone", "url": "https://example.test/gone.git"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        def fake_clone(url, destination, ref=None):
            """Materialize a clone for one URL and fail for the other."""
            if "gone" in url:
                raise OSError("repository not found")
            destination.mkdir(parents=True)
            (destination / "a.py").write_text("DB.DisplayUnitType\n", encoding="utf-8")

        keep = self.root / "kept"
        with (
            mock.patch.object(checker, "EXTENSIONS_CATALOG_PATH", listing),
            mock.patch.object(checker, "clone_repo", fake_clone),
        ):
            code, out, err = self.run_main(
                "--extensions", "all", "--keep-clones", str(keep), "--format", "json"
            )
        self.assertEqual(2, code, err)
        self.assertIn("incomplete", err)
        payload = json.loads(out)
        self.assertEqual(["Good"], [t["name"] for t in payload["targets"]])
        self.assertEqual(["Gone"], [f["name"] for f in payload["clone_failures"]])
        self.assertIn("repository not found", payload["clone_failures"][0]["error"])
        self.assertTrue((keep / "01-Good.extension" / "a.py").is_file())


class CatalogTests(_TempTree):
    """Catalog loading and lookups."""

    def test_obsolete_years_stay_inside_availability(self):
        """A deprecation year the API is already gone in is not reported."""
        entry = {"avail": [[2021, 2023]], "obsolete_years": [[2022, 2025]]}
        self.assertEqual(frozenset({2022, 2023}), self.catalog.obsolete_years(entry))

    def test_obsolete_without_since_is_rejected_at_load(self):
        """A curated obsolete block without 'since' fails load, not the lint."""
        broken = {
            "instance_members": {"Thing": {"obsolete": {"message": "gone"}}},
        }
        with self.assertRaises(ValueError):
            checker.Catalog(GENERATED, broken)
        generated = self.root / "catalog.json"
        overrides = self.root / "overrides.json"
        generated.write_text(json.dumps(GENERATED), encoding="utf-8")
        overrides.write_text(json.dumps(broken), encoding="utf-8")
        with self.assertRaises(ValueError):
            checker.Catalog.load(generated, overrides)

    def test_overrides_are_not_shared_between_catalogs(self):
        """Editing one catalog's namespaces leaves the source overrides alone."""
        catalog = checker.Catalog(GENERATED, OVERRIDES)
        catalog.namespaces.clear()
        catalog.cpython_unavailable_modules.clear()
        self.assertIn("System.Web.Script.Serialization", OVERRIDES["namespaces"])
        self.assertIn("wpf", OVERRIDES["engine"]["cpython_unavailable_modules"])

    def test_parse_message_does_not_depend_on_the_interpreter(self):
        """The unparseable-file message omits the interpreter's own wording."""
        findings = self.lint("def broken(:\n")
        self.assertEqual(
            "not analyzed: does not parse as Python 3; "
            "run check_py3_compat.py for the language axis",
            findings[0].message,
        )


class BuilderTests(unittest.TestCase):
    """The catalog diff, without downloading or reading assemblies."""

    def test_ranges(self):
        """Years compress to inclusive runs."""
        self.assertEqual(
            [[2021, 2023], [2026, 2026]], builder._ranges({2026, 2021, 2022, 2023})
        )

    def test_obsolete_message_decoding(self):
        """ObsoleteAttribute blobs decode with and without a message."""
        message = "Use X instead."
        blob = b"\x01\x00" + bytes([len(message)]) + message.encode() + b"\x00\x00"
        self.assertEqual(message, builder._obsolete_message(blob))
        self.assertEqual("", builder._obsolete_message(b"\x01\x00\x00\x00"))

    def test_signature_reader(self):
        """Method signature blobs decode to parameter type names."""
        blob = bytes([0x20, 0x02, 0x01, 0x08, 0x12, (5 << 2) | 1])
        names = {5: "Autodesk.Revit.DB.ForgeTypeId"}
        reader = builder._SignatureReader(
            blob, lambda tag, index: names[index] if tag == 1 else "?"
        )
        self.assertEqual(
            ["System.Int32", "Autodesk.Revit.DB.ForgeTypeId"], reader.method_params()
        )

    def test_signature_reader_skips_the_vararg_sentinel(self):
        """The sentinel before extra varargs is a marker; ParamCount covers all."""
        blob = bytes([0x05, 0x02, 0x01, 0x08, 0x41, 0x08])
        reader = builder._SignatureReader(blob, lambda tag, index: "?")
        self.assertEqual(["System.Int32", "System.Int32"], reader.method_params())

    def test_undecodable_overload_yields_no_overload_facts(self):
        """A method with an unreadable signature never claims a removed overload."""
        group = "Autodesk.Revit.DB.BuiltInParameterGroup"

        def surface(overloads, undecoded=False):
            """One year's surface with a BindingMap.Insert."""
            insert = {
                "kind": "method",
                "static": False,
                "obsolete": None,
                "overloads": overloads,
            }
            if undecoded:
                insert["undecoded_overload"] = True
            return {
                "Autodesk.Revit.DB.BindingMap": {
                    "kind": "class",
                    "obsolete": None,
                    "members": {"Insert": insert},
                }
            }

        readable = builder.build_catalog(
            {2021: [surface([[group]])], 2022: [surface([[]])]}, {}
        )
        self.assertIn(
            "overload_params",
            readable["types"]["Autodesk.Revit.DB.BindingMap"]["members"]["Insert"],
        )
        unreadable = builder.build_catalog(
            {2021: [surface([[group]])], 2022: [surface([[]], undecoded=True)]}, {}
        )
        self.assertEqual(
            {}, unreadable["types"].get("Autodesk.Revit.DB.BindingMap", {})
        )
        self.assertNotIn(
            "overload_params", unreadable["instance_members"].get("Insert", {})
        )

    def test_build_catalog_diff(self):
        """Per-year surfaces diff into availability, obsoletion and overloads."""

        def surface(members, extra=None):
            """Build a minimal per-year surface for the builder."""
            types = {
                "Autodesk.Revit.DB.ElementId": {
                    "kind": "class",
                    "obsolete": None,
                    "members": members,
                }
            }
            types.update(extra or {})
            return types

        prop = {"kind": "property", "static": False, "obsolete": None}
        old = dict(prop, obsolete="Please use the Value property instead.")
        insert_old = {
            "kind": "method",
            "static": False,
            "obsolete": None,
            "overloads": [["Autodesk.Revit.DB.BuiltInParameterGroup"], []],
        }
        insert_new = dict(insert_old, overloads=[[]])
        new_type = {
            "Autodesk.Revit.DB.ColorFillScheme": {
                "kind": "class",
                "obsolete": None,
                "members": {},
            }
        }
        surfaces = {
            2023: surface({"IntegerValue": prop, "Insert": insert_old}),
            2024: surface(
                {"IntegerValue": old, "Value": prop, "Insert": insert_new}, new_type
            ),
            2025: surface({"Value": prop, "Insert": insert_new}, new_type),
        }
        catalog = builder.build_catalog(
            {year: [surf] for year, surf in surfaces.items()}, {}, bcl_names={"Value"}
        )
        members = catalog["types"]["Autodesk.Revit.DB.ElementId"]["members"]
        self.assertEqual([[2023, 2024]], members["IntegerValue"]["avail"])
        self.assertEqual(2024, members["IntegerValue"]["obsolete"]["since"])
        self.assertEqual([[2024, 2025]], members["Value"]["avail"])
        self.assertEqual(
            {"Autodesk.Revit.DB.BuiltInParameterGroup": [[2023, 2023]]},
            members["Insert"]["overload_params"],
        )
        self.assertEqual(
            [[2024, 2025]],
            catalog["types"]["Autodesk.Revit.DB.ColorFillScheme"]["avail"],
        )
        self.assertTrue(catalog["instance_members"]["Value"]["bcl"])
        self.assertEqual(
            [[2024, 2024]],
            catalog["instance_members"]["IntegerValue"]["obsolete_years"],
        )

    def test_member_moved_to_base_is_not_a_removal(self):
        """A member that moves up to a base class stays available."""
        prop = {"kind": "property", "static": False, "obsolete": None}

        def surface(scope_members, base_members):
            """Build a minimal per-year surface for the builder."""
            return {
                "Autodesk.Revit.DB.EditScope": {
                    "kind": "class",
                    "base": "System.Object",
                    "obsolete": None,
                    "members": base_members,
                },
                "Autodesk.Revit.DB.StairsEditScope": {
                    "kind": "class",
                    "base": "Autodesk.Revit.DB.EditScope",
                    "obsolete": None,
                    "members": scope_members,
                },
            }

        catalog = builder.build_catalog(
            {
                2021: [surface({"IsPermitted": prop}, {})],
                2022: [surface({}, {"IsPermitted": prop})],
            },
            {},
        )
        stairs = catalog["types"].get("Autodesk.Revit.DB.StairsEditScope", {})
        self.assertNotIn("IsPermitted", stairs.get("members", {}))
        self.assertNotIn("IsPermitted", catalog["instance_members"])
        self.assertEqual(
            "Autodesk.Revit.DB.EditScope",
            catalog["bases"]["Autodesk.Revit.DB.StairsEditScope"],
        )
        base = catalog["types"]["Autodesk.Revit.DB.EditScope"]
        self.assertEqual([[2022, 2022]], base["members"]["IsPermitted"]["avail"])

    def test_api_added_in_an_update_is_partial(self):
        """An API only the later update of a year has is partial that year."""
        empty = {}
        step = {
            "Autodesk.Revit.DB.STEPImportOptions": {
                "kind": "class",
                "base": "System.Object",
                "obsolete": None,
                "members": {},
            }
        }
        catalog = builder.build_catalog(
            {2023: [empty], 2024: [empty, step], 2025: [step]}, {}
        )
        entry = catalog["types"]["Autodesk.Revit.DB.STEPImportOptions"]
        self.assertEqual([[2025, 2025]], entry["avail"])
        self.assertEqual([[2024, 2024]], entry["partial"])


class UpdateAndInheritanceTests(_TempTree):
    """Partial years and inherited members in the linter."""

    def setUp(self):
        """Extend the synthetic catalog with partial and inherited entries."""
        super().setUp()
        generated = json.loads(json.dumps(GENERATED))
        generated["types"]["Autodesk.Revit.DB.STEPImportOptions"] = {
            "kind": "class",
            "avail": [[2025, 2027]],
            "partial": [[2024, 2024]],
        }
        generated["types"]["Autodesk.Revit.DB.EditScope"] = {
            "kind": "class",
            "members": {
                "Brand": {"kind": "property", "static": True, "avail": [[2026, 2027]]}
            },
        }
        generated["types"]["Autodesk.Revit.DB.StairsEditScope"] = {
            "kind": "class",
            "base": "Autodesk.Revit.DB.EditScope",
            "avail": [[2022, 2027]],
        }
        self.catalog = checker.Catalog(generated, OVERRIDES)

    def test_partial_year_is_missing_with_a_feature_detection_hint(self):
        """Code requiring 2024 cannot rely on an API from a 2024 update."""
        findings = self.lint(
            "if HOST_APP.is_newer_than(2024, True):\n    DB.STEPImportOptions\n"
        )
        self.assertEqual(["API-MISSING"], [f.code for f in findings])
        self.assertIn("added in a Revit 2024 update", findings[0].message)
        self.assertIn("hasattr", findings[0].fix)

    def test_hasattr_covers_partial_years(self):
        """Feature detection is the guard that works across updates."""
        source = "if hasattr(DB, 'STEPImportOptions'):\n    DB.STEPImportOptions\n"
        self.assertEqual([], self.codes(source))

    def test_inherited_member_found_on_base(self):
        """A member accessed through a derived type is checked on its base."""
        source = "if HOST_APP.is_newer_than(2021):\n    DB.StairsEditScope.Brand\n"
        findings = self.lint(source)
        self.assertEqual(["API-MISSING"], [f.code for f in findings])
        self.assertIn("StairsEditScope.Brand", findings[0].message)


class ReviewRegressionTests(_TempTree):
    """Guard precision, scoping, inheritance and CLI fixes from PR review."""

    def setUp(self):
        """Extend the synthetic catalog with inheritance and partial data."""
        super().setUp()
        generated = json.loads(json.dumps(GENERATED))
        generated["types"]["Autodesk.Revit.DB.STEPImportOptions"] = {
            "kind": "class",
            "avail": [[2025, 2027]],
            "partial": [[2024, 2024]],
        }
        generated["types"]["Autodesk.Revit.DB.Element"] = {
            "kind": "class",
            "members": {"GetParameter": {"kind": "method", "avail": [[2022, 2027]]}},
        }
        generated["bases"] = {
            "Autodesk.Revit.DB.Wall": "Autodesk.Revit.DB.HostObject",
            "Autodesk.Revit.DB.HostObject": "Autodesk.Revit.DB.Element",
        }
        self.generated = generated
        self.catalog = checker.Catalog(generated, OVERRIDES)

    def test_probe_does_not_protect_other_apis(self):
        """A probe for one API leaves unrelated APIs in its branch checked."""
        source = "if hasattr(DB, 'ColorFillScheme'):\n    DB.STEPImportOptions\n"
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_probe_true_branch_is_limited_to_its_years(self):
        """Inside a probe for a 2022+ API, a 2021-only API is flagged."""
        source = "if hasattr(DB, 'ColorFillScheme'):\n    DB.DisplayUnitType\n"
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_probe_false_branch_is_limited_to_missing_years(self):
        """The else of a probe for a 2022+ API runs on 2021 only."""
        source = (
            "if hasattr(DB, 'ColorFillScheme'):\n"
            "    x = DB.ColorFillScheme\n"
            "else:\n"
            "    x = DB.DisplayUnitType\n"
        )
        self.assertEqual([], self.codes(source))

    def test_handler_without_cataloged_failure_is_checked(self):
        """A handler for unrelated errors gets no exemption."""
        source = "try:\n    x = 1 / 0\nexcept Exception:\n    DB.ColorFillScheme\n"
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_handler_runs_in_the_failing_years(self):
        """A fallback for a 2022+ API may use the API removed after 2021."""
        source = (
            "try:\n"
            "    x = DB.ColorFillScheme\n"
            "except AttributeError:\n"
            "    x = DB.DisplayUnitType\n"
        )
        self.assertEqual([], self.codes(source))

    def test_flags_resolve_per_function(self):
        """The same flag name in two functions resolves in each one."""
        source = """
        def a():
            supported = HOST_APP.is_newer_than(2021)
            if supported:
                return DB.ColorFillScheme

        def b():
            supported = HOST_APP.is_older_than(2023)
            if supported:
                return DB.ColorFillScheme
        """
        findings = self.lint(source)
        self.assertEqual(["API-MISSING"], [f.code for f in findings])
        self.assertEqual([9], [f.line for f in findings])

    def test_probe_variable_does_not_leak_into_another_function(self):
        """A parameter named like another function's probe is not a probe."""
        source = """
        def a(e):
            probe = hasattr(e, "ColorFillScheme")
            return probe

        def b(probe):
            if probe:
                return DB.ColorFillScheme
        """
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_function_in_try_body_is_not_guarded(self):
        """A def inside a try runs later, so neither absorbs nor narrows."""
        source = """
        try:
            def helper():
                return DB.ColorFillScheme
            x = 1
        except AttributeError:
            DB.DisplayUnitType
        """
        findings = self.lint(source)
        self.assertEqual(
            ["`ColorFillScheme`", "`DisplayUnitType`"],
            sorted(f.message.split(" ")[0] for f in findings),
        )

    def test_lambda_in_try_body_is_not_guarded(self):
        """A lambda body runs when called, outside the try."""
        source = """
        try:
            f = lambda: DB.ColorFillScheme
        except AttributeError:
            pass
        """
        self.assertEqual(["API-MISSING"], [c for c, _ in self.codes(source)])

    def test_class_body_in_try_keeps_the_guard(self):
        """A class body runs at definition, inside the try."""
        source = """
        try:
            class A(object):
                x = DB.ColorFillScheme
        except AttributeError:
            pass
        """
        self.assertEqual([], self.codes(source))

    def test_inherited_member_through_unchanged_classes(self):
        """Wall reaches Element.GetParameter through the bases map."""
        findings = self.lint("def f(w, p):\n    return DB.Wall.GetParameter(w, p)\n")
        self.assertEqual(["API-MISSING"], [f.code for f in findings])
        self.assertIn("added in Revit 2022", findings[0].message)

    def test_github_annotation_escapes_properties(self):
        """Commas and colons in a path are escaped in the file property."""
        finding = checker.Finding(
            self.root / "A, B.pushbutton" / "script.py",
            3,
            1,
            "API-MISSING",
            checker.ERROR,
            "50%\ndone",
        )
        out = io.StringIO()
        with redirect_stdout(out):
            checker._print_github([finding], self.root)
        line = out.getvalue().strip()
        self.assertIn("file=A%2C B.pushbutton/script.py,", line)
        self.assertTrue(line.endswith("::50%25%0Adone"))

    def run_cli(self, fake_clone, *argv):
        """Run the CLI with clone_repo replaced; returns the exit code."""
        catalog_path = self.root / "catalog.json"
        overrides_path = self.root / "overrides.json"
        catalog_path.write_text(json.dumps(self.generated), encoding="utf-8")
        overrides_path.write_text(json.dumps(OVERRIDES), encoding="utf-8")
        original = checker.clone_repo
        checker.clone_repo = fake_clone
        err = io.StringIO()
        try:
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(err):
                code = checker.main(
                    list(argv)
                    + [
                        "--catalog",
                        str(catalog_path),
                        "--overrides",
                        str(overrides_path),
                        "--format",
                        "json",
                    ]
                )
        finally:
            checker.clone_repo = original
        self.assertNotIn("cannot load catalog", err.getvalue())
        return code, out.getvalue()

    def test_same_named_repositories_get_separate_checkouts(self):
        """Two URLs ending in the same name are both cloned and linted."""

        def fake_clone(url, destination, ref=None):
            """Stand-in for clone_repo that writes a tiny checkout."""
            destination.mkdir(parents=True)
            body = "DB.DisplayUnitType\n" if "team-a" in url else "x = 1\n"
            (destination / "a.py").write_text(body, encoding="utf-8")

        code, out = self.run_cli(
            fake_clone,
            "--git-url",
            "https://example.invalid/team-a/Tools.git",
            "--git-url",
            "https://example.invalid/team-b/Tools.git",
        )
        targets = json.loads(out)["targets"]
        self.assertEqual([1, 0], [len(t["findings"]) for t in targets])
        self.assertEqual(1, code)

    def test_failed_clone_fails_the_run(self):
        """A failed clone makes the scan incomplete, even if others pass."""

        def fake_clone(url, destination, ref=None):
            """Stand-in for clone_repo that writes a tiny checkout."""
            if "broken" in url:
                raise OSError("unreachable")
            destination.mkdir(parents=True)
            (destination / "a.py").write_text("x = 1\n", encoding="utf-8")

        code, _ = self.run_cli(
            fake_clone,
            "--git-url",
            "https://example.invalid/ok.git",
            "--git-url",
            "https://example.invalid/broken.git",
        )
        self.assertEqual(2, code)

    def test_bad_baseline_is_reported_before_cloning(self):
        """A missing baseline aborts before any clone is made."""
        calls = []

        def fake_clone(url, destination, ref=None):
            """Stand-in for clone_repo that writes a tiny checkout."""
            calls.append(url)

        code, _ = self.run_cli(
            fake_clone,
            "--git-url",
            "https://example.invalid/ok.git",
            "--baseline",
            str(self.root / "missing.json"),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)


class ShippedCatalogTests(unittest.TestCase):
    """The committed catalog covers the known version breaks.

    These pin facts read from Autodesk's assemblies; if a regeneration changes
    one, check it against the Revit "What's New" notes before updating here.
    """

    @classmethod
    def setUpClass(cls):
        """Load the committed catalog and overrides."""
        cls.catalog = checker.Catalog.load()

    def avail(self, type_name, member=None):
        """Sorted available years of a DB type or member."""
        entry = self.catalog.types["Autodesk.Revit.DB." + type_name]
        if member:
            entry = entry["members"][member]
        return sorted(self.catalog.avail(entry))

    def test_years_are_contiguous_from_2021(self):
        """The catalog spans every year from 2021 without gaps."""
        self.assertEqual(2021, self.catalog.years[0])
        self.assertEqual(
            list(range(2021, self.catalog.years[-1] + 1)), self.catalog.years
        )

    def test_known_breaks(self):
        """The documented version breaks are present with the right years."""
        self.assertEqual(
            list(range(2021, 2026)), self.avail("ElementId", "IntegerValue")
        )
        self.assertEqual(2024, self.avail("ElementId", "Value")[0])
        self.assertEqual([2021], self.avail("DisplayUnitType"))
        self.assertEqual([2021], self.avail("UnitType"))
        self.assertEqual([2021, 2022], self.avail("ParameterType"))
        self.assertEqual(list(range(2021, 2025)), self.avail("BuiltInParameterGroup"))
        self.assertEqual(2022, self.avail("GroupTypeId")[0])
        self.assertEqual(
            list(range(2021, 2025)), self.avail("Definition", "ParameterGroup")
        )
        self.assertEqual([2021, 2022], self.avail("Revision", "NumberType"))
        self.assertEqual(2022, self.avail("Revision", "RevisionNumberingSequenceId")[0])
        self.assertEqual(2022, self.avail("ColorFillScheme")[0])
        insert = self.catalog.types["Autodesk.Revit.DB.BindingMap"]["members"]["Insert"]
        self.assertEqual(
            [[2021, 2024]],
            insert["overload_params"]["Autodesk.Revit.DB.BuiltInParameterGroup"],
        )

    def test_mismatches_seen_in_revit_2024_are_resolved(self):
        """Regressions from running the hosted catalog test in Revit 2024."""
        stairs = self.catalog.types.get("Autodesk.Revit.DB.StairsEditScope", {})
        self.assertNotIn("IsPermitted", stairs.get("members", {}))
        step = self.catalog.types["Autodesk.Revit.DB.STEPImportOptions"]
        self.assertIn(2024, self.catalog.partial(step))

    def test_unchanged_apis_are_absent(self):
        """APIs with no 2021+ change are not cataloged."""
        for name in ("Transaction", "SubTransaction", "ExternalResourceReference"):
            self.assertNotIn("Autodesk.Revit.DB." + name, self.catalog.types)

    def test_pyrevit_shims_pass(self):
        """The version shims in pyrevitlib are recognized as guarded."""
        bundles = checker.BundleRanges(self.catalog.universe)
        for relative in (
            "pyrevitlib/pyrevit/revit/db/ensure.py",
            "pyrevitlib/pyrevit/revit/units.py",
            "pyrevitlib/pyrevit/compat.py",
        ):
            path = checker.REPO_ROOT / relative
            self.assertTrue(path.is_file(), relative)
            findings = checker.check_file(path, self.catalog, bundles)
            self.assertEqual([], [str(f) for f in findings], relative)


if __name__ == "__main__":
    sys.exit(unittest.main())
