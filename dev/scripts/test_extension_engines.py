"""Regression tests for extension-level Python engine declarations."""

from pathlib import Path
import runpy
import unittest


EXTENSIONS = runpy.run_path(
    str(
        Path(__file__).resolve().parents[2]
        / "pyrevitlib/pyrevit/extensions/__init__.py"
    )
)
get_declared_python_engine = EXTENSIONS["get_declared_python_engine"]
get_declared_engine_type = EXTENSIONS["get_declared_engine_type"]


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


if __name__ == "__main__":
    unittest.main()
