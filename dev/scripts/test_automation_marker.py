"""Tests for the engine-neutral Python automation markers."""

import os.path as op
import sys
import unittest


ROOT_DIR = op.dirname(op.dirname(op.dirname(op.abspath(__file__))))
PYREVITLIB_DIR = op.join(ROOT_DIR, "pyrevitlib")
if PYREVITLIB_DIR not in sys.path:
    sys.path.insert(0, PYREVITLIB_DIR)

import pyrevit_automation as automation


class AutomationMarkerTests(unittest.TestCase):
    """Metadata markers preserve the original Python objects."""

    def test_operation_preserves_function_and_metadata(self):
        @automation.operation(
            "pyrevit.units.parse-length",
            PlainEnglish="Convert a written length to Revit internal feet.",
            mode="pure",
        )
        def parse_length(value):
            return value

        self.assertEqual(3, parse_length(3))
        self.assertEqual(
            {
                "id": "pyrevit.units.parse-length",
                "PlainEnglish": "Convert a written length to Revit internal feet.",
                "mode": "pure",
                "effects": (),
                "context": "document",
                "transaction": "none",
            },
            parse_length.__pyrevit_automation__,
        )

    def test_type_marks_class_without_marking_members(self):
        @automation.type(
            "rpw.types.element",
            PlainEnglish="Wrap a Revit element for access from Python.",
        )
        class Element(object):
            def name(self):
                return "Element"

        self.assertEqual("type", Element.__pyrevit_automation__["kind"])
        self.assertFalse(hasattr(Element.name, "__pyrevit_automation__"))

    def test_rejects_invalid_metadata(self):
        with self.assertRaises(ValueError):
            automation.operation("", PlainEnglish="Read an element.")
        with self.assertRaises(ValueError):
            automation.operation("pyrevit.elements.read", PlainEnglish="")
        with self.assertRaises(ValueError):
            automation.operation(
                "pyrevit.elements.read", PlainEnglish="Read an element.", effects=[]
            )


if __name__ == "__main__":
    unittest.main()
