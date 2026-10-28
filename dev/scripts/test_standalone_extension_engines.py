"""Regression tests for extension-level Python engine declarations."""

import ast
import json
from pathlib import Path
import runpy
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = runpy.run_path(
    str(REPO_ROOT / "pyrevitlib/pyrevit/extensions/__init__.py")
)
get_declared_python_engine = EXTENSIONS["get_declared_python_engine"]
get_declared_engine_type = EXTENSIONS["get_declared_engine_type"]


def _load_runtime_function(name):
    source = (REPO_ROOT / "pyrevitlib/pyrevit/runtime/__init__.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    node = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name
    )
    namespace = {"json": json, "exts": types.SimpleNamespace(**EXTENSIONS)}
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), "runtime", "exec"), namespace
    )
    return namespace[name]


create_ipyengine_configs = _load_runtime_function("create_ipyengine_configs")


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

    def test_blank_bundle_engine_type_is_not_an_override(self):
        """Whitespace bundle types fall back to the extension declaration."""
        configs = json.loads(
            create_ipyengine_configs(engine_type="cpython", bundle_engine_type="  ")
        )
        self.assertEqual("CPython", configs["type"])
        self.assertNotIn("type_explicit", configs)

    def test_no_declarations_leave_type_to_the_shebang(self):
        """Without any declaration the runtime picks the engine per script."""
        self.assertNotIn("type", json.loads(create_ipyengine_configs()))


if __name__ == "__main__":
    unittest.main()
