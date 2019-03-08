"""Lists all views that the selected elements is visible in."""
#pylint: disable=import-error,invalid-name
from pyrevit import revit, DB
from pyrevit import script


__context__ = 'selection'

output = script.get_output()


# collect all model views
cl_views = DB.FilteredElementCollector(revit.doc)
allviews = cl_views.OfCategory(DB.BuiltInCategory.OST_Views)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

views = filter(lambda x: ((x.ViewType != DB.ViewType.DraftingView
                           or x.ViewType != DB.ViewType.ThreeD)
                          and not x.IsTemplate),
               allviews)

# process visible elements in views
view_list = []

for v in views:
    print('Searching {} of type: {}'
          .format(revit.query.get_name(v), str(v.ViewType).ljust(25)))

    # collect view elements
    cl_els = DB.FilteredElementCollector(revit.doc, v.Id)\
               .WhereElementIsNotElementType()\
               .ToElementIds()
    print('\tTotal found: {0}'.format(len(cl_els)))

    i = 0
    for elid in revit.get_selection().element_ids:
        if elid in cl_els:
            i = + 1
            view_list.append(v)
    print('\t{0} matching element(s) found.'.format(i))

output.print_md('## Views Containing the selected objects:')

for view in view_list:
    revit.report.print_view(view)
