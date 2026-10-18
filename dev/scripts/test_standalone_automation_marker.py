"""Tests for the engine-neutral Python automation markers."""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"


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


class AutomationInputTests(unittest.TestCase):
    """Declared inputs are parsed strictly and checked before any call."""

    SPECS = (
        "name: string",
        "count: integer?",
        "ratio: number?",
        "flag: boolean?",
        "element: element?",
        "value: scalar?",
    )

    def assertRejected(self, inputs):
        with self.assertRaises(automation.InputError):
            automation.validate_inputs(self.SPECS, inputs)

    def test_inputs_are_kept_in_the_metadata_only_when_declared(self):
        @automation.operation(
            "pyrevit.elements.name",
            PlainEnglish="Read an element name.",
            inputs=("element: element", "title_on_sheet: boolean?"),
        )
        def get_name(element, title_on_sheet=False):
            return element

        @automation.operation("pyrevit.revisions.list", PlainEnglish="List.", inputs=())
        def get_revisions(doc=None):
            return doc

        self.assertEqual(
            ("element: element", "title_on_sheet: boolean?"),
            get_name.__pyrevit_automation__["inputs"],
        )
        self.assertEqual((), get_revisions.__pyrevit_automation__["inputs"])

    def test_parse_reads_name_type_and_optional_marker(self):
        self.assertEqual(
            [
                {"name": "element", "type": "element", "required": True},
                {"name": "title_on_sheet", "type": "boolean", "required": False},
            ],
            automation.parse_inputs(
                ("element: element", " title_on_sheet :boolean ? ")
            ),
        )

    def test_parse_rejects_malformed_declarations(self):
        for specs in (
            ["name: string"],
            ("name string",),
            ("name: text",),
            ("1name: string",),
            ("name: string", "name: integer?"),
            ("",),
            ("name: string!",),
        ):
            with self.assertRaises(ValueError, msg=repr(specs)):
                automation.parse_inputs(specs)
        with self.assertRaises(ValueError):
            automation.operation("a.b", PlainEnglish="Bad.", inputs=("x: text",))

    def test_valid_inputs_pass_unchanged(self):
        inputs = {
            "name": "Level 1",
            "count": 3,
            "ratio": 1.5,
            "flag": False,
            "element": 316542,
            "value": "Concrete",
        }
        self.assertIs(inputs, automation.validate_inputs(self.SPECS, inputs))
        automation.validate_inputs(self.SPECS, {"name": "x" * 256})
        for scalar in (2, 2.5, True, "x"):
            automation.validate_inputs(self.SPECS, {"name": "a", "value": scalar})

    def test_missing_unknown_and_null_inputs_are_rejected(self):
        self.assertRejected({})
        self.assertRejected({"name": "a", "extra": 1})
        self.assertRejected({"name": None})
        self.assertRejected({"name": "a", "count": None})
        with self.assertRaises(automation.InputError):
            automation.validate_inputs(self.SPECS, ["name"])
        with self.assertRaises(automation.InputError):
            automation.validate_inputs((), {"anything": 1})

    def test_wrong_types_are_rejected(self):
        for bad in (
            {"name": 1},
            {"name": ""},
            {"name": "   "},
            {"name": "x" * 257},
            {"name": "a", "count": 1.0},
            {"name": "a", "count": True},
            {"name": "a", "count": "3"},
            {"name": "a", "count": 2**63},
            {"name": "a", "ratio": float("inf")},
            {"name": "a", "ratio": float("nan")},
            {"name": "a", "ratio": "1.5"},
            {"name": "a", "ratio": False},
            {"name": "a", "flag": 1},
            {"name": "a", "element": "316542"},
            {"name": "a", "element": True},
            {"name": "a", "element": 3.0},
            {"name": "a", "value": []},
            {"name": "a", "value": {}},
            {"name": "a", "value": ""},
        ):
            self.assertRejected(bad)


def _load_operations_module():
    """Load pyrevit/agent/_operations.py without importing pyrevit itself."""
    import importlib.util

    path = op.join(PYREVITLIB_DIR, "pyrevit", "agent", "_operations.py")
    spec = importlib.util.spec_from_file_location("_operations_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeDocument(object):
    def __init__(self, elements):
        self.elements = elements

    def GetElement(self, element_id):
        return self.elements.get(element_id)


class AutomationInvokeTests(unittest.TestCase):
    """The in-Revit half re-checks the live marker before calling."""

    @classmethod
    def setUpClass(cls):
        cls.operations = _load_operations_module()

    def setUp(self):
        import types
        from unittest import mock

        fixtures = types.ModuleType("pyrevit.fixtures")

        @automation.operation(
            "test.elements.name",
            PlainEnglish="Name an element.",
            inputs=("element: element", "upper: boolean?"),
        )
        def element_name(element, upper=False):
            return element.upper() if upper else element

        @automation.operation(
            "test.items.list", PlainEnglish="List items.", inputs=("count: integer",)
        )
        def list_items(count, doc=None):
            return [doc] * count

        @automation.operation(
            "test.units.parse",
            PlainEnglish="Parse.",
            mode="pure",
            context="none",
            inputs=("value: scalar",),
        )
        def parse(value):
            return {"parsed": value}

        @automation.operation(
            "test.walls.delete",
            PlainEnglish="Delete.",
            mode="modify",
            transaction="caller",
            inputs=("element: element",),
        )
        def delete(element):
            raise AssertionError("must never run")

        @automation.operation("test.views.list", PlainEnglish="List views.")
        def unlisted():
            raise AssertionError("must never run")

        @automation.operation(
            "test.items.stream",
            PlainEnglish="Stream items.",
            inputs=("count: integer",),
        )
        def stream_items(count):
            return (index for index in range(count))

        for function in (
            element_name,
            list_items,
            stream_items,
            parse,
            delete,
            unlisted,
        ):
            setattr(fixtures, function.__name__, function)
        fixtures.unmarked = lambda: None

        compat = types.ModuleType("pyrevit.compat")
        compat.get_elementid_from_value_func = lambda: lambda value: value
        package = types.ModuleType("pyrevit")
        package.__path__ = []
        patcher = mock.patch.dict(
            sys.modules,
            {
                "pyrevit": package,
                "pyrevit.fixtures": fixtures,
                "pyrevit.compat": compat,
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.doc = _FakeDocument({42: "wall", 7: "door"})

    def invoke(self, function, automation_id, inputs, doc=None, module=None):
        operation = {
            "id": automation_id,
            "module": module or "pyrevit.fixtures",
            "function": function,
        }
        return self.operations.invoke(operation, inputs, doc)

    def test_element_inputs_are_resolved_in_the_active_document(self):
        self.assertEqual(
            {"value": "WALL"},
            self.invoke(
                "element_name",
                "test.elements.name",
                {"element": 42, "upper": True},
                self.doc,
            ),
        )
        with self.assertRaises(automation.InputError):
            self.invoke("element_name", "test.elements.name", {"element": 99}, self.doc)

    def test_the_document_is_passed_only_to_functions_that_take_it(self):
        result = self.invoke("list_items", "TEST.items.LIST", {"count": 2}, self.doc)
        self.assertEqual([self.doc, self.doc], result["value"])
        self.assertEqual(
            {"value": "wall"},
            self.invoke(
                "element_name", "test.elements.name", {"element": 42}, self.doc
            ),
        )

    def test_list_results_are_bounded(self):
        result = self.invoke("list_items", "test.items.list", {"count": 250}, self.doc)
        self.assertEqual(self.operations.MAX_ITEMS, len(result["value"]))
        self.assertEqual(250, result["total"])
        self.assertTrue(result["truncated"])
        small = self.invoke("list_items", "test.items.list", {"count": 1}, self.doc)
        self.assertEqual({"value": [self.doc], "total": 1, "truncated": False}, small)

    def test_iterator_results_are_bounded_too(self):
        result = self.invoke(
            "stream_items", "test.items.stream", {"count": 250}, self.doc
        )
        self.assertEqual(list(range(self.operations.MAX_ITEMS)), result["value"])
        self.assertEqual(250, result["total"])
        self.assertTrue(result["truncated"])

    def test_a_pure_operation_runs_without_a_document(self):
        self.assertEqual(
            {"value": {"parsed": "8:12"}},
            self.invoke("parse", "test.units.parse", {"value": "8:12"}),
        )

    def test_a_document_operation_needs_a_document(self):
        with self.assertRaises(self.operations.OperationError):
            self.invoke("list_items", "test.items.list", {"count": 1})
        with self.assertRaises(self.operations.OperationError):
            self.invoke("element_name", "test.elements.name", {"element": 42})

    def test_inputs_are_validated_before_the_call(self):
        with self.assertRaises(automation.InputError):
            self.invoke("list_items", "test.items.list", {"count": "2"}, self.doc)
        with self.assertRaises(automation.InputError):
            self.invoke(
                "list_items", "test.items.list", {"count": 2, "doc": "x"}, self.doc
            )

    def test_only_marked_invocable_operations_run(self):
        for function, automation_id, module in (
            ("delete", "test.walls.delete", None),
            ("unlisted", "test.views.list", None),
            ("unmarked", "test.unmarked", None),
            ("missing", "test.missing", None),
            ("parse", "test.other.id", None),
            ("system", "os.system", "os"),
            ("system", "os.system", "pyrevitx.os"),
        ):
            with self.assertRaises(self.operations.OperationError, msg=function):
                self.invoke(
                    function, automation_id, {"element": 42}, self.doc, module=module
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

    def test_declared_inputs_match_the_function_they_mark(self):
        """run_automation calls ``function(**inputs)``, so the two must agree.

        Inputs belong only on module-level query or pure operations that open
        no transaction (the only ones run_automation calls), every input names
        a parameter, and every parameter without a default other than ``doc``
        is a required input.
        """
        problems = []
        declared = 0
        for path, source in _marker_files():
            relative = op.relpath(path, PYREVITLIB_DIR)
            tree = ast.parse(source, path)
            module_level = set(
                node for node in tree.body if isinstance(node, ast.FunctionDef)
            )
            for node, marker in _markers(tree):
                keywords = dict((k.arg, k.value) for k in marker.keywords)
                if "inputs" not in keywords:
                    continue
                declared += 1
                where = "{}:{} {}".format(relative, marker.lineno, node.name)
                try:
                    specs = ast.literal_eval(keywords["inputs"])
                    parsed = automation.parse_inputs(specs)
                except ValueError as error:
                    problems.append("{}: {}".format(where, error))
                    continue
                if not all(
                    isinstance(element, ast.Constant) and isinstance(element.value, str)
                    for element in keywords["inputs"].elts
                ):
                    problems.append(where + ": inputs must be string literals")
                mode = (
                    ast.literal_eval(keywords["mode"])
                    if "mode" in keywords
                    else "query"
                )
                transaction = (
                    ast.literal_eval(keywords["transaction"])
                    if "transaction" in keywords
                    else "none"
                )
                if (
                    marker.func.attr != "operation"
                    or node not in module_level
                    or mode not in ("query", "pure")
                    or transaction != "none"
                ):
                    problems.append(
                        where + ": inputs are only for module-level query or pure "
                        "operations without a transaction"
                    )
                    continue
                arguments = node.args.args
                defaults = len(node.args.defaults)
                names = [argument.arg for argument in arguments]
                required = set(names[: len(names) - defaults]) - {"doc"}
                given = set(spec["name"] for spec in parsed)
                for spec in parsed:
                    if spec["name"] not in names or spec["name"] == "doc":
                        problems.append(
                            "{}: input {!r} is not a parameter".format(
                                where, spec["name"]
                            )
                        )
                    elif spec["required"] != (spec["name"] in required):
                        problems.append(
                            "{}: input {!r} must be {} like its parameter".format(
                                where,
                                spec["name"],
                                "required" if spec["name"] in required else "optional",
                            )
                        )
                for name in sorted(required - given):
                    problems.append(
                        "{}: parameter {!r} has no default and no input".format(
                            where, name
                        )
                    )
                if node.args.vararg or node.args.kwarg or node.args.kwonlyargs:
                    problems.append(
                        where + ": *args, **kwargs and keyword-only "
                        "parameters cannot be inputs"
                    )
        self.assertTrue(declared, "no automation marker declares inputs")
        self.assertEqual([], problems)


if __name__ == "__main__":
    unittest.main()
