"""Selects elements with no associated tags in current view."""

import sys

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


curview = revit.activeview
if isinstance(curview, DB.ViewSheet):
    forms.alert("You're on a Sheet. Activate a model view please.")
    sys.exit(0)

selected_switch = ''

options = ['Rooms',
           'Areas',
           'Doors',
           'Windows',
           'Equipment',
           'Walls']

selected_switch = \
    forms.CommandSwitchWindow.show(options,
                                   message='Find untagged elements of type:')


selection = revit.get_selection()


if selected_switch == 'Rooms':
    roomtags = DB.FilteredElementCollector(revit.doc, curview.Id)\
                 .OfCategory(DB.BuiltInCategory.OST_RoomTags)\
                 .WhereElementIsNotElementType()\
                 .ToElementIds()

    rooms = DB.FilteredElementCollector(revit.doc, curview.Id)\
              .OfCategory(DB.BuiltInCategory.OST_Rooms)\
              .WhereElementIsNotElementType()\
              .ToElementIds()

    taggedrooms = []
    untaggedrooms = []
    for rtid in roomtags:
        rt = revit.doc.GetElement(rtid)
        if rt.Room is not None:
            taggedrooms.append(rt.Room.Number)

    for rmid in rooms:
        rm = revit.doc.GetElement(rmid)
        if rm.Number not in taggedrooms:
            untaggedrooms.append(rmid)

    if len(untaggedrooms) > 0:
        selection.set_to(untaggedrooms)
    else:
        forms.alert('All rooms have associated tags.')

elif selected_switch == 'Areas':
    areatags = DB.FilteredElementCollector(revit.doc, curview.Id)\
                 .OfCategory(DB.BuiltInCategory.OST_AreaTags)\
                 .WhereElementIsNotElementType()\
                 .ToElementIds()

    areas = DB.FilteredElementCollector(revit.doc, curview.Id)\
              .OfCategory(DB.BuiltInCategory.OST_Areas)\
              .WhereElementIsNotElementType()\
              .ToElementIds()

    taggedareas = []
    untaggedareas = []
    for atid in areatags:
        at = revit.doc.GetElement(atid)
        if at.Area is not None:
            taggedareas.append(at.Area.Id.IntegerValue)

    for areaid in areas:
        area = revit.doc.GetElement(areaid)
        if area.Id.IntegerValue not in taggedareas:
            untaggedareas.append(areaid)

    if len(untaggedareas) > 0:
        selection.set_to(untaggedareas)
    else:
        forms.alert('All areas have associated tags.')

elif selected_switch == 'Doors' \
        or selected_switch == 'Windows' \
        or selected_switch == 'Walls':
    if selected_switch == 'Doors':
        tagcat = DB.BuiltInCategory.OST_DoorTags
        elcat = DB.BuiltInCategory.OST_Doors
        elname = 'doors'
    elif selected_switch == 'Windows':
        tagcat = DB.BuiltInCategory.OST_WindowTags
        elcat = DB.BuiltInCategory.OST_Windows
        elname = 'windows'
    elif selected_switch == 'Walls':
        tagcat = DB.BuiltInCategory.OST_WallTags
        elcat = DB.BuiltInCategory.OST_Walls
        elname = 'Walls'

    elementtags = DB.FilteredElementCollector(revit.doc, curview.Id)\
                    .OfCategory(tagcat)\
                    .WhereElementIsNotElementType()\
                    .ToElementIds()

    elements = DB.FilteredElementCollector(revit.doc, curview.Id)\
                 .OfCategory(elcat)\
                 .WhereElementIsNotElementType()\
                 .ToElementIds()

    tagged_elements = []
    untagged_elements = []
    for eltid in elementtags:
        elt = revit.doc.GetElement(eltid)
        if elt.TaggedLocalElementId != DB.ElementId.InvalidElementId:
            tagged_elements.append(elt.TaggedLocalElementId.IntegerValue)

    for elid in elements:
        el = revit.doc.GetElement(elid)
        try:
            typecomment = el.Symbol.LookupParameter('Type Comments')
            if el.Id.IntegerValue not in tagged_elements \
                    and typecomment \
                    and typecomment.HasValue \
                    and ('auxiliary' not in typecomment.AsString().lower()):
                untagged_elements.append(elid)
        except Exception:
            if el.Id.IntegerValue not in tagged_elements:
                untagged_elements.append(elid)

    if len(untagged_elements) > 0:
        selection.set_to(untagged_elements)
    else:
        forms.alert('All {} have associated tags.'.format(elname))
