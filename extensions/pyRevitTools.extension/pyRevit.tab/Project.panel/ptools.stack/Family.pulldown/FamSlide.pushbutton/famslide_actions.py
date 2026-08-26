# -*- coding: utf-8 -*-
"""Destructive/bulk actions for FamSlide's bottom toolbar."""

import random

from pyrevit import revit, script
from pyrevit.revit import Transaction
from pyrevit import DB

import famslide_paramutils

logger = script.get_logger()


def shuffle_parameter_values(doc, family_manager, rows):
    """Randomize every editable numeric/Yes-No parameter within its
    default slider range. Intentionally does NOT touch formula-driven
    or read-only parameters.

    The range is computed from each parameter's current value at
    shuffle time (same rule the sliders render with), so rows that are
    currently hidden by the editable-only filter still get a range
    consistent with what their slider would show.

    Caller is responsible for confirming with the user first - this
    is destructive and cannot be limited to a subset from here.
    """
    current_type = family_manager.CurrentType
    with Transaction("FamSlide: Shuffle Parameter Values", doc=doc):
        for row in rows:
            if not row.is_editable:
                continue
            if row.group == "yesno":
                family_manager.Set(row.param, int(random.randint(0, 1)))
            elif row.storage_type == DB.StorageType.Double:
                lo, hi = famslide_paramutils.default_range(
                    row, current_type.AsDouble(row.param)
                )
                family_manager.Set(row.param, float(random.uniform(lo, hi)))
            elif row.storage_type == DB.StorageType.Integer:
                lo, hi = famslide_paramutils.default_range(
                    row, current_type.AsInteger(row.param)
                )
                family_manager.Set(row.param, int(random.randint(int(lo), int(hi))))
    revit.uidoc.RefreshActiveView()


def delete_unused_parameters(doc, family_manager, rows):
    """Remove every family parameter flagged as NOT `in_use` (per the
    heuristic in paramutils._scan_in_use) and not driving/driven by a
    formula, since those are much likelier to actually be safe to
    remove. Built-in parameters are never removable via the API and
    are skipped automatically.

    Caller is responsible for confirming with the user first.
    """
    with Transaction("FamSlide: Delete Unused Parameters", doc=doc):
        for row in rows:
            if row.is_builtin:
                continue
            if row.in_use or row.has_formula or row.used_in_formula:
                continue
            if row.is_associated:
                continue
            try:
                family_manager.RemoveParameter(row.param)
            except Exception:
                # keep going - some parameters may be removable-blocked
                # by Revit for reasons not visible from the API
                # (nested family constraints, etc.)
                logger.exception(
                    "FamSlide: could not remove parameter '{}'".format(row.name)
                )
                continue
    revit.uidoc.RefreshActiveView()
