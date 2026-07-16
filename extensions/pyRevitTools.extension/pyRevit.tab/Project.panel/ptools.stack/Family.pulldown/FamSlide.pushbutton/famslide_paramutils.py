# -*- coding: utf-8 -*-
"""Parameter discovery, classification, tag computation and default
slider ranges for FamSlide.
"""

from pyrevit import DB
from pyrevit.revit import is_yesno_parameter
from pyrevit.revit import query
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()


class ParamRow(object):
    """One row in the FamSlide UI: wraps a FamilyParameter plus
    everything the UI needs to render and edit it."""

    def __init__(self, family_parameter):
        self.param = family_parameter
        self.name = family_parameter.Definition.Name
        self.storage_type = family_parameter.StorageType
        self.is_instance = family_parameter.IsInstance
        self.is_yesno = is_yesno_parameter(family_parameter.Definition)
        self.is_angle = family_parameter.Definition.GetDataType() == DB.SpecTypeId.Angle
        self.is_builtin = get_elementid_value(family_parameter.Id) < 0
        self.has_formula = bool(getattr(family_parameter, "Formula", None))
        # self.has_formula = family_parameter.IsDeterminedByFormula # whats the difference?
        self.is_readonly = family_parameter.IsReadOnly
        self.locked = False  # filled in by classify_parameters
        self.used_in_formula = False  # filled in by classify_parameters
        self.in_use = False  # filled in by classify_parameters
        self.is_associated = not family_parameter.AssociatedParameters.IsEmpty
        self.group = None  # "value" | "builtin" | "yesno"

    @property
    def is_editable(self):
        """bool: whether the slider/checkbox should be enabled.

        Formula-driven parameters cannot be edited directly in Revit
        (the Family Types dialog greys them out too), so we mirror
        that here.
        """
        return not self.has_formula and not self.is_readonly and not self.locked

    def tags(self):
        """list[str]: stable tag identifiers to render as pills, in a
        stable order.

        These are internal identifiers, not display text - the UI layer
        is responsible for mapping each id to a localized label and a
        color (see script.TAG_COLORS / script.TAG_LABEL_KEYS). Keeping
        the id decoupled from the label means the color lookup keeps
        working regardless of the active locale.
        """
        tags = []
        if self.in_use:
            tags.append("in_use")
        if self.used_in_formula:
            tags.append("used_in_formula")
        if self.has_formula:
            tags.append("has_formula")
        if self.is_builtin:
            tags.append("built_in")
        if self.is_instance:
            tags.append("instance")
        else:
            tags.append("type")
        if self.is_associated:
            tags.append("associated")
        return tags


def _scan_in_use(doc, rows_by_id):
    """Best-effort: mark parameters that label at least one dimension."""
    for param in query.get_family_label_parameters(doc):
        row = rows_by_id.get(get_elementid_value(param.Id))
        if row:
            row.in_use = True


def _scan_used_in_formula(rows):
    """Mark parameters whose *name* appears in another parameter's
    Formula string. Simple substring heuristic - matches how Revit
    itself resolves formula references (by parameter name).
    """
    named_rows = [(r.name, r) for r in rows]
    for row in rows:
        formula = getattr(row.param, "Formula", None)
        if not formula:
            continue
        for other_name, other_row in named_rows:
            if other_row is row:
                continue
            if other_name and other_name in formula:
                other_row.used_in_formula = True


def _scan_locked(family_manager, rows):
    """Mark parameters that are locked in the family.

    Not every FamilyParameter supports locking; Revit may throw
    when IsParameterLocked is queried, so treat those as unlocked.
    """
    for row in rows:
        try:
            row.locked = family_manager.IsParameterLocked(row.param)
        except Exception:
            row.locked = False


def classify_parameters(doc, family_manager):
    """list[ParamRow]: every family parameter, classified and tagged,
    ready for the UI to render.
    """
    rows = [ParamRow(p) for p in family_manager.Parameters]
    rows_by_id = dict((get_elementid_value(r.param.Id), r) for r in rows)

    _scan_in_use(doc, rows_by_id)
    _scan_used_in_formula(rows)
    _scan_locked(family_manager, rows)

    for row in rows:
        if row.is_yesno:
            row.group = "yesno"
        elif row.is_builtin:
            row.group = "builtin"
        else:
            row.group = "value"

    # stable, readable ordering: alphabetic within each group
    rows.sort(key=lambda r: r.name.lower())
    return rows


# ---------------------------------------------------------------------
# Default slider ranges. Hardcoded.
# ---------------------------------------------------------------------

_TWO_PI = 6.283185307179586


def default_range(row, current_value):
    """tuple(float min, float max): a reasonable slider range for a
    Double/Integer family parameter, given its current internal value.
    """
    if row.is_angle:
        return 0.0, _TWO_PI

    if row.storage_type == DB.StorageType.Integer:
        lo, hi = 0, 100
        if current_value is not None and current_value > hi:
            hi = int(current_value * 2)
        return float(lo), float(hi)

    # generic Double (length, area, volume, number, etc.)
    if current_value is None or current_value == 0:
        return 0.0, 10.0
    if current_value > 0:
        return 0.0, current_value * 3.0
    return current_value * 3.0, 0.0
