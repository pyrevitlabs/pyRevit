"""Regression checks for #4180: Replace Fonts on CPython, without Revit.

Covers engine-neutral type names and the pyRevit forms dialog wiring.
The stubbed ``revit.query.get_name`` does not exercise the real helper on
pythonnet.
"""

import ast
import sys
import types
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import pytest


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


@pytest.mark.regression
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


@pytest.mark.regression
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


class _Forms(object):
    def __init__(self, font, choice, switches):
        self.font = font
        self.choice = choice
        self.switches = switches
        self.switch_arguments = None
        self.message = None

    @property
    def SelectFromList(self):
        return SimpleNamespace(show=lambda *args, **kwargs: self.font)

    @property
    def CommandSwitchWindow(self):
        def show(context, **kwargs):
            self.switch_arguments = kwargs["switches"]
            self.message = kwargs["message"]
            return self.choice, self.switches

        return SimpleNamespace(show=show)


class _Output(object):
    def print_md(self, text):
        pass


def _run_project_main(forms, calls):
    class _ProjectCollector(object):
        def __init__(self, document):
            pass

        def OfClass(self, cls):
            calls.append(cls)
            return self

        def ToElements(self):
            return []

    class _Bar(object):
        cancelled = False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def module(name, **attributes):
        stub = types.ModuleType(name)
        stub.__dict__.update(attributes)
        return stub

    db = SimpleNamespace(
        Family="Family",
        TextNoteType="TextNoteType",
        DimensionType="DimensionType",
        FilteredElementCollector=_ProjectCollector,
        Element=_PythonnetElement,
        ElementType=object,
        BuiltInParameter=SimpleNamespace(TEXT_FONT="TEXT_FONT"),
        BuiltInCategory=SimpleNamespace(OST_GenericAnnotation=1),
    )
    host_app = SimpleNamespace(
        doc=SimpleNamespace(IsFamilyDocument=False),
        uidoc=SimpleNamespace(RefreshActiveView=lambda: None),
    )
    revit = SimpleNamespace(
        Transaction=_Transaction,
        TransactionGroup=_Transaction,
        query=SimpleNamespace(get_name=lambda element: element.Name),
    )
    forms_module = module(
        "pyrevit.forms",
        SelectFromList=forms.SelectFromList,
        CommandSwitchWindow=forms.CommandSwitchWindow,
        alert=lambda *args, **kwargs: calls.append("alert"),
        ProgressBar=lambda **kwargs: _Bar(),
    )
    pyrevit = module(
        "pyrevit",
        script=SimpleNamespace(
            get_output=lambda: _Output(), get_logger=lambda: _Logger()
        ),
        DB=db,
        HOST_APP=host_app,
        revit=revit,
    )
    pyrevit.__path__ = []
    stubs = {
        "System": module(
            "System",
            Drawing=SimpleNamespace(
                FontFamily=SimpleNamespace(Families=[SimpleNamespace(Name="Arial")])
            ),
        ),
        "pyrevit": pyrevit,
        "pyrevit.forms": forms_module,
        "pyrevit.revit": module("pyrevit.revit"),
        "pyrevit.revit.db": module("pyrevit.revit.db"),
        "pyrevit.revit.db.create": module(
            "pyrevit.revit.db.create", FamilyLoaderOptionsHandler=object
        ),
        "pyrevit.compat": module(
            "pyrevit.compat",
            get_elementid_value_func=lambda: lambda element_id: element_id,
        ),
    }
    namespace = {"__name__": "replace_fonts_under_test", "__file__": str(SCRIPT)}
    with mock.patch.dict(sys.modules, stubs):
        exec(
            compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), namespace
        )
        namespace["main"]()
    return namespace


@pytest.mark.regression
class ProjectDialogTests(unittest.TestCase):
    """The three toggles map to the three collectors and keep their order."""

    def test_toggles_are_ordered_and_default_to_true(self):
        forms = _Forms("Arial", None, {})
        namespace = _run_project_main(forms, [])

        self.assertIsInstance(forms.switch_arguments, OrderedDict)
        self.assertEqual(
            [
                namespace["SWITCH_FAMILIES"],
                namespace["SWITCH_TEXT_NOTES"],
                namespace["SWITCH_DIMENSIONS"],
            ],
            list(forms.switch_arguments),
        )
        self.assertEqual([True] * 3, list(forms.switch_arguments.values()))

    def test_all_toggles_on_collect_every_type_class(self):
        calls = []
        forms = _Forms("Arial", "Replace Fonts", None)
        names = _run_project_main(_Forms("Arial", None, {}), [])
        forms.switches = dict.fromkeys(
            [
                names["SWITCH_FAMILIES"],
                names["SWITCH_TEXT_NOTES"],
                names["SWITCH_DIMENSIONS"],
            ],
            True,
        )

        _run_project_main(forms, calls)

        self.assertEqual(["Family", "TextNoteType", "DimensionType"], calls)

    def test_each_toggle_alone_runs_only_its_collector(self):
        names = _run_project_main(_Forms("Arial", None, {}), [])
        cases = (
            ("SWITCH_FAMILIES", "Family"),
            ("SWITCH_TEXT_NOTES", "TextNoteType"),
            ("SWITCH_DIMENSIONS", "DimensionType"),
        )
        for enabled, expected in cases:
            with self.subTest(switch=enabled):
                calls = []
                switches = {names[key]: key == enabled for key, _ in cases}
                forms = _Forms("Arial", "Replace Fonts", switches)

                _run_project_main(forms, calls)

                self.assertEqual([expected], calls)

    def test_confirmation_message_names_the_selected_font(self):
        forms = _Forms("Tahoma", None, {})

        _run_project_main(forms, [])

        self.assertIn("Tahoma", forms.message)

    def test_cancel_in_either_step_exits_quietly(self):
        for forms in (_Forms(None, None, {}), _Forms("Arial", None, {})):
            calls = []
            _run_project_main(forms, calls)
            self.assertEqual(["alert"], calls)

    def test_every_switch_lookup_uses_a_constant(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        lookups = [
            node.slice
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and getattr(node.value, "id", "") == "switches"
        ]

        self.assertEqual(3, len(lookups))
        for lookup in lookups:
            self.assertTrue(lookup.id.startswith("SWITCH_"))


if __name__ == "__main__":
    unittest.main()
