# -*- coding: utf-8 -*-
"""Filter Legend's Source View -> generated Legend View link.

Thin, tool-specific wrapper around the generic
pyrevit.coreutils.extensible_storage helper (see that module for the
underlying Extensible Storage mechanics). The link is stored on the
*source* view -- not a separate DataStorage element -- since the source
view is always at hand both when saving the link (we just created its
legend) and when reading it (it's the view the user picked again), so
there is nothing to collect/clean up separately.

Only this file needs to change if the Filter Legend tool ever needs to
track additional data alongside the link (e.g. a "last generated"
timestamp): add a field to _FilterLegendLinkSchema.fields and pass it
through save_link().
"""

from pyrevit import DB
from pyrevit.coreutils import extensible_storage


class _FilterLegendLinkSchema(extensible_storage.BaseSchema):
    guid = "f3b1e4d2-7a5c-4b8e-9f3a-1234567890ab"
    schema_name = "pyRevitFilterLegendViewLink"
    vendor_id = "flgd"
    fields = {"LegendViewId": DB.ElementId}


_storage = extensible_storage.ElementDataStorage(_FilterLegendLinkSchema)


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
