"""Check how Replace Fonts reads type names and builds its dialogs without Revit."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/pyRevit.tab"
    / "Modify.panel/edit3.stack/Edit.pulldown"
    / "Replace_Fonts.pushbutton/script.py"
)

FUNCTIONS = (
    "rename_element_type_if_needed",
    "update_nested_generic_annotations",
    "process_family_document",
    "update_text_types",
)


class _Parameter(object):
    HasValue = True

    def __init__(self, value):
        self.value = value

    def AsString(self):
        return self.value

    def Set(self, value):
        self.value = value


class _PythonnetElement(object):
    """Element whose ``Name`` is a plain property without IronPython ``GetValue``."""

    @property
    def Name(self):
        return self._name

    @Name.setter
    def Name(self, value):
        self._name = value

    def __init__(self, name, font):
        self._name = name
        self._param = _Parameter(font)

    def get_Parameter(self, bip):
        return self._param


class _Transaction(object):
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Logger(object):
    def __init__(self):
        self.errors = []

    def debug(self, message):
        pass

    def error(self, message):
        self.errors.append(message)


class _FamilyMarker(object):
    pass


class _Collector(object):
    def __init__(self, doc):
        self.doc = doc

    def OfClass(self, cls):
        self.cls = cls
        return self

    def ToElements(self):
        return [] if self.cls is _FamilyMarker else self.doc.types


def _load():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if getattr(node, "name", "") in FUNCTIONS]
    logger = _Logger()
    namespace = {
        "re": __import__("re"),
        "logger": logger,
        "DB": SimpleNamespace(
            Element=_PythonnetElement,
            BuiltInParameter=SimpleNamespace(TEXT_FONT="TEXT_FONT"),
            FilteredElementCollector=_Collector,
            ElementType=object,
            Family=_FamilyMarker,
            BuiltInCategory=SimpleNamespace(OST_GenericAnnotation=1),
        ),
        "revit": SimpleNamespace(
            Transaction=_Transaction,
            TransactionGroup=_Transaction,
            query=SimpleNamespace(get_name=lambda element: element.Name),
        ),
        "get_elementid_value": lambda element_id: element_id,
        "FamilyLoaderOptionsHandler": object,
    }
    exec(compile(tree, str(SCRIPT), "exec"), namespace)
    return namespace, logger


class TypeNameTests(unittest.TestCase):
    """Type names must read on every engine, so no ``Name.GetValue``."""

    def test_update_text_types_returns_the_type_name(self):
        namespace, logger = _load()
        element = _PythonnetElement("Calibri 2mm", "Calibri")

        result = namespace["update_text_types"](None, [element], "Arial")

        self.assertEqual([("Arial 2mm", "Calibri", "Arial")], result)
        self.assertEqual([], logger.errors)

    def test_rename_replaces_the_old_font_in_the_type_name(self):
        namespace, _ = _load()
        element = _PythonnetElement("Calibri 2mm", "Calibri")

        namespace["rename_element_type_if_needed"](element, "Calibri", "Arial")

        self.assertEqual("Arial 2mm", element.Name)

    def test_process_family_document_returns_the_type_name(self):
        namespace, logger = _load()
        element = _PythonnetElement("Tahoma 3mm", "Tahoma")
        family_doc = SimpleNamespace(types=[element], Title="fam")

        result, found = namespace["process_family_document"](family_doc, "Arial")

        self.assertTrue(found)
        self.assertEqual([("Arial 3mm", "Tahoma", "Arial")], result)
        self.assertEqual([], logger.errors)


class ScriptSourceTests(unittest.TestCase):
    """FlexForm is IronPython-only, so the script must use pyRevit forms."""

    def test_script_has_no_rpw_import_or_flexform(self):
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        modules += [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]

        self.assertEqual([], [m for m in modules if m.split(".")[0] == "rpw"])
        self.assertNotIn("FlexForm", source)
        self.assertNotIn("Name.GetValue", source)
        self.assertNotIn("Name.SetValue", source)


if __name__ == "__main__":
    unittest.main()
