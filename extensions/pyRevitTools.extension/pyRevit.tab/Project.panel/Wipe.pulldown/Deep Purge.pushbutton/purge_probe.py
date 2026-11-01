"""Find definitions nothing in the model depends on, by test-deleting them.

Revit's Purge Unused does not cover line styles, line patterns, fill patterns
or shared parameters, and the API has no "is this used?" query for them.
Instead, each candidate is deleted inside a transaction group that is always
rolled back, and `DocumentChanged` reports what else the deletion touched.
A candidate is unused when the deletion removed only the candidate itself
and changed nothing else.

Some usages raise no `DocumentChanged` entry, so they are excluded up front:
line patterns set in Object Styles and shared parameters bound as project
parameters are never offered.
"""

from collections import namedtuple

from pyrevit import EXEC_PARAMS
from pyrevit import revit, DB
from pyrevit.revit import query, events
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils.logger import get_logger


LINE_STYLES = "Line Styles"
LINE_PATTERNS = "Line Patterns"
FILL_PATTERNS = "Fill Patterns"
SHARED_PARAMETERS = "Shared Parameters"

logger = get_logger(__name__)

get_elementid_value = get_elementid_value_func()


class PurgeCandidate(
    namedtuple(
        "PurgeCandidate",
        ["kind", "element_id", "name", "detail", "own_ids", "witness_id"],
    )
):
    """Something that may be purged.

    `own_ids` holds the element id values that belong to the candidate itself,
    e.g. the graphics styles of a line style. Deleting or changing them is not
    evidence that anything else depends on the candidate.

    `witness_id` is an element that exists exactly as long as the candidate
    does. It differs from `element_id` for line styles, whose subcategory id
    is not an element.
    """

    __slots__ = ()


def _make_candidate(kind, element_id, name, detail="", companion_ids=()):
    own_ids = {get_elementid_value(element_id)}
    own_ids.update(get_elementid_value(x) for x in companion_ids)
    witness_id = companion_ids[0] if companion_ids else element_id
    return PurgeCandidate(
        kind, element_id, name, detail, frozenset(own_ids), witness_id
    )


def _is_user_defined(element_id):
    return get_elementid_value(element_id) > 0


def _collect_line_styles(doc):
    candidates = []
    for subcategory in query.get_line_categories(doc=doc):
        if not _is_user_defined(subcategory.Id):
            continue
        graphics_styles = [
            subcategory.GetGraphicsStyle(style_type)
            for style_type in (
                DB.GraphicsStyleType.Projection,
                DB.GraphicsStyleType.Cut,
            )
        ]
        candidates.append(
            _make_candidate(
                LINE_STYLES,
                subcategory.Id,
                subcategory.Name,
                companion_ids=[x.Id for x in graphics_styles if x],
            )
        )
    return candidates


def _get_object_style_line_pattern_ids(doc):
    pattern_ids = set()
    for category in doc.Settings.Categories:
        for style_category in [category] + list(category.SubCategories):
            for style_type in (
                DB.GraphicsStyleType.Projection,
                DB.GraphicsStyleType.Cut,
            ):
                pattern_ids.add(
                    get_elementid_value(style_category.GetLinePatternId(style_type))
                )
    return pattern_ids


def _collect_line_patterns(doc):
    object_style_pattern_ids = _get_object_style_line_pattern_ids(doc)
    return [
        _make_candidate(LINE_PATTERNS, x.Id, query.get_name(x))
        for x in query.get_elements_by_class(DB.LinePatternElement, doc=doc)
        if _is_user_defined(x.Id)
        and get_elementid_value(x.Id) not in object_style_pattern_ids
    ]


def _collect_fill_patterns(doc):
    candidates = []
    for element in query.get_elements_by_class(DB.FillPatternElement, doc=doc):
        pattern = element.GetFillPattern()
        if pattern.IsSolidFill or not _is_user_defined(element.Id):
            continue
        candidates.append(
            _make_candidate(
                FILL_PATTERNS,
                element.Id,
                query.get_name(element),
                detail=str(pattern.Target),
            )
        )
    return candidates


def _collect_shared_parameters(doc):
    bindings = doc.ParameterBindings
    return [
        _make_candidate(
            SHARED_PARAMETERS,
            x.Id,
            query.get_name(x),
            detail=str(x.GuidValue),
        )
        for x in query.get_elements_by_class(DB.SharedParameterElement, doc=doc)
        if not bindings.Contains(x.GetDefinition())
    ]


COLLECTORS = (
    (LINE_STYLES, _collect_line_styles),
    (LINE_PATTERNS, _collect_line_patterns),
    (FILL_PATTERNS, _collect_fill_patterns),
    (SHARED_PARAMETERS, _collect_shared_parameters),
)


def collect_candidates(doc, kinds=None):
    """Collect purge candidates per kind, in the order of `COLLECTORS`.

    Args:
        doc (DB.Document): document to search.
        kinds (list[str], optional): kinds to collect. Defaults to all.

    Returns:
        (list[tuple[str, list[PurgeCandidate]]]): kind and its candidates,
            sorted by name.
    """
    return [
        (kind, sorted(collector(doc), key=lambda x: x.name.lower()))
        for kind, collector in COLLECTORS
        if kinds is None or kind in kinds
    ]


class PurgeProbeFailureRecorder(DB.IFailuresPreprocessor):
    """Rolls back a transaction on any failure and remembers it did.

    A deletion that raises warnings or errors touches something besides the
    candidate, so it must count as in use, and no dialog may interrupt a run
    over hundreds of candidates.
    """

    __namespace__ = EXEC_PARAMS.exec_id

    def __init__(self):
        self.failed = False

    def PreprocessFailures(self, failuresAccessor):  # noqa: N802, N803
        """Required IFailuresPreprocessor interface method."""
        if failuresAccessor.GetFailureMessages().Count == 0:
            return DB.FailureProcessingResult.Continue
        self.failed = True
        return DB.FailureProcessingResult.ProceedWithRollBack


class _ChangeRecorder(object):
    def __init__(self, doc):
        self._doc = doc
        self.reset()

    def reset(self):
        self.changed = False
        self.deleted = set()
        self.touched = set()

    def record(self, sender, args):  # pylint: disable=unused-argument
        if args.Operation != DB.UndoOperation.TransactionCommitted:
            return
        if not args.GetDocument().Equals(self._doc):
            return
        self.changed = True
        self.deleted.update(get_elementid_value(x) for x in args.GetDeletedElementIds())
        for element_ids in (
            args.GetDeletedElementIds(),
            args.GetModifiedElementIds(),
            args.GetAddedElementIds(),
        ):
            self.touched.update(get_elementid_value(x) for x in element_ids)


def _delete_and_roll_back(doc, candidate, failures):
    with revit.DryTransactionGroup("Deep Purge check", doc=doc):
        with revit.Transaction(
            "Deep Purge check",
            doc=doc,
            clear_after_rollback=True,
            log_errors=False,
            failures_preprocessor=failures,
        ):
            doc.Delete(candidate.element_id)


def _is_unused(doc, candidate, recorder):
    recorder.reset()
    failures = PurgeProbeFailureRecorder()
    try:
        _delete_and_roll_back(doc, candidate, failures)
    except Exception as check_error:  # pylint: disable=broad-except
        logger.debug(
            "Deep Purge check failed for %s %s: %s",
            candidate.kind,
            candidate.name,
            check_error,
        )
        return False
    if failures.failed or not recorder.changed:
        return False
    return (
        get_elementid_value(candidate.element_id) in recorder.deleted
        and recorder.touched <= candidate.own_ids
    )


def find_unused(doc, candidates, progress_bar=None):
    """Return the candidates that can be deleted without affecting anything else.

    Args:
        doc (DB.Document): document the candidates belong to.
        candidates (list[PurgeCandidate]): items to check.
        progress_bar (forms.ProgressBar, optional): updated per candidate;
            checking stops early when it is cancelled.

    Returns:
        (list[PurgeCandidate]): unused candidates, in input order.

    Important:
        Call outside any open transaction or transaction group. Each check
        has to commit for Revit to raise `DocumentChanged`.

    Invariant:
        The document is unchanged afterwards, and the `DocumentChanged`
        handler is removed even when a check raises.
    """
    recorder = _ChangeRecorder(doc)
    handler = events.create_handler(recorder.record, DB.Events.DocumentChangedEventArgs)
    doc.Application.DocumentChanged += handler
    unused = []
    try:
        for index, candidate in enumerate(candidates, 1):
            if progress_bar:
                if progress_bar.cancelled:
                    break
                progress_bar.update_progress(index, len(candidates))
            if _is_unused(doc, candidate, recorder):
                unused.append(candidate)
    finally:
        doc.Application.DocumentChanged -= handler
    return unused


ROLLED_BACK = "Revit rolled back the purge"


def purge(doc, candidates):
    """Delete the candidates in one transaction.

    Returns:
        (tuple[list[PurgeCandidate], list[tuple[PurgeCandidate, str]]]):
            purged candidates, and candidates that failed with the error.

    Invariant:
        A candidate is reported as purged only if it is gone from the
        document after the transaction ends, so a rolled-back commit is
        reported as a failure for every candidate.
    """
    delete_errors = {}
    failures = PurgeProbeFailureRecorder()
    with revit.Transaction("Deep Purge", doc=doc, failures_preprocessor=failures):
        for index, candidate in enumerate(candidates):
            try:
                doc.Delete(candidate.element_id)
            except Exception as delete_error:  # pylint: disable=broad-except
                delete_errors[index] = str(delete_error)
    purged = []
    failed = []
    for index, candidate in enumerate(candidates):
        if index in delete_errors:
            failed.append((candidate, delete_errors[index]))
        elif doc.GetElement(candidate.witness_id) is not None:
            failed.append((candidate, ROLLED_BACK))
        else:
            purged.append(candidate)
    return purged, failed
