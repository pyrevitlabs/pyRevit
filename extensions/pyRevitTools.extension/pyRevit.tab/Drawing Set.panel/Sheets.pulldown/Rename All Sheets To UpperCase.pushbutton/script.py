"""Renames all sheets to UPPERCASE."""

from pyrevit import revit, DB


views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Sheets)\
          .WhereElementIsNotElementType()\
          .ToElements()

sheets = sorted(views, key=lambda x: x.SheetNumber)

with revit.Transaction('Rename Sheets to Upper'):
    for el in sheets:
        sheetnameparam = el.LookupParameter('Sheet Name')
        name = sheetnameparam.AsString()
        name = name.upper()
        print('RENAMING:\t{0}\n'
              '      to:\t{1}\n'.format(name, name.upper()))
        sheetnameparam.Set(name)
