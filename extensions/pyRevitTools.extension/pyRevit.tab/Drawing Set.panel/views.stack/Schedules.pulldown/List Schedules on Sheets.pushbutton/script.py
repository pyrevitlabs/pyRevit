from pyrevit import revit, DB, script

output = script.get_output()
output.close_others()

doc = revit.doc

schedules = [x for x in DB.FilteredElementCollector(doc)
    .OfCategory(DB.BuiltInCategory.OST_Views)
    .WhereElementIsNotElementType()
    .ToElements()
    if x.ViewType == DB.ViewType.Schedule
]

schedules_ids = [x.Id.IntegerValue for x in schedules]

sheets = (
    DB.FilteredElementCollector(doc)
    .OfCategory(DB.BuiltInCategory.OST_Sheets)
    .WhereElementIsNotElementType()
    .ToElements()
)

result = []
for sheet in sheets:
    vps = sheet.GetAllPlacedViews()
    for vp in vps:
        if vp.IntegerValue in schedules_ids:
            result.append(
                (doc.GetElement(vp).Name, sheet.SheetNumber, sheet.Name)
            )

result = sorted(result, key=lambda x: x[0])

output.print_md("## Schedules on Sheets")
headers = ["Schedule Name", "Sheet Number", "Sheet Name"]
output.print_table(result, headers)
