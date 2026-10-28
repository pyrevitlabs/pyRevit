"""Regression tests for Python engine selection across every implementation.

``ENGINE_SELECTION_CASES`` is the single table of precedence and first-line
cases. Each implementation is asserted against the same rows: the pyrevitlib
command generator (``runtime.create_ipyengine_configs`` read the way the C#
``ScriptRuntime`` reads it), ``GenericUICommand.is_cpython``, and the
standalone ``check_py3_compat`` mirror.
"""

import ast
import importlib.util
import json
from pathlib import Path
import runpy
import tempfile
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = runpy.run_path(
    str(REPO_ROOT / "pyrevitlib/pyrevit/extensions/__init__.py")
)
exts = types.SimpleNamespace(**EXTENSIONS)
get_declared_python_engine = exts.get_declared_python_engine
get_declared_engine_type = exts.get_declared_engine_type


def _load_function(relative_path, name, namespace, class_name=None):
    tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    body = tree.body
    if class_name is not None:
        body = next(
            n.body for n in body if isinstance(n, ast.ClassDef) and n.name == class_name
        )
    node = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), relative_path, "exec"),
        namespace,
    )
    return namespace[name]


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_py3_compat", REPO_ROOT / "dev/scripts/check_py3_compat.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


create_ipyengine_configs = _load_function(
    "pyrevitlib/pyrevit/runtime/__init__.py",
    "create_ipyengine_configs",
    {"json": json, "exts": exts},
)
is_cpython = _load_function(
    "pyrevitlib/pyrevit/extensions/genericcomps.py",
    "is_cpython",
    {"PY3": True, "exts": exts},
    class_name="GenericUICommand",
)
checker = _load_checker()


def _script_runtime_selects_cpython(engine_configs, first_line):
    """Read engine configs as C# ``ScriptRuntime.EngineType`` does."""
    configs = json.loads(engine_configs)
    engine_type = configs.get("type")
    if engine_type:
        if engine_type.lower() == "cpython":
            return True
        if engine_type.lower() == "ironpython" and configs.get("type_explicit"):
            return False
    return "python3" in first_line or "cpython" in first_line


ENGINE_SELECTION_CASES = (
    ("no declaration, plain first line", None, None, "import clr", False),
    ("no declaration, python3 shebang", None, None, "#! python3", True),
    ("no declaration, cpython shebang", None, None, "#! cpython", True),
    ("marker anywhere on the first line", None, None, "# needs python3 here", True),
    ("markers are case-sensitive", None, None, "#! Python3", False),
    ("CPython marker is case-sensitive", None, None, "#! CPython", False),
    ("extension cpython", None, "cpython", "import clr", True),
    ("extension cpython is normalized", None, " CPython ", "import clr", True),
    ("extension mapping form", None, {"type": "CPython"}, "import clr", True),
    ("extension ironpython keeps shebang", None, "ironpython", "#! python3", True),
    ("unsupported extension value", None, "python3", "import clr", False),
    ("mapping without type", None, {"clean": True}, "import clr", False),
    ("bundle cpython", "cpython", None, "import clr", True),
    ("bundle CPython over extension", "CPython", "ironpython", "import clr", True),
    ("bundle ironpython over all", "IronPython", "cpython", "#! python3", False),
    ("blank bundle type is no override", "  ", "cpython", "import clr", True),
    ("unknown bundle type drops extension", "python3", "cpython", "import clr", False),
    ("unknown bundle type uses shebang", "python3", "cpython", "#! python3", True),
)

FIRST_LINE_ONLY_CASES = tuple(
    case for case in ENGINE_SELECTION_CASES if case[1] is None and case[2] is None
)


class EngineSelectionTableTests(unittest.TestCase):
    """Every Python implementation agrees on the shared selection table."""

    def test_command_generator_configs(self):
        """Engine configs from pyrevitlib select the engine the table expects."""
        for name, bundle, extension, first_line, expected in ENGINE_SELECTION_CASES:
            with self.subTest(name):
                configs = create_ipyengine_configs(
                    engine_type=get_declared_python_engine({"engine": extension}),
                    bundle_engine_type=bundle,
                )
                self.assertEqual(
                    expected, _script_runtime_selects_cpython(configs, first_line)
                )

    def test_checker_mirror(self):
        """The standalone checker reads bundle.yaml and extension.json the same way."""
        for name, bundle, extension, first_line, expected in ENGINE_SELECTION_CASES:
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                extension_dir = Path(directory) / "Ext.extension"
                bundle_dir = extension_dir / "Tool.pushbutton"
                bundle_dir.mkdir(parents=True)
                if extension is not None:
                    (extension_dir / "extension.json").write_text(
                        json.dumps({"engine": extension})
                    )
                if bundle is not None:
                    (bundle_dir / "bundle.yaml").write_text(
                        "engine:\n  type: {}\n".format(json.dumps(bundle))
                    )
                self.assertEqual(
                    expected,
                    checker._may_run_under_cpython(
                        bundle_dir / "script.py", first_line + "\nx = 1\n"
                    ),
                )

    def test_first_line_rule(self):
        """The shared first-line rule and the checker mirror agree."""
        for name, _, _, first_line, expected in FIRST_LINE_ONLY_CASES:
            with self.subTest(name):
                self.assertEqual(expected, exts.first_line_selects_cpython(first_line))
                self.assertEqual(
                    expected, checker._first_line_selects_cpython(first_line)
                )
                self.assertEqual(
                    exts.CPYTHON_FIRST_LINE_MARKERS, checker.CPYTHON_FIRST_LINE_MARKERS
                )

    def test_generic_ui_command_is_cpython(self):
        """GenericUICommand.is_cpython applies the first-line rule to the script."""
        for name, _, _, first_line, expected in FIRST_LINE_ONLY_CASES:
            with self.subTest(name), tempfile.TemporaryDirectory() as directory:
                script = Path(directory) / "script.py"
                script.write_text(first_line + "\nx = 1\n", encoding="utf-8")
                command = types.SimpleNamespace(script_file=str(script))
                self.assertEqual(expected, is_cpython(command))


class ExtensionEngineTests(unittest.TestCase):
    """Extension metadata declarations preserve explicit engine choice."""

    def test_cpython_declaration_is_normalized(self):
        """CPython declarations are case-insensitive metadata values."""
        self.assertEqual("cpython", get_declared_python_engine({"engine": " CPython "}))

    def test_ironpython_declaration_is_normalized(self):
        """IronPython declarations are case-insensitive metadata values."""
        self.assertEqual(
            "ironpython", get_declared_python_engine({"engine": "IRONPYTHON"})
        )

    def test_missing_or_unknown_declarations_do_not_override_shebangs(self):
        """Only supported declarations supply an explicit runtime override."""
        self.assertIsNone(get_declared_python_engine({}))
        self.assertIsNone(get_declared_python_engine({"engine": "python3"}))

    def test_bundle_style_mapping_declares_its_type(self):
        """The mapping form the C# loader reads declares the same engine."""
        self.assertEqual(
            "cpython",
            get_declared_python_engine({"engine": {"type": "CPython", "clean": True}}),
        )

    def test_mapping_without_type_declares_nothing(self):
        """Engine behavior settings alone are not an unsupported declaration."""
        self.assertIsNone(get_declared_engine_type({"engine": {"clean": True}}))
        self.assertIsNone(get_declared_python_engine({"engine": {"clean": True}}))

    def test_bundle_engine_type_reads_only_the_mapping_form(self):
        """A scalar bundle ``engine:`` is ignored, as the C# BundleParser does."""
        self.assertEqual(
            "CPython", exts.get_bundle_engine_type({"engine": {"type": "CPython"}})
        )
        self.assertIsNone(exts.get_bundle_engine_type({"engine": "cpython"}))
        self.assertIsNone(exts.get_bundle_engine_type(None))


class EngineConfigPrecedenceTests(unittest.TestCase):
    """The Python command generator matches C# BuildEngineConfigs precedence."""

    def test_extension_cpython_declaration_sets_type(self):
        """A cpython extension makes CPython the default without marking it explicit."""
        configs = json.loads(create_ipyengine_configs(engine_type="cpython"))
        self.assertEqual("CPython", configs["type"])
        self.assertNotIn("type_explicit", configs)

    def test_bundle_engine_type_wins_over_extension(self):
        """A bundle's own engine.type overrides the extension declaration."""
        configs = json.loads(
            create_ipyengine_configs(
                engine_type="cpython", bundle_engine_type="IronPython"
            )
        )
        self.assertEqual("IronPython", configs["type"])
        self.assertTrue(configs["type_explicit"])

    def test_no_declarations_leave_type_to_the_shebang(self):
        """Without any declaration the runtime picks the engine per script."""
        self.assertNotIn("type", json.loads(create_ipyengine_configs()))


if __name__ == "__main__":
    unittest.main()
