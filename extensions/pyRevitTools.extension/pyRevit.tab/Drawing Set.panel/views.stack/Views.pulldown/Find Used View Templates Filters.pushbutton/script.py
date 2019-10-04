"""Lists all view templates and the filters that has been assigned to each."""

from pyrevit import revit, DB
from pyrevit import script


output = script.get_output()
output.set_width(1100)


views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElements()

for v in views:
    if v.IsTemplate:
        print('\nID: {1}\t{0}'.format(revit.query.get_name(v),
                                      str(v.Id).ljust(10)))
        filters = v.GetFilters()
        for fl in filters:
            print('\t\t\tID: {0}\t{1}'.format(fl,
                                              revit.doc.GetElement(fl).Name))
