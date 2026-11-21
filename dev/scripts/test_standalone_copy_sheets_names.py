"""Check how Copy Sheets to Open Documents matches viewport type names without Revit."""

import ast
import contextlib
from pathlib import Path
from types import SimpleNamespace
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Drawing Set.panel/Sheets.pulldown"
    / "Copy Sheets to Open Documents.pushbutton/script.py"
)

FUNCTIONS = ("copy_viewport_types", "apply_viewport_type")


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
        return self._elements[element_id]


def _load_functions(copied):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if getattr(node, "name", "") in FUNCTIONS]
    query = SimpleNamespace(get_name=lambda element: element.Name)
    db = SimpleNamespace(
        CopyPasteOptions=lambda: SimpleNamespace(
            SetDuplicateTypeNamesHandler=lambda handler: None
        ),
        ElementTransformUtils=SimpleNamespace(
            CopyElements=lambda *args: copied.append(args)
        ),
        ElementId=int,
    )
    namespace = {
        "DB": db,
        "to_clr_list": lambda item_type, items: list(items),
        "CopyUseDestination": object,
        "query": query,
        "revit": SimpleNamespace(
            query=query,
            Transaction=lambda *args, **kwargs: contextlib.nullcontext(),
        ),
    }
    exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace


class ViewportTypeNameTests(unittest.TestCase):
    """Viewport type names must read on every engine."""

    def test_no_name_getvalue_on_db_elements(self):
        """``Element.Name.GetValue`` is IronPython-only; pythonnet has no such call."""
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

    def test_missing_type_is_copied_to_destination(self):
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

        self.assertEqual(1, len(copied))


if __name__ == "__main__":
    unittest.main()
