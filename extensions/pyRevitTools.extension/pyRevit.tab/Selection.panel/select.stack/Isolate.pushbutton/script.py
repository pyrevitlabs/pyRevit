"""Isolates specific elements in current view and
put the view in isolate element mode
"""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit.framework import List
from pyrevit import forms
from pyrevit import revit, DB
import isolate_config

__doc__ = "Isolates specific elements in current view and " "put the view in isolate element mode."


def main():
    element_cats = isolate_config.load_configs()

    select_options = sorted(x.Name for x in element_cats) + [
        "Room Tags",
        "Model Groups",
        "Painted Elements",
        "Model Elements",
    ]

    selected_switch = forms.CommandSwitchWindow.show(select_options, message="Temporarily isolate elements of type:")

    if selected_switch:
        curview = revit.active_view

        tg = DB.TransactionGroup(revit.doc, "Isolate {}".format(selected_switch))
        tg.Start()
        # reset temporary hide/isolate before filtering elements
        t1 = DB.Transaction(revit.doc, "Reset temporary hide/isolate")
        t1.Start()
        curview.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)
        t1.Commit()

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
            element_to_isolate = List[DB.ElementId](allelements)

        elif selected_switch == "Model Groups":
            elements = DB.FilteredElementCollector(revit.doc, curview.Id).WhereElementIsNotElementType().ToElementIds()
            modelgroups = []
            expanded = []
            for elid in elements:
                el = revit.doc.GetElement(elid)
                if isinstance(el, DB.Group) and not el.ViewSpecific:
                    modelgroups.append(elid)
                    members = el.GetMemberIds()
                    expanded.extend(list(members))
            expanded.extend(modelgroups)
            element_to_isolate = List[DB.ElementId](expanded)

        elif selected_switch == "Painted Elements":
            element_to_isolate = List[DB.ElementId]()
            elements = DB.FilteredElementCollector(revit.doc, curview.Id).WhereElementIsNotElementType().ToElementIds()
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

        elif selected_switch == "Model Elements":
            element_to_isolate = []

            elements = DB.FilteredElementCollector(revit.doc, curview.Id).WhereElementIsNotElementType().ToElementIds()
            for elid in elements:
                el = revit.doc.GetElement(elid)
                if not el.ViewSpecific:  # and not isinstance(el, DB.Dimension):
                    element_to_isolate.append(elid)

            element_to_isolate = List[DB.ElementId](element_to_isolate)

        else:
            element_to_isolate = (
                DB.FilteredElementCollector(revit.doc, curview.Id)
                .OfCategory(revit.query.get_builtincategory(selected_switch))
                .WhereElementIsNotElementType()
                .ToElementIds()
            )

        # now that list of elements is ready, let's isolate them in the active view
        t2 = DB.Transaction(revit.doc, "Isolate {}".format(selected_switch))
        t2.Start()
        curview.IsolateElementsTemporary(element_to_isolate)
        t2.Commit()
        tg.Assimilate()
        # with revit.Transaction("Isolate {}".format(selected_switch)):
        #     curview.IsolateElementsTemporary(element_to_isolate)


if __name__ == "__main__":
    main()
