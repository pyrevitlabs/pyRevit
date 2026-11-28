# -*- coding: utf-8 -*-
"""Save the selection memory of the active document as a selection filter."""

from pyrevit import forms
from pyrevit import coreutils
from pyrevit import revit, DB, framework

import selectionmemory


def filter_name():
    project_name = revit.query.get_project_info().name
    name_parts = ["SavedSelection", project_name, coreutils.timestamp()]
    return coreutils.cleanup_filename("_".join(part for part in name_parts if part))


def main():
    element_ids = selectionmemory.require_memory_element_ids()
    name = filter_name()
    with revit.Transaction(selectionmemory.text("save_transaction")):
        selection_filter = DB.SelectionFilterElement.Create(revit.doc, name)
        selection_filter.SetElementIds(framework.to_clr_list(DB.ElementId, element_ids))
    if not selection_filter.IsValidObject:
        forms.alert(selectionmemory.text("save_failed"), exitscript=True)
    forms.alert(
        selectionmemory.text("save_done").format(len(element_ids), name),
        warn_icon=False,
    )


if __name__ == "__main__":
    main()
