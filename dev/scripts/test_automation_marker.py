"""Tests for the engine-neutral Python automation markers."""

import ast
import io
import os
import os.path as op
import re
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


STRING_LITERAL = re.compile(r"""^(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')$""")
MARKER_DECORATORS = ("operation", "type")


def _marker_files():
    for directory, _, files in os.walk(PYREVITLIB_DIR):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = op.join(directory, name)
            with io.open(path, encoding="utf-8") as source_file:
                source = source_file.read()
            if "@automation." in source:
                yield path, source


def _markers(tree):
    for node in ast.walk(tree):
        for decorator in getattr(node, "decorator_list", []):
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "automation"
                and decorator.func.attr in MARKER_DECORATORS
            ):
                yield node, decorator


class AutomationSourceMarkerTests(unittest.TestCase):
    """Every marker in pyrevitlib is one the CLI library index can read.

    The index skips a marker it cannot read and an id used twice, so this test
    is what keeps those mistakes from silently dropping an API from agents.
    """

    def test_markers_are_readable_and_ids_unique(self):
        problems = []
        owners = {}
        for path, source in _marker_files():
            relative = op.relpath(path, PYREVITLIB_DIR)
            try:
                tree = ast.parse(source, path)
            except SyntaxError as error:
                problems.append("{}: cannot parse ({})".format(relative, error))
                continue
            for node, marker in _markers(tree):
                where = "{}:{} {}".format(relative, marker.lineno, node.name)
                literal_id = (
                    ast.get_source_segment(source, marker.args[0])
                    if marker.args
                    else None
                )
                plain_english = next(
                    (
                        ast.get_source_segment(source, keyword.value)
                        for keyword in marker.keywords
                        if keyword.arg == "PlainEnglish"
                    ),
                    None,
                )
                if not literal_id or not STRING_LITERAL.match(literal_id):
                    problems.append(where + ": id must be one string literal")
                    continue
                if not plain_english or not STRING_LITERAL.match(plain_english):
                    problems.append(where + ": PlainEnglish must be one string literal")
                marker_id = ast.literal_eval(literal_id).lower()
                if marker_id in owners:
                    problems.append(
                        "{}: id {!r} is also used by {}".format(
                            where, marker_id, owners[marker_id]
                        )
                    )
                else:
                    owners[marker_id] = where
        self.assertTrue(owners, "no automation markers found in pyrevitlib")
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
