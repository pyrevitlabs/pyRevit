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


LINE_PATTERN_ELEMENT = type("LinePatternElement", (), {})
FILL_PATTERN_ELEMENT = type("FillPatternElement", (), {})
SHARED_PARAMETER_ELEMENT = type("SharedParameterElement", (), {})
VIEW = type("View", (), {})
BUILTIN_CATEGORY_VALUES = (-2000500, -2000501, -2000502)
PROJECTION = 1
CUT = 2


class _RecordingLogger(object):
    def __init__(self):
        self.debug_calls = []
        self.warning_calls = []

    def debug(self, message, *args):
        self.debug_calls.append(message % args)

    def warning(self, message, *args):
        self.warning_calls.append(message % args)


class _Category(object):
    def __init__(
        self,
        projection_pattern_id,
        cut_pattern_id=-1,
        subcategories=(),
        category_id=None,
    ):
        self._pattern_ids = {PROJECTION: projection_pattern_id, CUT: cut_pattern_id}
        self.SubCategories = list(subcategories)
        self.Id = category_id

    def GetLinePatternId(self, style_type):
        return self._pattern_ids[style_type]


def _overrides(**pattern_ids):
    values = {name: -1 for name in OVERRIDE_PATTERN_PROPERTIES}
    values.update(pattern_ids)
    return types.SimpleNamespace(**values)


OVERRIDE_PATTERN_PROPERTIES = (
    "ProjectionLinePatternId",
    "CutLinePatternId",
    "SurfaceForegroundPatternId",
    "SurfaceBackgroundPatternId",
    "CutForegroundPatternId",
    "CutBackgroundPatternId",
)


class _View(object):
    def __init__(
        self,
        category_overrides=None,
        filter_overrides=None,
        overrides_allowed=True,
        overridable_category_ids=None,
    ):
        self._category_overrides = category_overrides or {}
        self._filter_overrides = filter_overrides or {}
        self._overrides_allowed = overrides_allowed
        self._overridable = overridable_category_ids

    def AreGraphicsOverridesAllowed(self):
        return self._overrides_allowed

    def GetFilters(self):
        if not self._overrides_allowed:
            raise AssertionError("GetFilters called on a view without overrides")
        return list(self._filter_overrides)

    def GetFilterOverrides(self, filter_id):
        return self._filter_overrides[filter_id]

    def IsCategoryOverridable(self, category_id):
        return self._overridable is None or category_id in self._overridable

    def GetCategoryOverrides(self, category_id):
        if not self.IsCategoryOverridable(category_id):
            raise AssertionError("category {} is not overridable".format(category_id))
        return self._category_overrides.get(category_id, _overrides())


def _collector_doc(
    categories=(),
    elements_by_class=None,
    bound_definitions=(),
    builtin_categories=None,
):
    return types.SimpleNamespace(
        Settings=types.SimpleNamespace(Categories=list(categories)),
        builtin_categories=builtin_categories or {},
        ParameterBindings=types.SimpleNamespace(
            Contains=lambda definition: definition in bound_definitions
        ),
        elements_by_class=elements_by_class or {},
        line_categories=[],
    )


def _line_pattern(element_id):
    return types.SimpleNamespace(Id=element_id, Name="pattern {}".format(element_id))


def _fill_pattern(element_id):
    return types.SimpleNamespace(
        Id=element_id,
        Name="fill {}".format(element_id),
        GetFillPattern=lambda: types.SimpleNamespace(
            IsSolidFill=False, Target="Drafting"
        ),
    )


def _shared_parameter(element_id):
    return types.SimpleNamespace(
        Id=element_id,
        Name="parameter {}".format(element_id),
        GuidValue="guid-{}".format(element_id),
        GetDefinition=lambda: "definition-{}".format(element_id),
    )


def _load_probe():
    db = types.SimpleNamespace(
        IFailuresPreprocessor=object,
        FailureProcessingResult=types.SimpleNamespace(
            Continue="Continue", ProceedWithRollBack="ProceedWithRollBack"
        ),
        Events=types.SimpleNamespace(
            DocumentChangedEventArgs=object,
            UndoOperation=types.SimpleNamespace(TransactionCommitted=COMMITTED),
        ),
        GraphicsStyleType=types.SimpleNamespace(Projection=PROJECTION, Cut=CUT),
        LinePatternElement=LINE_PATTERN_ELEMENT,
        FillPatternElement=FILL_PATTERN_ELEMENT,
        SharedParameterElement=SHARED_PARAMETER_ELEMENT,
        View=VIEW,
        BuiltInCategory=types.SimpleNamespace(
            GetValues=lambda _: list(BUILTIN_CATEGORY_VALUES)
        ),
        Category=types.SimpleNamespace(
            GetCategory=lambda doc, value: doc.builtin_categories.get(value)
        ),
    )
    revit = types.ModuleType("pyrevit.revit")
    revit.Transaction = _Transaction
    revit.DryTransactionGroup = _DryTransactionGroup
    revit.query = types.SimpleNamespace(
        get_elements_by_class=lambda cls, doc: doc.elements_by_class.get(cls, []),
        get_name=lambda element: element.Name,
        get_line_categories=lambda doc: doc.line_categories,
    )
    revit.events = types.SimpleNamespace(create_handler=lambda func, _: func)
    pyrevit = types.ModuleType("pyrevit")
    pyrevit.revit = revit
    pyrevit.DB = db
    pyrevit.EXEC_PARAMS = types.SimpleNamespace(exec_id="PyRevitTest")
    compat = types.ModuleType("pyrevit.compat")
    compat.get_elementid_value_func = lambda: lambda element_id: element_id
    coreutils = types.ModuleType("pyrevit.coreutils")
    logger_module = types.ModuleType("pyrevit.coreutils.logger")
    logger_module.get_logger = lambda name: _RecordingLogger()
    coreutils.logger = logger_module
    stubs = {
        "pyrevit": pyrevit,
        "pyrevit.revit": revit,
        "pyrevit.compat": compat,
        "pyrevit.coreutils": coreutils,
        "pyrevit.coreutils.logger": logger_module,
    }
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
    """Check how a rolled-back trial deletion classifies a candidate."""

    @classmethod
    def setUpClass(cls):
        """Load the probe once with the pyrevit and Revit stubs."""
        cls.probe = _load_probe()

    def _candidate(self, element_id, companions=()):
        return self.probe._make_candidate(
            "Line Patterns", element_id, "item {}".format(element_id), "", companions
        )

    def test_deleting_only_itself_is_unused(self):
        """Offer an item whose deletion removes nothing but itself."""
        doc = _FakeDoc({10: {"deleted": [10]}})
        result = self.probe.find_unused(doc, [self._candidate(10)])
        self.assertEqual([x.element_id for x in result], [10])

    def test_modifying_another_element_means_in_use(self):
        """Keep an item whose deletion changes another element."""
        doc = _FakeDoc({10: {"deleted": [10], "modified": [99]}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_deleting_another_element_means_in_use(self):
        """Keep an item whose deletion takes another element with it."""
        doc = _FakeDoc({10: {"deleted": [10, 11]}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_companion_ids_do_not_count_as_usage(self):
        """Ignore changes to the item's own graphics styles."""
        doc = _FakeDoc({10: {"deleted": [10, 21, 22], "modified": [21]}})
        candidate = self._candidate(10, companions=[21, 22])
        self.assertEqual(self.probe.find_unused(doc, [candidate]), [candidate])

    def test_failures_mean_in_use(self):
        """Keep an item whose deletion raises warnings or errors."""
        doc = _FakeDoc({10: {"deleted": [10], "failures": 1}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_refused_delete_means_in_use_and_is_logged(self):
        """Keep a refused item, log why, and keep checking the rest."""
        doc = _FakeDoc({10: {"raises": True}, 11: {"deleted": [11]}})
        self.probe.logger.debug_calls[:] = []
        result = self.probe.find_unused(doc, [self._candidate(10), self._candidate(11)])
        self.assertEqual([x.element_id for x in result], [11])
        self.assertEqual(len(self.probe.logger.debug_calls), 1)
        self.assertIn("item 10", self.probe.logger.debug_calls[0])

    def test_no_change_event_means_in_use(self):
        """Keep an item when the commit reports no change."""
        doc = _FakeDoc({10: {}})
        self.assertEqual(self.probe.find_unused(doc, [self._candidate(10)]), [])

    def test_commits_without_any_change_event_are_warned_about(self):
        """Warn once when no check ever produced a change event."""
        doc = _FakeDoc({10: {}, 11: {}})
        self.probe.logger.warning_calls[:] = []
        self.probe.find_unused(doc, [self._candidate(10), self._candidate(11)])
        self.assertEqual(len(self.probe.logger.warning_calls), 1)
        self.assertIn("2 checks", self.probe.logger.warning_calls[0])

    def test_no_warning_once_a_change_event_is_seen(self):
        """Stay quiet when at least one check produced an event."""
        doc = _FakeDoc({10: {}, 11: {"deleted": [11]}})
        self.probe.logger.warning_calls[:] = []
        self.probe.find_unused(doc, [self._candidate(10), self._candidate(11)])
        self.assertEqual(self.probe.logger.warning_calls, [])

    def test_no_warning_when_every_delete_is_refused(self):
        """Stay quiet when nothing was committed at all."""
        doc = _FakeDoc({10: {"raises": True}})
        self.probe.logger.warning_calls[:] = []
        self.probe.find_unused(doc, [self._candidate(10)])
        self.assertEqual(self.probe.logger.warning_calls, [])

    def test_line_style_is_unused_when_only_its_graphics_styles_are_deleted(self):
        """Match line styles by graphics style, not subcategory id."""
        doc = _FakeDoc({5: {"deleted": [21, 22]}})
        candidate = self._candidate(5, companions=[21, 22])
        self.assertEqual(self.probe.find_unused(doc, [candidate]), [candidate])

    def test_rollback_events_are_not_taken_for_commits(self):
        """Ignore the event raised by rolling back the group."""
        doc = _FakeDoc({10: {}})
        recorder = self.probe._ChangeRecorder(doc)
        recorder.record(None, _ChangedArgs(doc, [10], [], [], GROUP_ROLLED_BACK))
        self.assertFalse(recorder.changed)
        self.assertFalse(recorder.commit_seen)

    def test_changes_in_other_documents_are_ignored(self):
        """Ignore change events from other open documents."""
        doc = _FakeDoc({10: {"deleted": [10]}})
        other = _FakeDoc({})
        recorder = self.probe._ChangeRecorder(doc)
        recorder.record(None, _ChangedArgs(other, [5], [6], []))
        self.assertFalse(recorder.changed)

    def test_handler_is_removed_after_checking(self):
        """Unsubscribe from DocumentChanged after a normal run."""
        doc = _FakeDoc({10: {"deleted": [10]}})
        self.probe.find_unused(doc, [self._candidate(10)])
        self.assertEqual(doc.Application.DocumentChanged.handlers, [])

    def test_handler_is_removed_when_a_check_raises(self):
        """Unsubscribe from DocumentChanged even when checking raises."""
        doc = _FakeDoc({10: {"deleted": [10]}})
        progress = types.SimpleNamespace(cancelled=False, update_progress=_raise)
        with self.assertRaises(RuntimeError):
            self.probe.find_unused(doc, [self._candidate(10)], progress_bar=progress)
        self.assertEqual(doc.Application.DocumentChanged.handlers, [])

    def test_cancelled_progress_stops_checking(self):
        """Stop at the candidate where the progress bar was cancelled."""
        doc = _FakeDoc({x: {"deleted": [x]} for x in (10, 11, 12)})
        progress = _Progress(cancel_after=1)
        result = self.probe.find_unused(
            doc, [self._candidate(x) for x in (10, 11, 12)], progress_bar=progress
        )
        self.assertEqual([x.element_id for x in result], [10])
        self.assertEqual(progress.updates, [(1, 3)])


class CollectorTests(unittest.TestCase):
    """Check usage that raises no change event is excluded before probing."""

    @classmethod
    def setUpClass(cls):
        """Load the probe once with the pyrevit and Revit stubs."""
        cls.probe = _load_probe()

    def _collect(self, collector, doc):
        return collector(doc, self.probe._PatternUsage(doc))

    def test_line_patterns_set_in_object_styles_are_not_candidates(self):
        """Exclude patterns set on categories or subcategories in Object Styles."""
        doc = _collector_doc(
            categories=[
                _Category(101, subcategories=[_Category(-1, cut_pattern_id=102)])
            ],
            elements_by_class={
                LINE_PATTERN_ELEMENT: [_line_pattern(x) for x in (101, 102, 103, -5)]
            },
        )
        candidates = self._collect(self.probe._collect_line_patterns, doc)
        self.assertEqual([x.element_id for x in candidates], [103])

    def test_patterns_in_view_category_overrides_are_not_candidates(self):
        """Exclude line and fill patterns used by view category overrides."""
        view = _View(
            category_overrides={
                1: _overrides(ProjectionLinePatternId=101),
                2: _overrides(
                    SurfaceForegroundPatternId=301, CutBackgroundPatternId=302
                ),
            }
        )
        doc = _collector_doc(
            categories=[
                _Category(
                    -1, category_id=1, subcategories=[_Category(-1, category_id=2)]
                )
            ],
            elements_by_class={
                LINE_PATTERN_ELEMENT: [_line_pattern(x) for x in (101, 102)],
                FILL_PATTERN_ELEMENT: [_fill_pattern(x) for x in (301, 302, 303)],
                VIEW: [view],
            },
        )
        lines = self._collect(self.probe._collect_line_patterns, doc)
        fills = self._collect(self.probe._collect_fill_patterns, doc)
        self.assertEqual([x.element_id for x in lines], [102])
        self.assertEqual([x.element_id for x in fills], [303])

    def test_patterns_in_view_filter_overrides_are_not_candidates(self):
        """Exclude line and fill patterns used by view filter overrides."""
        template = _View(
            filter_overrides={
                900: _overrides(CutLinePatternId=101, CutForegroundPatternId=301)
            }
        )
        doc = _collector_doc(
            elements_by_class={
                LINE_PATTERN_ELEMENT: [_line_pattern(x) for x in (101, 102)],
                FILL_PATTERN_ELEMENT: [_fill_pattern(x) for x in (301, 302)],
                VIEW: [template],
            },
        )
        lines = self._collect(self.probe._collect_line_patterns, doc)
        fills = self._collect(self.probe._collect_fill_patterns, doc)
        self.assertEqual([x.element_id for x in lines], [102])
        self.assertEqual([x.element_id for x in fills], [302])

    def test_patterns_in_overrides_of_categories_missing_from_settings_are_not_candidates(
        self,
    ):
        """Scan overrides of categories such as Internal Origin."""
        settings_category = _Category(-1, category_id=1)
        internal_origin = _Category(-1, category_id=-2000500)
        view = _View(
            category_overrides={
                -2000500: _overrides(
                    ProjectionLinePatternId=101, SurfaceForegroundPatternId=301
                ),
            }
        )
        doc = _collector_doc(
            categories=[settings_category],
            builtin_categories={-2000500: internal_origin, -2000501: settings_category},
            elements_by_class={
                LINE_PATTERN_ELEMENT: [_line_pattern(x) for x in (101, 102)],
                FILL_PATTERN_ELEMENT: [_fill_pattern(x) for x in (301, 302)],
                VIEW: [view],
            },
        )
        lines = self._collect(self.probe._collect_line_patterns, doc)
        fills = self._collect(self.probe._collect_fill_patterns, doc)
        self.assertEqual([x.element_id for x in lines], [102])
        self.assertEqual([x.element_id for x in fills], [302])

    def test_categories_found_twice_are_checked_once(self):
        """Check a category found by both lookups only once per view."""
        settings_category = _Category(-1, category_id=1)
        doc = _collector_doc(
            categories=[settings_category],
            builtin_categories={-2000501: settings_category},
        )
        category_ids = self.probe._get_overridable_category_ids(doc)
        self.assertEqual(category_ids, [1])

    def test_views_without_overrides_and_unoverridable_categories_are_skipped(self):
        """Skip views and categories Revit refuses to override."""
        doc = _collector_doc(
            categories=[_Category(-1, category_id=1), _Category(-1, category_id=2)],
            elements_by_class={
                LINE_PATTERN_ELEMENT: [_line_pattern(101)],
                VIEW: [
                    _View(overrides_allowed=False),
                    _View(overridable_category_ids={2}),
                ],
            },
        )
        lines = self._collect(self.probe._collect_line_patterns, doc)
        self.assertEqual([x.element_id for x in lines], [101])

    def test_bound_shared_parameters_are_not_candidates(self):
        """Exclude shared parameters bound as project parameters."""
        doc = _collector_doc(
            elements_by_class={
                SHARED_PARAMETER_ELEMENT: [_shared_parameter(x) for x in (201, 202)]
            },
            bound_definitions={"definition-201"},
        )
        candidates = self._collect(self.probe._collect_shared_parameters, doc)
        self.assertEqual([x.element_id for x in candidates], [202])
        self.assertEqual(candidates[0].detail, "guid-202")


class PurgeTests(unittest.TestCase):
    """Check what the real purge reports as purged or failed."""

    @classmethod
    def setUpClass(cls):
        """Load the probe once with the pyrevit and Revit stubs."""
        cls.probe = _load_probe()

    def _candidates(self, *element_ids):
        return [
            self.probe._make_candidate("Fill Patterns", x, "p{}".format(x))
            for x in element_ids
        ]

    def test_refused_delete_is_reported_and_others_are_purged(self):
        """Report a refused delete and still purge the others."""
        doc = _FakeDoc({10: {"raises": True}, 11: {"deleted": [11]}})
        purged, failed = self.probe.purge(doc, self._candidates(10, 11))
        self.assertEqual([x.element_id for x in purged], [11])
        self.assertEqual(
            [(c.element_id, err) for c, err in failed], [(10, "cannot delete")]
        )

    def test_rolled_back_commit_reports_every_item_as_failed(self):
        """Report every item as failed when Revit rolls back the purge."""
        doc = _FakeDoc({10: {"deleted": [10]}, 11: {"deleted": [11], "failures": 1}})
        purged, failed = self.probe.purge(doc, self._candidates(10, 11))
        self.assertEqual(purged, [])
        self.assertEqual(
            [(c.element_id, err) for c, err in failed],
            [(10, self.probe.ROLLED_BACK), (11, self.probe.ROLLED_BACK)],
        )

    def test_line_style_counts_as_purged_once_its_graphics_style_is_gone(self):
        """Confirm a line style is purged through its graphics style."""
        doc = _FakeDoc({5: {"deleted": [5, 6]}, 6: {}})
        candidate = self.probe._make_candidate(
            "Line Styles", 5, "style", companion_ids=[6]
        )
        self.assertEqual(candidate.witness_id, 6)
        self.assertEqual(self.probe.purge(doc, [candidate]), ([candidate], []))


if __name__ == "__main__":
    unittest.main()
