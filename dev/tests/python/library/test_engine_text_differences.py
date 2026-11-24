"""Check text that must render the same on IronPython 2.7 and CPython 3."""

import ast
from pathlib import Path
import unittest


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

NON_ASCII_FUNCTIONS = ("_update_status_bar", "_update_title")


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def _load_format_setting_value():
    tree = _parse(SETTINGS_WINDOW)
    tree.body = [
        node
        for node in tree.body
        if getattr(node, "name", "") == "_format_setting_value"
    ]
    namespace = {}
    exec(compile(tree, str(SETTINGS_WINDOW), "exec"), namespace)
    return namespace["_format_setting_value"]


def _non_ascii_literals(tree, function_names):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, str):
                    if not child.value.isascii():
                        found.append((node.name, child.value))
    return found


class FormatSettingValueTests(unittest.TestCase):
    def setUp(self):
        self.format = _load_format_setting_value()

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


class DegreeSignTests(unittest.TestCase):
    def test_coordinate_selector_uses_unicode_literals(self):
        tree = _parse(COORDINATE_SELECTOR)
        imports = [
            node
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "__future__"
        ]
        names = [alias.name for node in imports for alias in node.names]
        self.assertIn("unicode_literals", names)

    def test_grid_bubbles_status_does_not_format_a_byte_literal_with_degree(self):
        offenders = [
            node.value
            for node in ast.walk(_parse(GRID_BUBBLES))
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "\N{DEGREE SIGN}" in node.value
            and "tolerance" in node.value
        ]
        self.assertEqual(offenders, [])


class KeynoteManagerTextTests(unittest.TestCase):
    def test_constants_decode_to_the_expected_characters(self):
        tree = _parse(KEYNOTES)
        wanted = {"EM_DASH", "MIDDOT"}
        tree.body = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and getattr(node.targets[0], "id", "") in wanted
        ]
        namespace = {}
        exec(compile(tree, str(KEYNOTES), "exec"), namespace)
        self.assertEqual(namespace["EM_DASH"], "\N{EM DASH}")
        self.assertEqual(namespace["MIDDOT"], "\N{MIDDLE DOT}")

    def test_title_and_status_bar_have_no_non_ascii_literals(self):
        found = _non_ascii_literals(_parse(KEYNOTES), NON_ASCII_FUNCTIONS)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
