---
name: scheduling
description: Schedules and quantities. Covers creating schedules, adding fields, filters, sorting and grouping, reading schedule contents, placing schedules on sheets, and exporting them. Use it for "make a door schedule", "count windows by type", "export the room schedule" and similar tasks.
---

# Scheduling

Read `revit-scripting` first. Check API names with `lookup_revit_api`.

## Answering a quantity question

A `run_query` over the elements is usually more reliable and faster than building a schedule and reading it back. Build a schedule when the user wants one in the model.

## Creating a schedule

```python
cat_id = DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Doors).Id
schedule = DB.ViewSchedule.CreateSchedule(doc, cat_id)
schedule.Name = "Door Schedule"
definition = schedule.Definition
```

- **Other kinds:** key schedules `DB.ViewSchedule.CreateKeySchedule(doc, cat_id)`, material takeoffs `CreateMaterialTakeoff(doc, cat_id)`, sheet lists `CreateSheetList(doc)`.

## Fields

```python
fields = {}
for sf in definition.GetSchedulableFields():
    fields[sf.GetName(doc)] = sf
mark = definition.AddField(fields["Mark"])
width = definition.AddField(fields["Width"])
```

- **Available fields:** `GetSchedulableFields()` lists what can be scheduled for that category. Pick fields by name.
- **Field ids:** `AddField` returns a `ScheduleField`. Its `FieldId` is what filters and sorting use.
- **Order:** fields appear in the order they are added.
- **Hiding a field:** set `field.IsHidden = True` to keep it for filtering or sorting but not show it.

## Filters, sorting, grouping, totals

```python
definition.AddFilter(DB.ScheduleFilter(level.FieldId, DB.ScheduleFilterType.Equal, "Level 1"))
definition.AddSortGroupField(DB.ScheduleSortGroupField(mark.FieldId))
definition.IsItemized = False        # group identical rows
definition.ShowGrandTotal = True
```

- **Filter values** must match the field's storage type: a string, a double in feet, an int, or an ElementId.
- **Headers and footers:** grouping headers and footers are properties of `ScheduleSortGroupField` (`ShowHeader`, `ShowFooter`).

## Reading schedule contents

```python
table = schedule.GetTableData()
body = table.GetSectionData(DB.SectionType.Body)
rows = []
for r in range(body.NumberOfRows):
    rows.append([schedule.GetCellText(DB.SectionType.Body, r, c) for c in range(body.NumberOfColumns)])
result = rows
```

The first body rows can be column headers, depending on the schedule's settings.

## Placing on a sheet

```python
DB.ScheduleSheetInstance.Create(doc, sheet.Id, schedule.Id, DB.XYZ(x, y, 0))
```

- **Sheet coordinates** are in feet, measured from the sheet origin.

## Exporting

```python
options = DB.ViewScheduleExportOptions()
schedule.Export(folder, "doors.txt", options)
```

- **Output:** a delimited text file. Tell the user where it is.
- **Where to write:** only to folders the user named, or the run's own folder.

## Checking the result

- **Content:** read the schedule back after creating it, and compare the rows with a direct element query.
- **Appearance:** `capture_view(view="Door Schedule")` shows how it looks.
