---
name: drawings
description: Producing drawings and blueprints. Covers sheets with title blocks, viewports, tags, dimensions, text, and PDF export. Use it for "set up sheets", "make a floor plan drawing", "tag all doors", "dimension the walls", "export to PDF" and similar tasks.
---

# Drawings (views, sheets, annotation)

Read `revit-scripting` first. Check API names with `lookup_revit_api`.

## Views

Create, frame and find views with the `views` skill and its `kit` helpers: `kit.plan`, `kit.section`, `kit.elevation`, `kit.view3d`, `kit.crop_to`, `kit.apply_template`.

- **Settings:** `view.Scale` (for example 100 for 1:100), `view.DetailLevel`, `view.CropBoxActive`.
- **Templates:** prefer the project's templates to setting graphics by hand.

## Sheets

```python
titleblock = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_TitleBlocks).WhereElementIsElementType().FirstElement()
sheet = DB.ViewSheet.Create(doc, titleblock.Id)
sheet.SheetNumber = "A101"
sheet.Name = "Floor Plan"
```

- **Helper:** pyRevit has `from pyrevit.revit.db.create import create_sheet`.
- **Title block parameters** such as drawn by and date are parameters on the title block instance on the sheet.

## Viewports

```python
if DB.Viewport.CanAddViewToSheet(doc, sheet.Id, plan.Id):
    DB.Viewport.Create(doc, sheet.Id, plan.Id, DB.XYZ(x, y, 0))
```

- **One sheet per view:** a view can be placed on only one sheet. Duplicate it (`view.Duplicate(DB.ViewDuplicateOption.WithDetailing)`) for another.
- **Position:** the point is the viewport center in sheet coordinates (feet). Read the title block's bounding box on the sheet to fit the viewport inside it.
- **Schedules** are placed with `DB.ScheduleSheetInstance.Create`; see the `scheduling` skill.

## Annotation

Annotation belongs to a view. Pass the plan's id, not the sheet's.

- **Tags:**

  ```python
  DB.IndependentTag.Create(doc, view.Id, DB.Reference(element), False, DB.TagMode.TM_ADDBY_CATEGORY, DB.TagOrientation.Horizontal, point)
  ```

  Tag each element at a point near its location.
- **Room tags:** `doc.Create.NewRoomTag(DB.LinkElementId(room.Id), DB.UV(x, y), view.Id)`.
- **Text:** `DB.TextNote.Create(doc, view.Id, DB.XYZ(x, y, 0), "text", text_type.Id)`, with a type from `OfClass(DB.TextNoteType)`.
- **Dimensions:** `doc.Create.NewDimension(view, line, reference_array)`.
  - `reference_array` is a `DB.ReferenceArray` of references, for example wall faces. Get face references from the wall's geometry with `DB.Options()` and `ComputeReferences = True`, or use `DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Exterior)`.
  - The line gives the dimension's position and direction.

## Exporting to PDF (Revit 2022 and later)

```python
from System.Collections.Generic import List
options = DB.PDFExportOptions()
options.FileName = "Set A"
options.Combine = True
doc.Export(folder, List[DB.ElementId]([sheet.Id for sheet in sheets]), options)
```

- **Where to write:** only to folders the user named. Tell them where the file is.

## Checking the result

- **Every new sheet and view:** use `capture_view(view="A101")`. Look for viewports outside the title block, overlapping tags, and empty views (a view outside its crop box or on the wrong level).
- **Tag and dimension counts:** compare them with the element counts you intended.
