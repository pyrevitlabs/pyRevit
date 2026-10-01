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

- **Available fields:** `GetSchedulableFields()` lists what can be scheduled for that category. Its display names are localized, so discover them in the active Revit session instead of hardcoding English labels.
- **Field ids:** `AddField` returns a `ScheduleField`. Its `FieldId` is what filters and sorting use.
- **Order:** fields appear in the order they are added.
- **Hiding a field:** set `field.IsHidden = True` to keep it for filtering or sorting but not show it.

## Filters, sorting, grouping, totals

```python
definition.AddFilter(DB.ScheduleFilter(level.FieldId, DB.ScheduleFilterType.Equal, "Level 1"))
definition.AddSortGroupField(DB.ScheduleSortGroupField(mark.FieldId))
definition.IsItemized = False
definition.ShowGrandTotal = True
```

- **Grouping identical rows:** `definition.IsItemized = False` merges rows with the same values; `True` lists every element.

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

Guarded agent runs block schedule exports. Prepare and verify the schedule in a run, then have
the user export it from Revit after the run ends.
- **Where to write:** only to folders the user named, or the run's own folder.

## Before you report done

- [ ] The schedule's rows, read back, match a direct element query of the same category and filters.
- [ ] Its fields, filters, sorting and totals, read back from `schedule.Definition`, are the ones asked for.
- [ ] `capture_view(view="Door Schedule")` shows how it looks.
- [ ] An exported file exists where the user asked, and you told them the path.
