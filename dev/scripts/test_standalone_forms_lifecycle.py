"""Portable tests for forms helpers whose engine contracts need no Revit host."""

import ast
import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest


FORMS = Path(__file__).resolve().parents[2] / "pyrevitlib" / "pyrevit" / "forms"


def _load(module, names, scope, class_name=None):
    tree = ast.parse((FORMS / module).read_text(encoding="utf-8"))
    body = tree.body
    if class_name:
        body = next(node for node in body if getattr(node, "name", None) == class_name)
        body = body.body
    tree.body = [node for node in body if getattr(node, "name", None) in names]
    exec(compile(tree, module, "exec"), scope)
    return scope


class _Dictionary(dict):
    def ContainsKey(self, key):
        return key in self


class PendingDockableShowTests(unittest.TestCase):
    """A pending show left by a dead handler must not block later shows."""

    def setUp(self):
        """Load the pending-show helpers with a deterministic token source."""
        guids = iter(["first", "second", "third"])
        self.scope = _load(
            "dockable.py",
            {
                "_pending_entry",
                "_pending_entry_token",
                "_pending_entry_is_stale",
                "_claim_pending_show",
            },
            {
                "_PENDING_SHOW_STALE_SECONDS": 10,
                "framework": SimpleNamespace(
                    System=SimpleNamespace(
                        Guid=SimpleNamespace(
                            NewGuid=lambda: SimpleNamespace(
                                ToString=lambda: next(guids)
                            )
                        )
                    )
                ),
            },
        )
        self.claim = self.scope["_claim_pending_show"]

    def test_live_show_is_not_duplicated(self):
        """A show with a recent heartbeat keeps its token."""
        pending = _Dictionary()
        self.assertEqual("first", self.claim(pending, "pane", 100.0))
        self.assertIsNone(self.claim(pending, "pane", 105.0))
        self.assertEqual("first", self.scope["_pending_entry_token"](pending["pane"]))

    def test_show_without_recent_heartbeat_is_replaced(self):
        """A show whose handler stopped beating is taken over."""
        pending = _Dictionary()
        self.claim(pending, "pane", 100.0)
        self.assertEqual("second", self.claim(pending, "pane", 111.0))
        self.assertEqual("second", self.scope["_pending_entry_token"](pending["pane"]))

    def test_legacy_and_future_entries_are_replaced(self):
        """Entries without a valid recent heartbeat never block a show."""
        pending = _Dictionary(pane="token-without-heartbeat", other="x|200.0")
        self.assertEqual("first", self.claim(pending, "pane", 100.0))
        self.assertEqual("second", self.claim(pending, "other", 100.0))


class BalloonTimestampTests(unittest.TestCase):
    """InfoCenter receives a managed DateTime from both engines."""

    def test_python_datetime_is_converted(self):
        """Python datetimes become DateTime; managed values pass through."""
        scope = _load(
            "notify.py",
            {"_to_clr_datetime"},
            {"datetime": datetime, "System": SimpleNamespace(DateTime=lambda *a: a)},
        )
        convert = scope["_to_clr_datetime"]
        value = datetime.datetime(2019, 1, 2, 3, 4, 5, 678999)
        self.assertEqual((2019, 1, 2, 3, 4, 5, 678), convert(value))
        managed = object()
        self.assertIs(managed, convert(managed))


class PickFileTests(unittest.TestCase):
    """Multi-file picks return a Python list, as documented."""

    def test_multi_file_returns_list(self):
        """The managed String[] is copied into a list."""
        dialog = SimpleNamespace(ShowDialog=lambda: "ok", FileNames=("a", "b"))
        scope = _load(
            "native.py",
            {"pick_file"},
            {
                "Forms": SimpleNamespace(
                    OpenFileDialog=lambda: dialog,
                    DialogResult=SimpleNamespace(OK="ok"),
                )
            },
        )
        self.assertEqual(["a", "b"], scope["pick_file"](multi_file=True))


class _Proxy(object):
    def __init__(self, item):
        self.item = item


class ResetCallbackTests(unittest.TestCase):
    """Reset callbacks see the listed items and their changes reach the list."""

    @staticmethod
    def _dialog(items_source, unwrap, reset_func):
        scope = _load(
            "listdialog.py",
            {"button_reset"},
            {
                "_backend": SimpleNamespace(
                    unwrap_item=unwrap,
                    list_source=lambda values: [_Proxy(v) for v in values],
                )
            },
            class_name="SelectFromList",
        )
        dialog = SimpleNamespace(
            list_lb=SimpleNamespace(ItemsSource=items_source), reset_func=reset_func
        )
        scope["button_reset"](dialog, None, None)
        return dialog

    def test_native_items_receive_the_live_collection(self):
        """IronPython callbacks mutate the bound ItemsSource itself."""
        live = ["a", "b"]
        observed = []
        self._dialog(live, lambda value: value, observed.append)
        self.assertIs(live, observed[0])

    def test_proxied_items_are_unwrapped_and_rebound_after_changes(self):
        """CPython callbacks get Python items; list edits are rebound."""
        first, second = object(), object()
        observed = []

        def reset(values):
            observed.append(list(values))
            values.remove(second)

        dialog = self._dialog(
            [_Proxy(first), _Proxy(second)], lambda value: value.item, reset
        )
        self.assertEqual([[first, second]], observed)
        self.assertEqual([first], [p.item for p in dialog.list_lb.ItemsSource])

    def test_proxied_items_keep_their_binding_when_unchanged(self):
        """Unchanged CPython lists keep the existing bound collection."""
        proxies = [_Proxy(object())]
        dialog = self._dialog(proxies, lambda value: value.item, lambda values: None)
        self.assertIs(proxies, dialog.list_lb.ItemsSource)


if __name__ == "__main__":
    unittest.main()
