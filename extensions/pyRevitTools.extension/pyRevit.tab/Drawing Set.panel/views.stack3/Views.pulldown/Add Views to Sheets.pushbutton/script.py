__author__ = 'Dan Mapes'
__doc__ = 'Add Selected View Callout to Selected Sheet \n' \
            'Works with section and plan view callouts! '\
            'Adds the selected callout to the selected sheet. '\
            'Will add view at 0,0,0 point on sheet.'

import Autodesk.Revit.DB as DB
from Autodesk.Revit.DB import Transaction, View, XYZ
from Autodesk.Revit.UI import TaskDialog
from pyrevit import script
from rpw.ui.forms import SelectFromList


doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# selection
selected_ids = uidoc.Selection.GetElementIds()
if selected_ids.Count == 1:
    for element_id in selected_ids:
        element = doc.GetElement(element_id)
        section_name = element.Name
        # section_name = element.GetParameters('View Name')
else:
    TaskDialog.Show('pyMapes', 'Select 1 Section. No more No less')
    script.exit()

sheet_ids = []
sheet_names = []

# Find all views
views = DB.FilteredElementCollector(doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElementIds()
# Find all sheets
sheets = DB.FilteredElementCollector(doc)\
          .OfCategory(DB.BuiltInCategory.OST_Sheets)\
          .WhereElementIsNotElementType()\
          .ToElementIds()

for sheet in sheets:
    s_element = doc.GetElement(sheet)
    sheet_id = s_element.Id
    title = s_element.Name
    sheet_names.append(title)
    sheet_ids.append(sheet_id)

sheet_names_and_ids = zip(sheet_names, sheet_ids)
sheet_names_and_ids_dict = dict(sheet_names_and_ids)

final_location = XYZ(0,0,0)

selected_sheet_value = SelectFromList('Select view to add section view', sheet_names_and_ids_dict.keys())
selected_sheet = sheet_names_and_ids_dict[selected_sheet_value]

t = Transaction(doc, "Add Selected View Callout to Selected Sheet")
t.Start()
for view in views:
    v_element = doc.GetElement(view)
    if v_element.Name == section_name:
        section_id = v_element.Id
        DB.Viewport.Create(doc, selected_sheet, section_id, final_location)
# print section_name, section_id
t.Commit()
