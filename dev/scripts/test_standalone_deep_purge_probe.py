"""Host-free tests for how Deep Purge decides an item is unused."""

import importlib.util
import os
import sys
import types
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROBE_PATH = os.path.join(
    REPO_ROOT,
    "extensions",
    "pyRevitTools.extension",
    "pyRevit.tab",
    "Project.panel",
    "Wipe.pulldown",
    "Deep Purge.pushbutton",
    "purge_probe.py",
)


class _Event(object):
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self


class _FailureMessages(object):
    def __init__(self, count):
        self.Count = count


class _FailuresAccessor(object):
    def __init__(self, count):
        self._count = count

    def GetFailureMessages(self):
        return _FailureMessages(self._count)


COMMITTED = "TransactionCommitted"
GROUP_ROLLED_BACK = "TransactionGroupRolledBack"


class _ChangedArgs(object):
    def __init__(self, doc, deleted, modified, added, operation=COMMITTED):
        self._doc = doc
        self._deleted = deleted
        self._modified = modified
        self._added = added
        self.Operation = operation

    def GetDocument(self):
        return self._doc

    def GetDeletedElementIds(self):
        return self._deleted

    def GetModifiedElementIds(self):
        return self._modified

    def GetAddedElementIds(self):
        return self._added


class _FakeDoc(object):
    def __init__(self, effects):
        self.Application = types.SimpleNamespace(DocumentChanged=_Event())
        self.effects = effects
        self.existing = set(effects)
        self.pending = []
        self._group_snapshot = None

    def Equals(self, other):
        return other is self

    def GetElement(self, element_id):
        return object() if element_id in self.existing else None

    def Delete(self, element_id):
        if self.effects[element_id].get("raises"):
            raise Exception("cannot delete")
        self.pending.append(element_id)

    def _fire(self, args):
        for handler in list(self.Application.DocumentChanged.handlers):
            handler(None, args)

    def commit(self, preprocessor):
        element_ids, self.pending = self.pending, []
        effects = [self.effects[x] for x in element_ids]
        failure_count = sum(x.get("failures", 0) for x in effects)
        if failure_count:
            if preprocessor:
                preprocessor.PreprocessFailures(_FailuresAccessor(failure_count))
            return
        self.existing.difference_update(element_ids)
        self.existing.difference_update(
            i for x in effects for i in x.get("deleted", [])
        )
        if not any(effects):
            return
        self._fire(
            _ChangedArgs(
                self,
                [i for x in effects for i in x.get("deleted", [])],
                [i for x in effects for i in x.get("modified", [])],
                [i for x in effects for i in x.get("added", [])],
            )
        )

    def roll_back(self):
        self.pending = []

    def start_group(self):
        self._group_snapshot = set(self.existing)

    def roll_back_group(self):
        restored = self._group_snapshot - self.existing
        self.existing = self._group_snapshot
        self._fire(_ChangedArgs(self, [77], [78], list(restored), GROUP_ROLLED_BACK))


class _Transaction(object):
    def __init__(self, name=None, doc=None, failures_preprocessor=None, **_):
        self._doc = doc
        self._preprocessor = failures_preprocessor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._doc.commit(self._preprocessor)
        else:
            self._doc.roll_back()


class _DryTransactionGroup(object):
    def __init__(self, name=None, doc=None, **_):
        self._doc = doc

    def __enter__(self):
        self._doc.start_group()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._doc.roll_back_group()
        return False


def _load_probe():
    db = types.SimpleNamespace(
        IFailuresPreprocessor=object,
        FailureProcessingResult=types.SimpleNamespace(
            Continue="Continue", ProceedWithRollBack="ProceedWithRollBack"
        ),
        Events=types.SimpleNamespace(DocumentChangedEventArgs=object),
        UndoOperation=types.SimpleNamespace(TransactionCommitted=COMMITTED),
        GraphicsStyleType=types.SimpleNamespace(Projection=1, Cut=2),
        LinePatternElement=object,
        FillPatternElement=object,
        SharedParameterElement=object,
    )
    revit = types.ModuleType("pyrevit.revit")
    revit.Transaction = _Transaction
    revit.DryTransactionGroup = _DryTransactionGroup
    revit.query = types.SimpleNamespace()
    revit.events = types.SimpleNamespace(create_handler=lambda func, _: func)
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.revit = revit
    pyrevit.DB = db
    pyrevit.EXEC_PARAMS = types.SimpleNamespace(exec_id="PyRevitTest")
    compat = types.ModuleType("pyrevit.compat")
    compat.get_elementid_value_func = lambda: lambda element_id: element_id
    stubs = {"pyrevit": pyrevit, "pyrevit.revit": revit, "pyrevit.compat": compat}
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location("purge_probe", PROBE_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module


def _raise(*_):
    raise RuntimeError("progress bar closed")


class _Progress(object):
    def __init__(self, cancel_after=None):
        self.cancelled = False
        self.updates = []
        self._cancel_after = cancel_after

    def update_progress(self, value, max_value):
        self.updates.append((value, max_value))
        if self._cancel_after is not None and value >= self._cancel_after:
            self.cancelled = True


class FindUnusedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = _load_probe()

    def _candidate(self, element_id, companions=()):
        return self.probe._make_candidate(
            "Line Patterns", element_id, "item {}".format(element_id), "", companions
        )

    def test_deleting_only_itself_is_unused(self):
        doc = _FakeDoc({10: {"deleted": [10]}})
        result = self.probe.find_unused(doc, [self._candidate(10)])
        self.assertEqual([x.element_id for x in result], [10])

    def test_modifying_another_element_means_in_use(self):
        doc = _FakeDoc({10: {"deleted": [10], "modified": [99]}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_deleting_another_element_means_in_use(self):
        doc = _FakeDoc({10: {"deleted": [10, 11]}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_companion_ids_do_not_count_as_usage(self):
        doc = _FakeDoc({10: {"deleted": [10, 21, 22], "modified": [21]}})
        candidate = self._candidate(10, companions=[21, 22])
        self.assertEqual(self.probe.find_unused(doc, [candidate]), [candidate])

    def test_failures_mean_in_use(self):
        doc = _FakeDoc({10: {"deleted": [10], "failures": 1}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_refused_delete_means_in_use(self):
        doc = _FakeDoc({10: {"raises": True}, 11: {"deleted": [11]}})
        result = self.probe.find_unused(doc, [self._candidate(10), self._candidate(11)])
        self.assertEqual([x.element_id for x in result], [11])

    def test_no_change_event_means_in_use(self):
        doc = _FakeDoc({10: {}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_changes_in_other_documents_are_ignored(self):
        doc = _FakeDoc({10: {"deleted": [10]}})
        other = _FakeDoc({})
        recorder = self.probe._ChangeRecorder(doc)
        recorder.record(None, _ChangedArgs(other, [5], [6], []))
        self.assertFalse(recorder.changed)

    def test_handler_is_removed_after_checking(self):
        doc = _FakeDoc({10: {"deleted": [10]}})
        self.probe.find_unused(doc, [self._candidate(10)])
        self.assertEqual(doc.Application.DocumentChanged.handlers, [])

    def test_handler_is_removed_when_a_check_raises(self):
        doc = _FakeDoc({10: {"deleted": [10]}})
        progress = types.SimpleNamespace(cancelled=False, update_progress=_raise)
        with self.assertRaises(RuntimeError):
            self.probe.find_unused(doc, [self._candidate(10)], progress_bar=progress)
        self.assertEqual(doc.Application.DocumentChanged.handlers, [])

    def test_cancelled_progress_stops_checking(self):
        doc = _FakeDoc({x: {"deleted": [x]} for x in (10, 11, 12)})
        progress = _Progress(cancel_after=1)
        result = self.probe.find_unused(
            doc, [self._candidate(x) for x in (10, 11, 12)], progress_bar=progress
        )
        self.assertEqual([x.element_id for x in result], [10])
        self.assertEqual(progress.updates, [(1, 3)])


class PurgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = _load_probe()

    def _candidates(self, *element_ids):
        return [
            self.probe._make_candidate("Fill Patterns", x, "p{}".format(x))
            for x in element_ids
        ]

    def test_refused_delete_is_reported_and_others_are_purged(self):
        doc = _FakeDoc({10: {"raises": True}, 11: {"deleted": [11]}})
        purged, failed = self.probe.purge(doc, self._candidates(10, 11))
        self.assertEqual([x.element_id for x in purged], [11])
        self.assertEqual(
            [(c.element_id, err) for c, err in failed], [(10, "cannot delete")]
        )

    def test_rolled_back_commit_reports_every_item_as_failed(self):
        doc = _FakeDoc({10: {"deleted": [10]}, 11: {"deleted": [11], "failures": 1}})
        purged, failed = self.probe.purge(doc, self._candidates(10, 11))
        self.assertEqual(purged, [])
        self.assertEqual(
            [(c.element_id, err) for c, err in failed],
            [(10, self.probe.ROLLED_BACK), (11, self.probe.ROLLED_BACK)],
        )

    def test_line_style_counts_as_purged_once_its_graphics_style_is_gone(self):
        doc = _FakeDoc({5: {"deleted": [5, 6]}, 6: {}})
        candidate = self.probe._make_candidate(
            "Line Styles", 5, "style", companion_ids=[6]
        )
        self.assertEqual(candidate.witness_id, 6)
        self.assertEqual(self.probe.purge(doc, [candidate]), ([candidate], []))


if __name__ == "__main__":
    unittest.main()
