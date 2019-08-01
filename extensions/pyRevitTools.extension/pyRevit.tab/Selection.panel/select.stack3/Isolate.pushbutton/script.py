from pyrevit.framework import List
from pyrevit import forms
from pyrevit import revit, DB


__doc__ = 'Isolates specific elements in current view and '\
          'put the view in isolate element mode.'

element_cats = {'Area Lines': DB.BuiltInCategory.OST_AreaSchemeLines,
                'Doors': DB.BuiltInCategory.OST_Doors,
                'Room Separation Lines':
                    DB.BuiltInCategory.OST_RoomSeparationLines,
                'Room Tags': None,
                'Model Groups': None,
                'Painted Elements': None,
                'Model Elements': None}


selected_switch = \
    forms.CommandSwitchWindow.show(
        sorted(element_cats.keys()),
        message='Temporarily isolate elements of type:'
        )


if selected_switch:
    curview = revit.active_view

    if selected_switch == 'Room Tags':
        roomtags = DB.FilteredElementCollector(revit.doc, curview.Id)\
                     .OfCategory(DB.BuiltInCategory.OST_RoomTags)\
                     .WhereElementIsNotElementType()\
                     .ToElementIds()

        rooms = DB.FilteredElementCollector(revit.doc, curview.Id)\
                  .OfCategory(DB.BuiltInCategory.OST_Rooms)\
                  .WhereElementIsNotElementType()\
                  .ToElementIds()

        allelements = []
        allelements.extend(rooms)
        allelements.extend(roomtags)
        element_to_isolate = List[DB.ElementId](allelements)

    elif selected_switch == 'Model Groups':
        elements = DB.FilteredElementCollector(revit.doc, curview.Id)\
                     .WhereElementIsNotElementType()\
                     .ToElementIds()

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

    elif selected_switch == 'Painted Elements':
        set = []

        elements = DB.FilteredElementCollector(revit.doc, curview.Id)\
                     .WhereElementIsNotElementType()\
                     .ToElementIds()

        for elId in elements:
            el = revit.doc.GetElement(elId)
            if len(list(el.GetMaterialIds(True))) > 0:
                set.append(elId)
            elif isinstance(el, DB.Wall) and el.IsStackedWall:
                memberWalls = el.GetStackedWallMemberIds()
                for mwid in memberWalls:
                    mw = revit.doc.GetElement(mwid)
                    if len(list(mw.GetMaterialIds(True))) > 0:
                        set.append(elId)
        element_to_isolate = List[DB.ElementId](set)

    elif selected_switch == 'Model Elements':
        elements = DB.FilteredElementCollector(revit.doc, curview.Id)\
                     .WhereElementIsNotElementType()\
                     .ToElementIds()

        element_to_isolate = []
        for elid in elements:
            el = revit.doc.GetElement(elid)
            if not el.ViewSpecific:  # and not isinstance(el, DB.Dimension):
                element_to_isolate.append(elid)

        element_to_isolate = List[DB.ElementId](element_to_isolate)

    else:
        element_to_isolate = \
            DB.FilteredElementCollector(revit.doc, curview.Id)\
              .OfCategory(element_cats[selected_switch]) \
              .WhereElementIsNotElementType()\
              .ToElementIds()

    # now that list of elements is ready, let's isolate them in the active view
    with revit.Transaction('Isolate {}'.format(selected_switch)):
        curview.IsolateElementsTemporary(element_to_isolate)
