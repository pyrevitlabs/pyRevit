"""Check Copy Sheets to Open Documents helpers without Revit."""

import ast
import contextlib
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Sheets.pulldown"
    / "Copy Sheets to Open Documents.pushbutton/script.py"
)

FUNCTIONS = (
    "copy_viewport_types",
    "apply_viewport_type",
    "copy_view_contents",
    "copy_sheet_guides",
    "apply_detail_number",
)


class _PythonnetList(object):
    """``List[T]`` as pythonnet exposes it: no conversion from a Python list."""

    def __class_getitem__(cls, item_type):
        return cls

    def __init__(self, capacity=0):
        if not isinstance(capacity, int):
            raise TypeError(
                "No method matches given arguments for List`1..ctor: (<class 'list'>)"
            )
        self.items = []

    def Add(self, item):
        self.items.append(item)


def _to_clr_list(item_type, iterable):
    clr_list = _PythonnetList[item_type]()
    for item in iterable:
        clr_list.Add(item)
    return clr_list


class _ArgumentException(Exception):
    pass


class _PythonnetElement(object):
    """Element class whose ``Name`` descriptor has no IronPython ``GetValue``."""

    @property
    def Name(self):
        return self._name

    def __init__(self, element_id, name, type_id=None, valid_types=()):
        self.Id = element_id
        self._name = name
        self._type_id = type_id
        self._valid_types = list(valid_types)
        self.changed_to = None

    def GetTypeId(self):
        return self._type_id

    def GetValidTypes(self):
        return list(self._valid_types)

    def ChangeTypeId(self, type_id):
        self.changed_to = type_id


class _Document(object):
    def __init__(self, *elements):
        self._elements = {element.Id: element for element in elements}

    def GetElement(self, element_id):
        return self._elements.get(element_id)


class _Parameter(object):
    def __init__(self, value=None, set_error=None):
        self._value = value
        self._set_error = set_error
        self.IsReadOnly = False

    def AsString(self):
        return self._value

    def AsElementId(self):
        return self._value

    def Set(self, value):
        if self._set_error:
            raise self._set_error


class _ParamHost(object):
    Name = "A101"

    def __init__(self, parameter):
        self._parameter = parameter

    def get_Parameter(self, param_id):
        return self._parameter


def _module(name, **attrs):
    module = ModuleType(name)
    module.__dict__.update(attrs)
    return module


def _load_functions(copied, **globals_):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    tree.body = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        or getattr(node, "name", "") in FUNCTIONS
    ]
    query = SimpleNamespace(get_name=lambda element: element.Name)
    db = SimpleNamespace(
        CopyPasteOptions=lambda: SimpleNamespace(
            SetDuplicateTypeNamesHandler=lambda handler: None
        ),
        ElementTransformUtils=SimpleNamespace(
            CopyElements=lambda *args: copied.append(args)
        ),
        ElementId=int,
        BuiltInParameter=SimpleNamespace(
            VIEWPORT_DETAIL_NUMBER="detail", SHEET_GUIDE_GRID="guide"
        ),
    )
    revit = _module(
        "pyrevit.revit",
        query=query,
        create=SimpleNamespace(CopyUseDestination=object),
        Transaction=lambda *args, **kwargs: contextlib.nullcontext(),
    )
    modules = {
        "System": _module("System", ArgumentException=_ArgumentException),
        "pyrevit": _module(
            "pyrevit", revit=revit, DB=db, UI=None, forms=None, script=None
        ),
        "pyrevit.framework": _module(
            "pyrevit.framework", to_clr_list=_to_clr_list, List=_PythonnetList
        ),
        "pyrevit.revit": revit,
    }
    namespace = {
        "List": _PythonnetList,
        "logger": SimpleNamespace(debug=lambda msg: None, error=lambda msg: None),
    }
    namespace.update(globals_)
    with mock.patch.dict("sys.modules", modules):
        exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace


class ViewportTypeNameTests(unittest.TestCase):
    """Viewport type names must read on every engine."""

    def test_no_name_getvalue_on_db_elements(self):
        """Guard: ``Element.Name.GetValue`` is IronPython-only."""
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertFalse("Name.GetValue" in source)

    def test_matching_type_is_applied_without_copying(self):
        """An existing same-named type in the destination is reused and applied."""
        copied = []
        functions = _load_functions(copied)
        source_type = _PythonnetElement(10, "Title w Line")
        source_vport = _PythonnetElement(1, "vp", type_id=10)
        dest_other = _PythonnetElement(20, "No Title")
        dest_match = _PythonnetElement(21, "Title w Line")
        dest_vport = _PythonnetElement(2, "vp", type_id=20, valid_types=(20, 21))

        functions["apply_viewport_type"](
            _Document(source_type, source_vport),
            1,
            _Document(dest_other, dest_match, dest_vport),
            2,
        )

        self.assertEqual([], copied)
        self.assertEqual(21, dest_vport.changed_to)


class CopyElementsListTests(unittest.TestCase):
    """Ids reach ``CopyElements`` as a CLR list that pythonnet accepts."""

    def _assert_copied_ids(self, copied, ids):
        self.assertEqual(1, len(copied))
        self.assertIsInstance(copied[0][1], _PythonnetList)
        self.assertEqual(ids, copied[0][1].items)

    def test_missing_viewport_type_is_copied_as_clr_list(self):
        """A viewport type absent from the destination is copied over."""
        copied = []
        functions = _load_functions(copied)
        dest_other = _PythonnetElement(20, "No Title")
        dest_vport = _PythonnetElement(2, "vp", type_id=20, valid_types=(20,))

        functions["copy_viewport_types"](
            None,
            _PythonnetElement(10, "Title w Line"),
            "Title w Line",
            _Document(dest_other, dest_vport),
            dest_vport,
        )

        self._assert_copied_ids(copied, [10])

    def test_view_contents_are_copied_as_clr_list(self):
        """Drafting view contents are copied into the new view."""
        copied = []
        functions = _load_functions(copied, get_view_contents=lambda doc, view: [5, 6])
        view = SimpleNamespace(Name="Drafting 1", ViewType="DraftingView")

        functions["copy_view_contents"](None, view, None, view)

        self._assert_copied_ids(copied, [5, 6])

    def test_sheet_guide_is_copied_as_clr_list(self):
        """A sheet guide missing from the destination is copied over."""
        copied = []
        functions = _load_functions(copied, find_guide=lambda name, doc: None)
        guide = _PythonnetElement(30, "Guide A")

        functions["copy_sheet_guides"](
            _Document(guide), _ParamHost(_Parameter(30)), None, None
        )

        self._assert_copied_ids(copied, [30])


class DetailNumberTests(unittest.TestCase):
    """A rejected detail number is logged, not raised."""

    def test_argument_exception_is_caught(self):
        """The ``System.ArgumentException`` handler resolves its name."""
        errors = []
        functions = _load_functions(
            [],
            OPTION_SET=SimpleNamespace(op_preserve_detail_numbers=True),
            logger=SimpleNamespace(error=errors.append),
        )
        source = _ParamHost(_Parameter("A1"))
        dest = _ParamHost(_Parameter(set_error=_ArgumentException("in use")))

        with contextlib.redirect_stdout(None):
            functions["apply_detail_number"](source, dest)

        self.assertEqual(1, len(errors))


if __name__ == "__main__":
    unittest.main()
