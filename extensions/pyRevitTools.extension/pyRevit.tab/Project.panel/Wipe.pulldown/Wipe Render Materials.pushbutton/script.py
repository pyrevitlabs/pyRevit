"""Remove all materials that their names starts with 'Render'."""

from revitutils import doc, selection
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Transaction
from Autodesk.Revit.UI import TaskDialog


with Transaction(doc, 'Remove All Materials') as t:
    t.Start()
    cl = FilteredElementCollector(doc)
    materials = cl.OfCategory(BuiltInCategory.OST_Materials).WhereElementIsNotElementType().ToElements()

    count = 0

    for m in materials:
        if m.Name.startswith('Render'):
            try:
                doc.Delete(m.Id)
                count += 1
            except Exception as e:
                logger.error('Material', m.Id, e)
                continue
    t.Commit()

    TaskDialog.Show('pyRevit', '{} materials removed.'.format(count))
