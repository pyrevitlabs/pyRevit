"""Isolates specific elements in current view and
put the view in isolate element mode"""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit.framework import List
from pyrevit import forms
from pyrevit import revit, DB

import isolate_config


def get_isolation_elements(selected_switch):
    """Get elements to be isolated, by the selected option"""
    curview = revit.active_view

    if selected_switch == "Room Tags":
        roomtags = (
            DB.FilteredElementCollector(revit.doc, curview.Id)
            .OfCategory(DB.BuiltInCategory.OST_RoomTags)
            .WhereElementIsNotElementType()
            .ToElementIds()
        )

        rooms = (
            DB.FilteredElementCollector(revit.doc, curview.Id)
            .OfCategory(DB.BuiltInCategory.OST_Rooms)
            .WhereElementIsNotElementType()
            .ToElementIds()
        )

        allelements = []
        allelements.extend(rooms)
        allelements.extend(roomtags)
        return List[DB.ElementId](allelements)

    elif selected_switch == "Model Groups":
        elements = (
            DB.FilteredElementCollector(revit.doc, curview.Id)
            .WhereElementIsNotElementType()
            .ToElementIds()
        )
        modelgroups = []
        expanded = []
        for elid in elements:
            el = revit.doc.GetElement(elid)
            if isinstance(el, DB.Group) and not el.ViewSpecific:
                modelgroups.append(elid)
                members = el.GetMemberIds()
                expanded.extend(list(members))
        expanded.extend(modelgroups)
        return List[DB.ElementId](expanded)

    elif selected_switch == "Painted Elements":
        element_to_isolate = List[DB.ElementId]()
        elements = (
            DB.FilteredElementCollector(revit.doc, curview.Id)
            .WhereElementIsNotElementType()
            .ToElementIds()
        )
        for elId in elements:
            el = revit.doc.GetElement(elId)
            if len(list(el.GetMaterialIds(True))) > 0:
                element_to_isolate.Append(elId)
            elif isinstance(el, DB.Wall) and el.IsStackedWall:
                memberWalls = el.GetStackedWallMemberIds()
                for mwid in memberWalls:
                    mw = revit.doc.GetElement(mwid)
                    if len(list(mw.GetMaterialIds(True))) > 0:
                        element_to_isolate.Append(elId)
        return element_to_isolate

    elif selected_switch == "Model Elements":
        element_to_isolate = []

        elements = (
            DB.FilteredElementCollector(revit.doc, curview.Id)
            .WhereElementIsNotElementType()
            .ToElementIds()
        )
        for elid in elements:
            el = revit.doc.GetElement(elid)
            if not el.ViewSpecific:  # and not isinstance(el, DB.Dimension):
                element_to_isolate.append(elid)

        return List[DB.ElementId](element_to_isolate)

    else:
        return (
            DB.FilteredElementCollector(revit.doc, curview.Id)
            .OfCategory(revit.query.get_builtincategory(selected_switch))
            .WhereElementIsNotElementType()
            .ToElementIds()
        )


def ask_for_options():
    """Ask for isolation options and isolate elements"""
    element_cats = isolate_config.load_configs()

    select_options = sorted(x.Name for x in element_cats) + [
        "Room Tags",
        "Model Groups",
        "Painted Elements",
        "Model Elements",
    ]

    selected_switch = forms.CommandSwitchWindow.show(
        select_options, message="Temporarily isolate elements of type:"
    )

    if selected_switch:
        curview = revit.active_view

        with revit.TransactionGroup("Isolate {}".format(selected_switch)):
            with revit.Transaction("Reset temporary hide/isolate"):
                # reset temporary hide/isolate before filtering elements
                curview.DisableTemporaryViewMode(
                    DB.TemporaryViewMode.TemporaryHideIsolate
                )
            element_to_isolate = get_isolation_elements(selected_switch)
            with revit.Transaction("Isolate {}".format(selected_switch)):
                # now that list of elements is ready,
                # let's isolate them in the active view
                curview.IsolateElementsTemporary(element_to_isolate)


if __name__ == "__main__":
    ask_for_options()
