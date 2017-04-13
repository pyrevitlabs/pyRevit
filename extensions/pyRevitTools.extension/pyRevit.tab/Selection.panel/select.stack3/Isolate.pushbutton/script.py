"""Isolates specific elements in current view and put the view in isolate element mode."""

from scriptutils.userinput import CommandSwitchWindow
from revitutils import doc, uidoc, Action

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Group, ElementId, Wall, Dimension
# noinspection PyUnresolvedReferences
from System.Collections.Generic import List


element_cats = {'Area Lines': BuiltInCategory.OST_AreaSchemeLines,
                'Doors': BuiltInCategory.OST_Doors,
                'Room Separation Lines': BuiltInCategory.OST_RoomSeparationLines,
                'Room Tags': None,
                'Model Groups': None,
                'Painted Elements': None,
                'Model Elements': None }

selected_switch = CommandSwitchWindow(sorted(element_cats.keys()),
                                      'Temporarily isolate elements of type:').pick_cmd_switch()


if selected_switch:
    curview = uidoc.ActiveGraphicalView

    if selected_switch == 'Room Tags':
        roomtags = FilteredElementCollector(doc, curview.Id).OfCategory(
            BuiltInCategory.OST_RoomTags).WhereElementIsNotElementType().ToElementIds()
        rooms = FilteredElementCollector(doc, curview.Id).OfCategory(
            BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElementIds()

        allelements = []
        allelements.extend(rooms)
        allelements.extend(roomtags)
        element_to_isolate = List[ElementId](allelements)

    elif selected_switch == 'Model Groups':
        elements = FilteredElementCollector(doc, curview.Id).WhereElementIsNotElementType().ToElementIds()

        modelgroups = []
        expanded = []
        for elid in elements:
            el = doc.GetElement(elid)
            if isinstance(el, Group) and not el.ViewSpecific:
                modelgroups.append(elid)
                members = el.GetMemberIds()
                expanded.extend(list(members))

        expanded.extend(modelgroups)
        element_to_isolate = List[ElementId](expanded)

    elif selected_switch == 'Painted Elements':
        set = []
        elements = FilteredElementCollector(doc, curview.Id).WhereElementIsNotElementType().ToElementIds()
        for elId in elements:
            el = doc.GetElement(elId)
            if len(list(el.GetMaterialIds(True))) > 0:
                set.append(elId)
            elif isinstance(el, Wall) and el.IsStackedWall:
                memberWalls = el.GetStackedWallMemberIds()
                for mwid in memberWalls:
                    mw = doc.GetElement(mwid)
                    if len(list(mw.GetMaterialIds(True))) > 0:
                        set.append(elId)
        element_to_isolate = List[ElementId](set)

    elif selected_switch == 'Model Elements':
        elements = FilteredElementCollector(doc, curview.Id).WhereElementIsNotElementType().ToElementIds()

        element_to_isolate = []
        for elid in elements:
            el = doc.GetElement(elid)
            if not el.ViewSpecific:  #and not isinstance(el, Dimension):
                element_to_isolate.append(elid)

        element_to_isolate = List[ElementId](element_to_isolate)

    else:
        element_to_isolate = FilteredElementCollector(doc, curview.Id) \
                             .OfCategory(element_cats[selected_switch]) \
                             .WhereElementIsNotElementType().ToElementIds()

    # now that list of elements is ready, let's isolate them in the active view
    with Action('Isolate {}'.format(selected_switch)):
        curview.IsolateElementsTemporary(element_to_isolate)
