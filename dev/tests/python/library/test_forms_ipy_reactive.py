"""Regression tests for #4179: IronPython ``forms.Reactive`` keeps listeners per instance."""

import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

import pytest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

ROOT = Path(__file__).resolve().parents[4]
IPY_BACKEND = ROOT / "pyrevitlib/pyrevit/forms/backends/_ipy.py"
PYEVENT = ROOT / "site-packages/pyevent.py"


def _load_reactive():
    spec = importlib.util.spec_from_file_location("pyevent_under_test", PYEVENT)
    pyevent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pyevent)
    tree = ast.parse(IPY_BACKEND.read_text(encoding="utf-8"))
    tree.body = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Reactive"
    ]
    namespace = {
        "pyevent": pyevent,
        "ComponentModel": SimpleNamespace(
            INotifyPropertyChanged=object,
            PropertyChangedEventArgs=lambda name: SimpleNamespace(PropertyName=name),
        ),
    }
    exec(compile(tree, str(IPY_BACKEND), "exec"), namespace)
    return namespace["Reactive"]


@pytest.mark.regression
class ReactiveListenerTests(unittest.TestCase):
    """A row notifies only the listeners registered on that row."""

    def setUp(self):
        self.Reactive = _load_reactive()

    def test_listeners_are_not_shared_between_instances(self):
        first, second = self.Reactive(), self.Reactive()
        calls = []
        first.add_PropertyChanged(lambda sender, args: calls.append(("first", args)))
        second.add_PropertyChanged(lambda sender, args: calls.append(("second", args)))
        first.OnPropertyChanged("IsSelected")
        self.assertEqual(["first"], [name for name, _ in calls])
        self.assertEqual("IsSelected", calls[0][1].PropertyName)

    def test_remove_detaches_only_that_listener(self):
        row = self.Reactive()
        calls = []

        def listener(sender, args):
            calls.append(args.PropertyName)

        row.add_PropertyChanged(listener)
        row.remove_PropertyChanged(listener)
        row.OnPropertyChanged("Name")
        self.assertEqual([], calls)

    def test_event_syntax_still_works(self):
        row = self.Reactive()
        calls = []
        row.PropertyChanged += lambda sender, args: calls.append(sender)
        row.OnPropertyChanged("Name")
        self.assertEqual([row], calls)

    def test_notifying_without_listeners_is_harmless(self):
        self.Reactive().OnPropertyChanged("Name")
