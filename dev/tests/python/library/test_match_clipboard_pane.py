"""Check the Match Properties clipboard pane without Revit or WPF."""

import ast
import os
import pickle
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

CLIPBOARD_DIR = (
    Path(__file__).resolve().parents[4]
    / "extensions/pyRevitTools.extension/lib/panes/clipboard"
)
PANE = CLIPBOARD_DIR / "pane.py"
WPF_NS = "{http://schemas.microsoft.com/winfx/2006/xaml/presentation}"
X_NS = "{http://schemas.microsoft.com/winfx/2006/xaml}"


class _Reactive(object):
    def __init__(self):
        pass

    def OnPropertyChanged(self, prop_name):
        self.__dict__.setdefault("_notified", []).append(prop_name)


class _Form(object):
    def merge_resource_dict(self, path):
        self.__dict__.setdefault("_merged", []).append(path)


class _WPFWindow(_Form):
    def __init__(self, xaml_source, literal_string=False, **kwargs):
        self.xaml_source = xaml_source
        self.literal_string = literal_string
        _bind_widgets(self)


class _WPFPanel(_Form):
    panel_source = None

    def __init__(self):
        self.load_xaml(self.panel_source)

    def load_xaml(self, xaml_source, literal_string=False):
        self.xaml_source = xaml_source
        self.literal_string = literal_string


class _PropKeyValue(object):
    def __init__(
        self, name, datatype, value, istype, display_value=None, categories=None
    ):
        self.name = name
        self.datatype = datatype
        self.value = value
        self.istype = istype
        self.display_value = str(display_value or value)
        self.categories = categories if categories is not None else []

    def __eq__(self, other):
        return isinstance(other, _PropKeyValue) and (
            self.name,
            self.datatype,
            self.value,
            self.istype,
        ) == (other.name, other.datatype, other.value, other.istype)

    def __hash__(self):
        return hash((self.name, self.datatype, self.value, self.istype))


def _load_pane(test_class):
    forms = SimpleNamespace(
        Reactive=_Reactive,
        WPFWindow=_WPFWindow,
        WPFPanel=_WPFPanel,
        WPF_COLLAPSED="collapsed",
        WPF_VISIBLE="visible",
    )
    pyrevit = ModuleType("pyrevit")
    pyrevit.__path__ = []
    pyrevit.forms = forms
    pyrevit.revit = SimpleNamespace()
    pyrevit.op = os.path
    pyrevit.script = SimpleNamespace(
        restore_window_position=lambda *a: None, save_window_position=lambda *a: None
    )
    pyrevit.DB = SimpleNamespace(ElementId=type("ElementId", (), {}))
    forms_mod = ModuleType("pyrevit.forms")
    forms_mod.__dict__.update(forms.__dict__)
    forms_mod.__path__ = []
    events_mod = ModuleType("pyrevit.revit.events")
    events_mod.execute_in_revit_context = lambda *a, **k: None
    compat_mod = ModuleType("pyrevit.compat")
    compat_mod.IRONPY = False
    compat_mod.get_elementid_value_func = lambda: lambda value: value
    userconfig_mod = ModuleType("pyrevit.userconfig")
    userconfig_mod.user_config = SimpleNamespace(user_locale="en_us")
    match_pkg = ModuleType("match")
    match_pkg.__path__ = []
    match_utils = ModuleType("match.match_utils")
    match_utils.PropKeyValue = _PropKeyValue
    match_utils.get_source_properties = lambda *a, **k: []
    match_utils.paste_props = lambda *a, **k: None
    filter_utils = ModuleType("match.filter_utils")
    for name in (
        "dissect_parameter_filter",
        "get_color_source_parameter",
        "get_most_common_ogs_brush",
        "get_contrasting_brush",
        "get_ogs_from_prop_in_view",
    ):
        setattr(filter_utils, name, lambda *a, **k: None)
    modules = {
        "pyrevit": pyrevit,
        "pyrevit.forms": forms_mod,
        "pyrevit.revit": pyrevit.revit,
        "pyrevit.revit.events": events_mod,
        "pyrevit.compat": compat_mod,
        "pyrevit.userconfig": userconfig_mod,
        "match": match_pkg,
        "match.match_utils": match_utils,
        "match.filter_utils": filter_utils,
    }
    pyrevit.revit.events = events_mod
    pyrevit.userconfig = userconfig_mod
    namespace = {"__name__": "clipboard_pane_under_test", "__file__": str(PANE)}
    patcher = mock.patch.dict(sys.modules, modules)
    patcher.start()
    test_class.addClassCleanup(patcher.stop)
    source = PANE.read_text(encoding="utf-8")
    exec(compile(source, str(PANE), "exec"), namespace)
    return SimpleNamespace(**namespace)


def _prop(name, value="v", display=None):
    return _PropKeyValue(name, "String", value, False, display_value=display)


class _Widget(object):
    def __init__(self, **attrs):
        self.IsChecked = False
        self.IsEnabled = True
        self.Visibility = None
        self.Text = ""
        self.Content = None
        self.ItemsSource = None
        self.__dict__.update(attrs)

    def Focus(self):
        pass


def _bind_widgets(form):
    form.paramListView = _Widget()
    form.regexToggle_b = _Widget()
    form.search_tb = _Widget()
    form.clrsearch_b = _Widget()
    form.pasteSingleBtn = _Widget()
    form.pasteRectBtn = _Widget()
    form.pasteSelBtn = _Widget()
    form.categoryFilterCheck = _Widget()
    form.loadViewFiltersBtn = _Widget()
    form.loadFilterElemBtn = _Widget()
    form.categoryColumn = _Widget(Width=100)
    form.FindResource = lambda key: "res:" + key
    return form


def _recall_form(pane, memfile=None, target_type="Elements"):
    form = object.__new__(pane.RecallWindow)
    form._init_clipboard(is_recall=True, target_type=target_type, memfile=memfile)
    return _bind_widgets(form)


def _class_bases(tree, class_name):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [ast.unparse(base) for base in node.bases]
    return None


class PaneStructureTests(unittest.TestCase):
    """CPython forms cannot subclass WPF types or call wpf.LoadComponent."""

    @classmethod
    def setUpClass(cls):
        cls.source = PANE.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_no_python_class_derives_from_a_wpf_control(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    self.assertNotIn("UserControl", ast.unparse(base), node.name)

    def test_no_load_component_on_self(self):
        self.assertNotIn("wpf.LoadComponent(self,", self.source)

    def test_forms_derive_from_the_engine_neutral_bases(self):
        self.assertIn("forms.WPFWindow", _class_bases(self.tree, "RecallWindow"))
        self.assertIn(
            "forms.WPFPanel", _class_bases(self.tree, "MatchHistoryClipboard")
        )

    def test_rows_derive_from_forms_reactive(self):
        self.assertEqual(["forms.Reactive"], _class_bases(self.tree, "ParameterItem"))


class ComposedXamlTests(unittest.TestCase):
    """Window and page XAML wrap the one shared grid and bind to the logic."""

    @classmethod
    def setUpClass(cls):
        cls.pane = _load_pane(cls)

    def _composed(self, name):
        return self.pane._compose_xaml(str(CLIPBOARD_DIR / name))

    def test_window_root_is_a_window_holding_the_grid(self):
        root = ET.fromstring(self._composed("clipboard_window.xaml"))
        self.assertEqual(WPF_NS + "Window", root.tag)
        self.assertEqual([WPF_NS + "Grid"], [child.tag for child in root])

    def test_page_root_is_a_page_holding_the_grid(self):
        root = ET.fromstring(self._composed("clipboard_page.xaml"))
        self.assertEqual(WPF_NS + "Page", root.tag)
        self.assertEqual([WPF_NS + "Grid"], [child.tag for child in root])

    def test_every_click_handler_exists_on_the_logic(self):
        root = ET.fromstring(self._composed("clipboard_window.xaml"))
        handlers = set()
        for element in root.iter():
            for attribute in ("Click", "TextChanged"):
                if attribute in element.attrib:
                    handlers.add(element.attrib[attribute])
        self.assertTrue(handlers)
        for handler in handlers:
            self.assertTrue(
                callable(getattr(self.pane._ClipboardLogic, handler, None)), handler
            )

    def test_window_binds_closing_in_xaml(self):
        root = ET.fromstring(self._composed("clipboard_window.xaml"))
        handler = root.attrib["Closing"]
        self.assertTrue(callable(getattr(self.pane.RecallWindow, handler)))

    def test_panel_and_window_load_literal_xaml(self):
        panel = object.__new__(self.pane.MatchHistoryClipboard)
        panel.load_xaml(self.pane._PAGE_XAML)
        window = self.pane.RecallWindow("Elements", [], None)
        for form in (panel, window):
            self.assertTrue(form.literal_string)
            self.assertIn("<Grid", form.xaml_source)
            self.assertNotIn("@@CONTENT@@", form.xaml_source)


class ParameterItemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = _load_pane(cls)

    def test_selection_change_notifies_once_per_change(self):
        item = self.pane.ParameterItem(_prop("Mark"))
        item.IsSelected = True
        item.IsSelected = True
        item.IsSelected = False
        self.assertEqual(["IsSelected", "IsSelected"], item._notified)

    def test_display_fallbacks(self):
        pkv = _prop("Mark", value=7)
        pkv.display_value = None
        self.assertEqual("7", self.pane.ParameterItem(pkv).DisplayValue)
        self.assertEqual("unknown", self.pane.ParameterItem(pkv).Category)
        pkv.categories = [SimpleNamespace(Name="Walls")]
        self.assertEqual("Walls", self.pane.ParameterItem(pkv).Category)
        pkv.categories = ["a", "b"]
        self.assertEqual("multiple", self.pane.ParameterItem(pkv).Category)


class FilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = _load_pane(cls)

    def _form(self):
        form = _recall_form(self.pane)
        form.populate(
            [
                _prop("Mark", "A1", "A1"),
                _prop("Comments", "Fire rated", "Fire rated"),
                _prop("Level", "L2", "L2"),
            ]
        )
        return form

    def _names(self, form):
        return [i.Name for i in form.paramListView.ItemsSource]

    def test_list_order_is_preserved_and_all_rows_start_checked(self):
        form = self._form()
        self.assertEqual(["Mark", "Comments", "Level"], self._names(form))
        self.assertTrue(all(i.IsSelected for i in form._items))

    def test_substring_matches_name_or_value_ignoring_case(self):
        form = self._form()
        form._refresh_list(search_text="FIRE")
        self.assertEqual(["Comments"], self._names(form))
        form._refresh_list(search_text="mar")
        self.assertEqual(["Mark"], self._names(form))

    def test_regex_mode_and_invalid_regex(self):
        form = self._form()
        form.regexToggle_b.IsChecked = True
        form._refresh_list(search_text="^l[0-9e]")
        self.assertEqual(["Level"], self._names(form))
        form._refresh_list(search_text="(")
        self.assertEqual(["Mark", "Comments", "Level"], self._names(form))

    def test_clearing_the_search_shows_everything(self):
        form = self._form()
        form._refresh_list(search_text="Mark")
        form._refresh_list()
        self.assertEqual(3, len(form.paramListView.ItemsSource))

    def test_search_changed_toggles_clear_button(self):
        form = self._form()
        form.search_tb.Text = "mark"
        form.search_changed(None, None)
        self.assertEqual("visible", form.clrsearch_b.Visibility)
        self.assertEqual(["Mark"], self._names(form))
        form.search_tb.Text = ""
        form.search_changed(None, None)
        self.assertEqual("collapsed", form.clrsearch_b.Visibility)

    def test_toggle_regex_swaps_icon(self):
        form = self._form()
        form.regexToggle_b.IsChecked = True
        form.toggle_regex(None, None)
        self.assertEqual("res:regexIcon", form.regexToggle_b.Content)
        form.regexToggle_b.IsChecked = False
        form.toggle_regex(None, None)
        self.assertEqual("res:filterIcon", form.regexToggle_b.Content)


class DedupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = _load_pane(cls)

    def _form(self):
        form = _recall_form(self.pane)
        form.populate(
            [_prop("Mark", "A"), _prop("Mark", "B"), _prop("Level", "L")],
            all_selected=False,
        )
        return form

    def test_check_all_checks_only_first_row_per_name(self):
        form = self._form()
        form.check_all(None, None)
        self.assertEqual([True, False, True], [i.IsSelected for i in form._items])

    def test_checking_a_row_unchecks_same_named_rows(self):
        form = self._form()
        form._items[0].IsSelected = True
        form._items[1].IsSelected = True
        sender = SimpleNamespace(DataContext=form._items[1])
        form.checkbox_click(sender, None)
        self.assertEqual([False, True, False], [i.IsSelected for i in form._items])

    def test_paste_buttons_follow_checked_state(self):
        form = self._form()
        self.assertFalse(form.pasteSingleBtn.IsEnabled)
        form.check_all(None, None)
        self.assertTrue(form.pasteSingleBtn.IsEnabled)
        self.assertTrue(form.pasteRectBtn.IsEnabled)
        self.assertTrue(form.pasteSelBtn.IsEnabled)
        form.uncheck_all(None, None)
        self.assertFalse(form.pasteSelBtn.IsEnabled)


class RecallLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = _load_pane(cls)

    def test_recall_mode_hides_panel_only_controls(self):
        form = _recall_form(self.pane)
        form._finish_clipboard()
        self.assertEqual("collapsed", form.loadViewFiltersBtn.Visibility)
        self.assertEqual("collapsed", form.loadFilterElemBtn.Visibility)
        self.assertEqual("collapsed", form.categoryFilterCheck.Visibility)
        self.assertEqual(0, form.categoryColumn.Width)

    def test_panel_mode_keeps_controls_and_merges_dictionaries_icons_first(self):
        form = _bind_widgets(object.__new__(self.pane.MatchHistoryClipboard))
        form._init_clipboard(is_recall=False)
        form._finish_clipboard()
        self.assertIsNone(form.loadViewFiltersBtn.Visibility)
        self.assertEqual(100, form.categoryColumn.Width)
        merged = [os.path.basename(path) for path in form._merged]
        self.assertEqual(
            ["clipboard.Icons.xaml", "clipboard_ui.ResourceDictionary.en_us.xaml"],
            merged,
        )


class SaveRecallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = _load_pane(cls)

    def _memfile(self):
        handle, path = tempfile.mkstemp()
        os.close(handle)
        os.remove(path)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_checked_rows_are_pickled_with_target_type(self):
        path = self._memfile()
        form = _recall_form(self.pane, memfile=path, target_type="Views")
        form.populate([_prop("Mark", "A"), _prop("Level", "L")])
        form._items[1].IsSelected = False
        form._save_recall()
        with open(path, "rb") as f:
            target_type, props = pickle.loads(f.read())
        self.assertEqual("Views", target_type)
        self.assertEqual(["Mark"], [p.name for p in props])
        self.assertEqual(
            {"name", "datatype", "value", "istype", "display_value", "categories"},
            set(vars(props[0])),
        )

    def test_empty_selection_is_not_saved(self):
        path = self._memfile()
        form = _recall_form(self.pane, memfile=path)
        form.populate([_prop("Mark")], all_selected=False)
        form._save_recall()
        self.assertFalse(os.path.exists(path))

    def test_no_memfile_saves_nothing(self):
        form = _recall_form(self.pane)
        form.populate([_prop("Mark")])
        form._save_recall()


if __name__ == "__main__":
    unittest.main()
