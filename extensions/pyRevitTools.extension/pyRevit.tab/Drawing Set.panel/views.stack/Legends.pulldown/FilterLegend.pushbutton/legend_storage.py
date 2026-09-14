# -*- coding: utf-8 -*-
"""Filter Legend's Source View -> generated Legend View link, and
which elements within a generated legend are this tool's own.

Thin, tool-specific wrapper around the generic
pyrevit.coreutils.extensible_storage helper (see that module for the
underlying Extensible Storage mechanics). Two separate schemas, since
they're two separate concerns attached to two different elements:

  * The Source View -> Legend View link lives on the *source* view --
    it's always at hand both when saving the link (we just created its
    legend) and when reading it (it's the view the user picked again),
    so there is nothing to collect/clean up separately.

  * The list of elements a legend owns lives on the *legend* view
    itself, so a future run can delete exactly those elements before
    redrawing -- and leave anything the user added to the legend by
    hand alone.

Only this file needs to change if the Filter Legend tool ever needs to
track additional data (e.g. a "last generated" timestamp): add a field
to the relevant schema class and pass it through the corresponding
save_* function.
"""

from pyrevit import DB
from pyrevit.coreutils import extensible_storage


class _FilterLegendLinkSchema(extensible_storage.BaseSchema):
    guid = "f3b1e4d2-7a5c-4b8e-9f3a-1234567890ab"
    schema_name = "pyRevitFilterLegendViewLink"
    vendor_id = "flgd"
    fields = {"LegendViewId": DB.ElementId}


class _FilterLegendManagedElementsSchema(extensible_storage.BaseSchema):
    guid = "a17c9e4b-2d6f-4a91-8b3d-9e5f6a7b8c0d"
    schema_name = "pyRevitFilterLegendManagedElements"
    vendor_id = "flgd"
    array_fields = {"ManagedElementIds": DB.ElementId}


_storage = extensible_storage.ElementDataStorage(_FilterLegendLinkSchema)
_managed_storage = extensible_storage.ElementDataStorage(
    _FilterLegendManagedElementsSchema
)


def save_link(source_view, legend_view):
    """Save (or overwrite) the link from `source_view` to `legend_view`.

    A view only ever needs to remember its *current* generated legend,
    so any previous link on this view is replaced.

    Args:
        source_view: DB.View the filters were read from
        legend_view: DB.View (Legend) generated for it

    Must be called inside an open transaction.
    """
    _storage.set_data(source_view, LegendViewId=legend_view.Id)


def get_linked_legend(doc, source_view):
    """Look up the legend previously linked to `source_view`, confirming
    it still exists in the model and is a usable Legend view.

    Args:
        doc: DB.Document
        source_view: DB.View to check for an existing link

    Returns:
        DB.View: the linked legend view, or None if there is no link,
            the schema has never been used in this document, or the
            linked element no longer exists / isn't a valid Legend view
            (e.g. it was deleted by the user since the last run)
    """
    data = _storage.get_data(source_view)
    if not data:
        return None

    legend_id = data.get("LegendViewId")
    if legend_id is None or legend_id == DB.ElementId.InvalidElementId:
        return None

    legend_view = doc.GetElement(legend_id)
    if legend_view is None or not legend_view.IsValidObject:
        return None
    if (
        not isinstance(legend_view, DB.View)
        or legend_view.ViewType != DB.ViewType.Legend
    ):
        return None

    return legend_view


def clear_link(source_view):
    """Remove any existing link from `source_view`.

    Not needed for the normal create/update flow (save_link overwrites
    in place), but useful if a caller wants to explicitly unlink a view
    -- e.g. after deleting its legend on purpose.

    Args:
        source_view: DB.View to clear

    Must be called inside an open transaction.
    """
    _storage.clear_data(source_view)


def save_managed_elements(legend_view, element_ids):
    """Record which elements in `legend_view` this tool generated, so a
    future update knows exactly what to delete before redrawing --
    and, just as importantly, what *not* to delete (anything the user
    added to the legend by hand).

    Overwrites any previously recorded list for this legend.

    Args:
        legend_view: DB.View (Legend) that owns the elements
        element_ids: iterable of DB.ElementId generated for this legend

    Must be called inside an open transaction.
    """
    _managed_storage.set_data(legend_view, ManagedElementIds=list(element_ids))


def get_managed_elements(legend_view):
    """Return the element ids previously recorded for `legend_view`.

    Args:
        legend_view: DB.View (Legend) to check

    Returns:
        list of DB.ElementId, or None if nothing has ever been
        recorded for this legend -- e.g. it was linked by a version of
        this tool that predates managed-element tracking. Callers
        should treat None and an empty list differently: None means
        "unknown, fall back to something safer"; an empty list means
        "recorded, and there were none" (a legend whose filters have
        all since been removed from the source view).
    """
    data = _managed_storage.get_data(legend_view)
    if data is None:
        return None
    return data.get("ManagedElementIds")
