"""Regression tests for #4184: text that differs between engines.

IronPython 2.7 shows floats with 12 significant digits and widens the UTF-8
bytes of non-ASCII byte-string literals one by one (mojibake); CPython 3 and
IronPython 3.4 do neither. These checks inspect source without loading Revit.
"""

import ast
from pathlib import Path
import unittest

import pytest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

ROOT = Path(__file__).resolve().parents[4]
SETTINGS_WINDOW = ROOT / "pyrevitlib/pyrevit/forms/settings_window.py"
TOOLS = ROOT / "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel"
COORDINATE_SELECTOR = (
    TOOLS
    / "views.stack/Views.pulldown/Toggle Grid Bubbles by Direction.pushbutton"
    / "coordinate_selector.py"
)
GRID_BUBBLES = COORDINATE_SELECTOR.with_name("script.py")
KEYNOTES = TOOLS / "Keynotes.pushbutton/script.py"

KEYNOTES_ALLOWED_NON_ASCII = (
    "KeynoteManager | engine cfgs unavailable",
    "\N{BLACK CIRCLE}",
    "paste: %s dropped",
    "%s: could not read keynote tags",
    "Cannot connect to this project's keynote file.",
    "Converted ",
    "Backup failed ",
    "Keynote hierarchy cycle detected at key",
    "ui_guard: %s.%s not found",
    "KeynoteManager | no persistent engine",
)


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _load(path, names, kind):
    tree = _parse(path)
    nodes = [node for node in tree.body if isinstance(node, kind)]
    selected = [node for node in nodes if _defined_name(node) in names]
    missing = set(names) - {_defined_name(node) for node in selected}
    assert not missing, "%s not found in %s" % (sorted(missing), path.name)
    tree.body = selected
    namespace = {}
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


def _defined_name(node):
    if isinstance(node, ast.Assign):
        return getattr(node.targets[0], "id", "")
    return node.name


def _docstring_nodes(tree):
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
            ):
                docstrings.add(id(body[0].value))
    return docstrings


def _non_ascii_literals_outside_docstrings(tree):
    docstrings = _docstring_nodes(tree)
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and not node.value.isascii()
        and id(node) not in docstrings
    ]


@pytest.mark.regression
class FormatSettingValueTests(unittest.TestCase):
    """Issue 4184: floats must show the same text on every engine."""

    def setUp(self):
        namespace = _load(SETTINGS_WINDOW, {"_format_setting_value"}, ast.FunctionDef)
        self.format = namespace["_format_setting_value"]

    def test_long_float_is_cut_to_twelve_significant_digits(self):
        self.assertEqual(self.format(0.19685039370078738), "0.196850393701")

    def test_float_noise_is_hidden(self):
        self.assertEqual(self.format(0.1 + 0.2), "0.3")

    def test_whole_floats_keep_a_decimal_point(self):
        self.assertEqual(self.format(1.0), "1.0")
        self.assertEqual(self.format(100000.0), "100000.0")

    def test_exponent_forms_are_kept(self):
        self.assertEqual(self.format(1e16), "1e+16")
        self.assertEqual(self.format(1e-5), "1e-05")
        self.assertEqual(self.format(123456789012345.0), "1.23456789012e+14")

    def test_non_finite_floats_are_not_given_a_decimal_point(self):
        self.assertEqual(self.format(float("inf")), "inf")
        self.assertEqual(self.format(float("nan")), "nan")

    def test_other_types_use_str(self):
        self.assertEqual(self.format(5), "5")
        self.assertEqual(self.format("text"), "text")
        self.assertEqual(self.format(True), "True")

    def test_none_is_empty(self):
        self.assertEqual(self.format(None), "")


@pytest.mark.regression
class DegreeSignTests(unittest.TestCase):
    """Issue 4184: the degree sign must not show as mojibake on IronPython 2.7."""

    def test_coordinate_selector_uses_unicode_literals(self):
        tree = _parse(COORDINATE_SELECTOR)
        names = [
            alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "__future__"
            for alias in node.names
        ]
        self.assertIn("unicode_literals", names)

    def test_grid_bubbles_degree_constant_decodes_to_the_degree_sign(self):
        namespace = _load(GRID_BUBBLES, {"DEGREE"}, ast.Assign)
        self.assertEqual(namespace["DEGREE"], "\N{DEGREE SIGN}")

    def test_grid_bubbles_has_no_non_ascii_literal_outside_comments(self):
        found = _non_ascii_literals_outside_docstrings(_parse(GRID_BUBBLES))
        self.assertEqual(found, [])


@pytest.mark.regression
class KeynoteManagerTextTests(unittest.TestCase):
    """Issue 4184: Keynote Manager text must not show as mojibake on IronPython 2.7."""

    def test_constants_decode_to_the_expected_characters(self):
        names = {"EM_DASH", "MIDDLE_DOT", "LEFT_DOUBLE_QUOTE", "RIGHT_DOUBLE_QUOTE"}
        namespace = _load(KEYNOTES, names, ast.Assign)
        self.assertEqual(namespace["EM_DASH"], "\N{EM DASH}")
        self.assertEqual(namespace["MIDDLE_DOT"], "\N{MIDDLE DOT}")
        self.assertEqual(
            namespace["LEFT_DOUBLE_QUOTE"], "\N{LEFT DOUBLE QUOTATION MARK}"
        )
        self.assertEqual(
            namespace["RIGHT_DOUBLE_QUOTE"], "\N{RIGHT DOUBLE QUOTATION MARK}"
        )

    def test_only_allowlisted_literals_contain_non_ascii(self):
        found = _non_ascii_literals_outside_docstrings(_parse(KEYNOTES))
        unexpected = [
            literal
            for literal in found
            if not literal.startswith(KEYNOTES_ALLOWED_NON_ASCII)
        ]
        self.assertEqual(unexpected, [])

    def test_allowlist_has_no_stale_entries(self):
        found = _non_ascii_literals_outside_docstrings(_parse(KEYNOTES))
        stale = [
            prefix
            for prefix in KEYNOTES_ALLOWED_NON_ASCII
            if not any(literal.startswith(prefix) for literal in found)
        ]
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
