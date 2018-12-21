"""Lists all views that the selected elements is visible in."""
from pyrevit import revit, DB


__context__ = 'selection'


selection = revit.get_selection()


cl_views = DB.FilteredElementCollector(revit.doc)
allviews = cl_views.OfCategory(DB.BuiltInCategory.OST_Views)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

views = filter(lambda x: ((x.ViewType != DB.ViewType.DraftingView
                           or x.ViewType != DB.ViewType.ThreeD)
                          and not x.IsTemplate),
               allviews)

viewList = []


for v in views:
    print('Searching {0} of type: {1}'.format(revit.query.get_name(v),
                                              str(v.ViewType).ljust(25)))

    cl_els = DB.FilteredElementCollector(revit.doc, v.Id)\
               .WhereElementIsNotElementType()\
               .ToElementIds()

    print('\tTotal found: {0}'.format(len(cl_els)))

    i = 0
    for elId in selection:
        if elId in cl_els:
            i = + 1
            viewList.append(v)
        print('\t{0} element(s) found.'.format(i))

print('\n\nViews Containing the selected objects:')

for v in viewList:
    print('{0}{1}ID:{2}'.format(revit.query.get_name(v).ljust(45),
                                str(v.ViewType).ljust(25),
                                str(v.Id).ljust(10)))
