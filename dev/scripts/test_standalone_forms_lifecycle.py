"""Portable tests for forms helpers whose engine contracts need no Revit host."""

import ast
import datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


FORMS = Path(__file__).resolve().parents[2] / "pyrevitlib" / "pyrevit" / "forms"


def _load_shared():
    spec = importlib.util.spec_from_file_location(
        "forms_backend_shared", FORMS / "backends" / "_shared.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            "_pane_show.py",
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


class _Selector(object):
    def __init__(self, items_source):
        self.ItemsSource = items_source


class ResetCallbackTests(unittest.TestCase):
    """Reset callbacks see the listed items and their changes reach the list."""

    @staticmethod
    def _backend(engine):
        shared = _load_shared()
        scope = _load(
            "backends/{}.py".format(engine),
            {"items_of", "rebind_if_changed"},
            {
                "same_items": shared.same_items,
                "unwrap_item": lambda value: value.item,
                "list_source": lambda values: [_Proxy(v) for v in values],
            },
        )
        return SimpleNamespace(**scope)

    def _reset(self, engine, items_source, reset_func):
        scope = _load(
            "listdialog.py",
            {"button_reset"},
            {"_backend": self._backend(engine)},
            class_name="SelectFromList",
        )
        dialog = SimpleNamespace(list_lb=_Selector(items_source), reset_func=reset_func)
        scope["button_reset"](dialog, None, None)
        return dialog

    def test_ironpython_items_receive_the_live_collection(self):
        """IronPython callbacks mutate the bound ItemsSource itself."""
        live = ["a", "b"]
        observed = []

        def reset(values):
            observed.append(values)
            values.remove("b")

        dialog = self._reset("_ipy", live, reset)
        self.assertIs(live, observed[0])
        self.assertIs(live, dialog.list_lb.ItemsSource)
        self.assertEqual(["a"], live)

    def test_proxied_items_are_unwrapped_and_rebound_after_changes(self):
        """CPython callbacks get Python items; list edits are rebound."""
        first, second = object(), object()
        observed = []

        def reset(values):
            observed.append(list(values))
            values.remove(second)

        dialog = self._reset("_cpy", [_Proxy(first), _Proxy(second)], reset)
        self.assertEqual([[first, second]], observed)
        self.assertEqual([first], [p.item for p in dialog.list_lb.ItemsSource])

    def test_proxied_items_keep_their_binding_when_unchanged(self):
        """Unchanged CPython lists keep the existing bound collection."""
        proxies = [_Proxy(object())]
        dialog = self._reset("_cpy", proxies, lambda values: None)
        self.assertIs(proxies, dialog.list_lb.ItemsSource)


class SharedBackendTests(unittest.TestCase):
    """Engine-neutral helpers behave the same for both backends."""

    def setUp(self):
        """Load the shared helpers without WPF."""
        self.shared = _load_shared()

    def test_same_items_compares_identity_and_order(self):
        """Equal but distinct objects, or a reordering, count as a change."""
        first, second = [1000], [1000]
        self.assertTrue(self.shared.same_items([first, second], (first, second)))
        self.assertFalse(self.shared.same_items([first, second], [second, first]))
        self.assertFalse(self.shared.same_items([first], [[1000]]))
        self.assertFalse(self.shared.same_items([first], [first, second]))

    def test_disposing_disposes_only_on_failure(self):
        """A failed construction disposes the form and re-raises the error."""
        disposed = []
        target = object()
        with self.shared.Disposing(target, disposed.append) as entered:
            self.assertIs(target, entered)
        self.assertEqual([], disposed)
        with self.assertRaises(ValueError):
            with self.shared.Disposing(target, disposed.append):
                raise ValueError("setup failed")
        self.assertEqual([target], disposed)

    def test_disposing_ignores_system_exit(self):
        """Only errors dispose; exiting the script leaves the form alone."""
        disposed = []
        with self.assertRaises(SystemExit):
            with self.shared.Disposing(object(), disposed.append):
                raise SystemExit()
        self.assertEqual([], disposed)

    def test_pane_options_copy_only_set_values(self):
        """Unset pane options keep Revit's defaults on the target."""
        panel = SimpleNamespace(
            initial_state="state", editor_interaction=None, contextual_help="help"
        )
        target = SimpleNamespace(EditorInteraction="default")
        self.shared.apply_pane_options(panel, target)
        self.assertEqual("state", target.InitialState)
        self.assertEqual("default", target.EditorInteraction)
        self.assertEqual("help", target.ContextualHelp)


if __name__ == "__main__":
    unittest.main()
