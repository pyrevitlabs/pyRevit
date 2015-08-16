from Autodesk.Revit.DB import *
doc = __revit__.ActiveUIDocument.Document

c = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines )
subcats = c.SubCategories
 
for lineStyle in subcats:
    print("STYLE NAME: {0} ID: {1}".format(lineStyle.Name.ljust(40), lineStyle.Id.ToString() ) )