# -*- coding: utf-8 -*-
"""Which elements the 3D preview streams, and at which detail level.

The preview follows the detail level, phase, phase filter and design options of
the view it shows. Visibility/Graphics, view filters and hidden elements are
deliberately not applied, so the box can be dragged over geometry the view
hides.

Note:
    The choices on a view's Visibility/Graphics "Design Options" tab cannot be
    read through the API. Such a set shows its primary option, unless the view
    is dedicated to an option ("Visible In Option") or an option of the set is
    being edited.
"""

from pyrevit import DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.framework import List

get_elementid_value = get_elementid_value_func()

PHASE_STATUS_NAMES = ("Existing", "Demolished", "New", "Temporary")
UNPHASED_STATUS_NAME = "None"
_ACTIVE_RANK = 3
_VIEW_RANK = 2
_PRIMARY_RANK = 1


def choose_shown_options(options, active_id=None, view_option_id=None):
    """Return the design option shown for each option set.

    Args:
        options (iterable[tuple]): ``(option_id, set_id, is_primary)``.
        active_id: the option being edited, which wins within its set.
        view_option_id: the option the view is dedicated to, which wins over
            the primary of its set.

    Returns:
        list: one option id per set, sorted.
    """
    chosen = {}
    for option_id, set_id, is_primary in options:
        if option_id == active_id:
            rank = _ACTIVE_RANK
        elif option_id == view_option_id:
            rank = _VIEW_RANK
        elif is_primary:
            rank = _PRIMARY_RANK
        else:
            continue
        if rank > chosen.get(set_id, (0, None))[0]:
            chosen[set_id] = (rank, option_id)
    return sorted(option_id for _, option_id in chosen.values())


def _id_value(element_id):
    if element_id is None or element_id == DB.ElementId.InvalidElementId:
        return None
    return int(get_elementid_value(element_id))


def _parameter_element_id(view, parameter):
    found = view.get_Parameter(parameter)
    return found.AsElementId() if found is not None else None


def _shown_phase_statuses(phase_filter):
    return tuple(
        name
        for name in PHASE_STATUS_NAMES
        if phase_filter.GetPhaseStatusPresentation(
            getattr(DB.ElementOnPhaseStatus, name)
        )
        != DB.PhaseStatusPresentation.DontShow
    )


def _design_options(doc):
    options = {}
    entries = []
    for option in DB.FilteredElementCollector(doc).OfClass(DB.DesignOption):
        option_id = _id_value(option.Id)
        set_id = _parameter_element_id(option, DB.BuiltInParameter.OPTION_SET_ID)
        options[option_id] = option.Id
        entries.append((option_id, _id_value(set_id), option.IsPrimary))
    return options, entries


class SceneFilter(object):
    """What the preview streams of the host model and of links.

    Linked models are read at the same detail level, show their primary design
    options and are not filtered by phase, which would need the link's phase
    mapping.

    Args:
        phase_id (DB.ElementId | None): the view's phase; None shows all phases,
            as a view whose phase filter is None does.
        statuses (tuple[str]): ``DB.ElementOnPhaseStatus`` names the view's
            phase filter shows. Elements without a phase status always pass.
        active_option (int | None): id value of the option being edited.
        view_option (int | None): id value of the option the view is dedicated to.
        detail_level (DB.ViewDetailLevel | None): level the geometry is read
            at; None and Undefined read at Medium.

    Attributes:
        key (tuple): filters with equal keys stream the same geometry.
    """

    def __init__(
        self,
        phase_id=None,
        statuses=(),
        active_option=None,
        view_option=None,
        detail_level=None,
    ):
        self.phase_id = phase_id
        self.statuses = tuple(statuses)
        self.active_option = active_option
        self.view_option = view_option
        if detail_level is None or detail_level == DB.ViewDetailLevel.Undefined:
            detail_level = DB.ViewDetailLevel.Medium
        self.detail_level = detail_level
        self.key = (
            _id_value(phase_id),
            self.statuses,
            active_option,
            view_option,
            str(detail_level),
        )

    @classmethod
    def for_view(cls, view):
        """Return the filter that follows ``view``, or the default without one."""
        if view is None:
            return cls()
        phase_id = _parameter_element_id(view, DB.BuiltInParameter.VIEW_PHASE)
        filter_id = _parameter_element_id(view, DB.BuiltInParameter.VIEW_PHASE_FILTER)
        statuses = ()
        if _id_value(phase_id) is None or _id_value(filter_id) is None:
            phase_id = None
        else:
            statuses = _shown_phase_statuses(view.Document.GetElement(filter_id))
        view_option = _parameter_element_id(
            view, DB.BuiltInParameter.VIEWER_OPTION_VISIBILITY
        )
        return cls(
            phase_id,
            statuses,
            _id_value(DB.DesignOption.GetActiveDesignOptionId(view.Document)),
            _id_value(view_option),
            view.DetailLevel,
        )

    def apply(self, collector, doc, host):
        """Narrow ``collector`` over ``doc``; ``host`` is False for linked models."""
        options, entries = _design_options(doc)
        if entries:
            shown = choose_shown_options(
                entries,
                self.active_option if host else None,
                self.view_option if host else None,
            )
            filters = List[DB.ElementFilter]()
            filters.Add(DB.ElementDesignOptionFilter(DB.ElementId.InvalidElementId))
            for option_id in shown:
                filters.Add(DB.ElementDesignOptionFilter(options[option_id]))
            collector = collector.WherePasses(DB.LogicalOrFilter(filters))
        if host and self.phase_id is not None:
            statuses = List[DB.ElementOnPhaseStatus]()
            for name in self.statuses + (UNPHASED_STATUS_NAME,):
                statuses.Add(getattr(DB.ElementOnPhaseStatus, name))
            collector = collector.WherePasses(
                DB.ElementPhaseStatusFilter(self.phase_id, statuses)
            )
        return collector
