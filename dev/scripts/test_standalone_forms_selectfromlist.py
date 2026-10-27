"""Exercise SelectFromList state and event wiring without importing WPF.

The list double models binding-generated toggle events during ItemsSource
replacement. Native WPF binding, virtualization and input still need a bench run.
"""

import ast
import os
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace


FORMS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pyrevitlib", "pyrevit", "forms")
)


def _load_classes():
    """Compile production state and selection methods with portable dependencies."""
    path = os.path.join(FORMS, "_ipy.py")
    with open(path, encoding="utf-8-sig") as source:
        tree = ast.parse(source.read())
    methods = {
        "_prepare_context_items", "_get_active_ctx", "_get_all_ctx", "_list_options",
        "_unwrap_options", "_get_options", "_set_states", "checkbox_clicked",
        "check_selected", "uncheck_selected", "check_all", "uncheck_all", "toggle_all",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TemplateListItem":
            selected.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == "SelectFromList":
            node.bases = [ast.Name(id="object", ctx=ast.Load())]
            node.body = [
                child for child in node.body
                if isinstance(child, ast.FunctionDef) and child.name in methods
            ]
            selected.append(node)
    tree.body = selected
    ast.fix_missing_locations(tree)
    scope = {
        "Reactive": object,
        "reactive": property,
        "safe_strtype": str,
        "WPF_VISIBLE": "Visible",
        "WPF_COLLAPSED": "Collapsed",
        "coreutils": SimpleNamespace(
            fuzzy_search_ratio=lambda target_string, sfilter, regex: (
                100 if sfilter.lower() in target_string.lower() else 0
            )
        ),
    }
    scope["ObservableCollection"] = type(
        "Collections", (), {"__getitem__": lambda self, _: list}
    )()
    exec(compile(tree, path, "exec"), scope)
    return scope["TemplateListItem"], scope["SelectFromList"]


class _List:
    """Dispatch only events actually wired by the production checkbox template."""

    def __init__(self, window, events):
        self.window = window
        self.events = events
        self.SelectedItems = []
        self._items = []

    @property
    def ItemsSource(self):
        return self._items

    @ItemsSource.setter
    def ItemsSource(self, items):
        for item in self._items:
            self.emit("Unchecked", item, False)
        self.SelectedItems = []
        self._items = items
        for item in items:
            self.emit("Checked" if item.checked else "Unchecked", item, item.checked)

    def emit(self, event, item, state):
        handler = self.events.get(event)
        if handler:
            getattr(self.window, handler)(SimpleNamespace(DataContext=item, IsChecked=state), None)

    def click(self, item, state):
        item.checked = state
        self.emit("Checked" if state else "Unchecked", item, state)
        self.emit("Click", item, state)


class SelectFromListTests(unittest.TestCase):
    def setUp(self):
        item_type, window_type = _load_classes()
        self.window = window_type()
        self.window.multiselect = True
        self.window.filter_func = None
        self.window._nameattr = None
        self.window.return_all = False
        self.window.use_regex = False
        self.window.in_check = self.window.in_uncheck = False
        self.window.get_locale_string = lambda key, fallback: fallback
        for name in ("checkall_b", "uncheckall_b", "toggleall_b"):
            setattr(self.window, name, SimpleNamespace())
        root = ET.parse(os.path.join(FORMS, "SelectFromList.xaml")).getroot()
        checkbox = root.find(".//{http://schemas.microsoft.com/winfx/2006/xaml/presentation}CheckBox")
        self.events = {name: checkbox.attrib[name] for name in ("Click", "Checked", "Unchecked") if name in checkbox.attrib}
        self.window.list_lb = _List(self.window, self.events)
        self.items = self.window._prepare_context_items(["Alpha", "Beta", "Gamma"])
        self.window._context = self.items
        self.window._list_options()

    def test_binding_events_do_not_propagate_to_selected_rows(self):
        self.assertNotIn("Checked", self.events)
        self.assertNotIn("Unchecked", self.events)
        self.assertEqual("checkbox_clicked", self.events.get("Click"))

    def test_hidden_checked_item_survives_filter_and_clear(self):
        alpha = self.items[0]
        self.window.list_lb.SelectedItems = [alpha]
        self.window.list_lb.click(alpha, True)
        self.window._list_options("Beta")
        self.assertTrue(alpha.checked)
        self.assertEqual(["Alpha"], self.window._get_options())
        self.window._list_options()
        self.assertIs(alpha, self.window.list_lb.ItemsSource[0])
        self.assertTrue(alpha.checked)

    def test_visible_checked_item_survives_repeated_filters(self):
        alpha = self.items[0]
        self.window.list_lb.click(alpha, True)
        for text in ("Al", "Alpha", "", "Beta", ""):
            self.window._list_options(text)
            self.assertTrue(alpha.checked)

    def test_click_toggles_sender_and_selected_rows(self):
        alpha, beta, gamma = self.items
        self.window.list_lb.SelectedItems = [beta]
        for state in (True, False):
            self.window.list_lb.click(alpha, state)
            self.assertEqual(state, alpha.checked)
            self.assertEqual(state, beta.checked)
            self.assertFalse(gamma.checked)

    def test_bulk_actions_only_change_visible_items(self):
        alpha, beta, gamma = self.items
        self.window.list_lb.click(alpha, True)
        self.window._list_options("Beta")
        self.window.check_all(None, None)
        self.assertEqual([True, True, False], [item.checked for item in self.items])
        self.window.uncheck_all(None, None)
        self.assertEqual([True, False, False], [item.checked for item in self.items])
        self.window.toggle_all(None, None)
        self.assertEqual([True, True, False], [item.checked for item in self.items])
        self.window._list_options()
        self.assertEqual(["Alpha", "Beta"], self.window._get_options())

    def test_group_switch_preserves_checked_wrappers(self):
        self.window._context = {"First": self.items[:1], "Second": self.items[1:]}
        self.window._get_active_ctx_group = lambda: self.group
        self.group = "First"
        self.window._list_options()
        self.window.list_lb.click(self.items[0], True)
        self.group = "Second"
        self.window._list_options()
        self.window.check_all(None, None)
        self.group = "First"
        self.window._list_options()
        self.assertTrue(self.items[0].checked)
        self.assertEqual(["Alpha", "Beta", "Gamma"], self.window._get_options())


if __name__ == "__main__":
    unittest.main()
