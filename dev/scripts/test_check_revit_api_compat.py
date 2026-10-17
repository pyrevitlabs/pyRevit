"""Tests for the Revit API compatibility checker and its catalog builder."""

import io
import json
import shutil
import sys
import tempfile
import textwrap
import unittest
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
    "instance_members": {"IntegerValue": {"receiver_exempt": "(?i)workset"}},
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

    def test_own_class_attributes_are_not_api(self):
        """Attributes the module defines itself are not Revit API uses."""
        source = """
        class Wrapper(object):
            def GetDataType(self):
                return 1

        def f(w):
            return w.GetDataType()
        """
        self.assertEqual([], self.codes(source))

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
        """A hasattr test protects both the probed path and its fallback."""
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
        """An AttributeError handler protects the attempt and the fallback."""
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

    def test_build_catalog_diff(self):
        """Per-year surfaces diff into availability, obsoletion and overloads."""

        def surface(members, extra=None):
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
            findings = [
                f
                for f in checker.check_file(path, self.catalog, bundles)
                if f.severity == checker.ERROR
            ]
            self.assertEqual([], [str(f) for f in findings], relative)


if __name__ == "__main__":
    sys.exit(unittest.main())
