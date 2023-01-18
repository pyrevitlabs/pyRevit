from pyrevit import revit, DB, script

output = script.get_output()
output.close_others()

doc = revit.doc

schedules = DB.FilteredElementCollector(doc).OfClass(
    DB.ScheduleSheetInstance).ToElements()

sheets = DB.FilteredElementCollector(doc).OfCategory(
    DB.BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()


result = []
for schedule in schedules:
    if not schedule.IsTitleblockRevisionSchedule:
        sheet = doc.GetElement(schedule.OwnerViewId)
        result.append(
            (doc.GetElement(schedule.ScheduleId).Name, sheet.SheetNumber, sheet.Name)
        )

result = sorted(result, key=lambda x: x[0])

output.print_md("## Schedules on Sheets")
headers = ["Schedule Name", "Sheet Number", "Sheet Name"]
output.print_table(result, headers)
