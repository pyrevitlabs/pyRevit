"""Regression tests for #4184: text that differs between engines.

IronPython 2.7 shows floats with 12 significant digits and widens the UTF-8
bytes of non-ASCII byte-string literals one by one (mojibake); CPython 3 and
IronPython 3.4 do neither. These checks inspect source without loading Revit.
"""

import ast
import builtins
from pathlib import Path
from types import SimpleNamespace
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


def _load_method(path, class_name, method_name, namespace):
    tree = _parse(path)
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method = next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    )
    module = ast.Module(body=[method], type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[method_name]


def _free_names(function):
    loaded = {
        node.id
        for node in ast.walk(function)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    bound = {
        node.id
        for node in ast.walk(function)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    bound |= {node.arg for node in ast.walk(function) if isinstance(node, ast.arg)}
    bound |= {
        node.name
        for node in ast.walk(function)
        if isinstance(node, (ast.ExceptHandler, ast.FunctionDef)) and node.name
    }
    return loaded - bound - set(dir(builtins))


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
class SettingValueFromTextTests(unittest.TestCase):
    """Issue 4184: an unedited rounded float must not replace the stored value."""

    def setUp(self):
        names = {"_format_setting_value", "_setting_value_from_text"}
        self.namespace = _load(SETTINGS_WINDOW, names, ast.FunctionDef)
        self.from_text = self.namespace["_setting_value_from_text"]
        self.format = self.namespace["_format_setting_value"]

    def test_unedited_float_keeps_its_exact_value(self):
        original = 1.9685039370078
        self.assertEqual(self.from_text(self.format(original), original), original)

    def test_edited_text_is_returned_as_typed(self):
        self.assertEqual(self.from_text("2.5", 1.9685039370078), "2.5")

    def test_non_float_originals_return_the_text(self):
        self.assertEqual(self.from_text("5", 5), "5")
        self.assertEqual(self.from_text("a", None), "a")

    def _save(self, setting_type, original, text, **schema):
        namespace = _load(
            SETTINGS_WINDOW,
            {
                "_format_setting_value",
                "_setting_value_from_text",
                "_DISPLAY_ONLY_TYPES",
            },
            (ast.FunctionDef, ast.Assign),
        )
        alerts = []
        namespace["forms"] = SimpleNamespace(
            alert=lambda message, **kwargs: alerts.append(message)
        )
        namespace["script"] = SimpleNamespace(save_config=lambda: None)
        methods = {
            name: _load_method(SETTINGS_WINDOW, "SettingsWindow", name, namespace)
            for name in ("save_clicked", "_validate_setting", "_validate_numeric")
        }
        written = {}
        setting = dict(schema, name="field", type=setting_type)
        window = SimpleNamespace(
            settings_schema=[setting],
            controls={"field": SimpleNamespace(Text=text)},
            _original_values={"field": original},
            config=SimpleNamespace(set_option=written.__setitem__),
            configparser=None,
            result=None,
            Close=lambda: None,
        )
        window._validate_setting = lambda s, v: methods["_validate_setting"](
            window, s, v
        )
        window._validate_numeric = lambda *a: methods["_validate_numeric"](window, *a)
        methods["save_clicked"](window, None, None)
        return written, alerts

    def test_unedited_float_setting_is_saved_exactly(self):
        original = 1.9685039370078
        written, alerts = self._save("float", original, "1.96850393701")
        self.assertEqual(written, {"field": original})
        self.assertEqual(alerts, [])

    def test_edited_float_setting_is_saved_as_typed(self):
        written, _ = self._save("float", 1.9685039370078, "2.5")
        self.assertEqual(written, {"field": 2.5})

    def test_int_setting_holding_a_decimal_is_still_rejected(self):
        written, alerts = self._save("int", 10.5, "10.5")
        self.assertEqual(written, {})
        self.assertEqual(len(alerts), 1)

    def test_string_setting_with_a_float_default_is_saved_as_text(self):
        written, _ = self._save("string", 1.5, "1.5")
        self.assertEqual(written, {"field": "1.5"})


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

    def test_status_line_shows_the_degree_sign(self):
        namespace = _load(GRID_BUBBLES, {"DEGREE"}, ast.Assign)
        update = _load_method(
            GRID_BUBBLES, "ToggleGridWindow", "update_status_display", namespace
        )
        grids = SimpleNamespace(
            selection=[],
            grids=lambda: [object()],
            get_active_grids=lambda: [object()],
        )
        window = SimpleNamespace(
            grids=grids,
            coordinate_system="true_north",
            angle_tolerance=1,
            status_grids=SimpleNamespace(Text=""),
            status_grids_active=SimpleNamespace(Text=""),
            status_coordinate_system=SimpleNamespace(Text=""),
            status_active_controls=SimpleNamespace(Text=""),
            top_bottom_collapsed=True,
            right_left_collapsed=True,
            show_element=lambda element: None,
            hide_element=lambda element: None,
        )
        update(window)
        self.assertIn("1° tolerance", window.status_coordinate_system.Text)

    def test_grid_bubbles_has_no_non_ascii_literal_outside_comments(self):
        found = _non_ascii_literals_outside_docstrings(_parse(GRID_BUBBLES))
        self.assertEqual(found, [])


@pytest.mark.regression
class KeynoteManagerTextTests(unittest.TestCase):
    """Issue 4184: Keynote Manager text must not show as mojibake on IronPython 2.7."""

    def test_lost_engine_warning_uses_no_script_globals(self):
        guard = next(
            node
            for node in _parse(KEYNOTES).body
            if isinstance(node, ast.FunctionDef) and node.name == "ui_guard"
        )
        guard.args.defaults = []
        self.assertEqual(_free_names(guard), set())

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
