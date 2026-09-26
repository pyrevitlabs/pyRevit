---
name: drawings
description: Producing drawings and blueprints. Covers sheets with title blocks, placing views and schedules on sheets, tags, room tags, dimensions, text, and PDF export. Use it for "set up sheets", "make a floor plan drawing", "tag all doors", "dimension the walls", "export to PDF" and similar tasks.
---

# Drawings (views, sheets, annotation)

Read `revit-scripting` and `pyrevit-library` first. The functions below are in pyrevitlib; check any of them with `lookup_pyrevit_api`.

```python
from pyrevit import revit
from pyrevit.revit.db import query, create, update
```

## Views

Create, frame and find views with the `views` skill: `create.create_plan_view`, `create_section_view`, `create_elevation_view`, `create_model_3d_view`, `update.crop_view_to_elements`.

- **Settings:** `view.Scale` (for example 48 for 1/4" = 1'-0", 100 for 1:100), `view.DetailLevel`, `view.CropBoxActive`.
- **Annotation crop:** `view.get_Parameter(DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE).Set(1)` keeps tags and dimensions inside the crop.
- **Hide what the drawing doesn't need:** `update.hide_categories(view, ["OST_Levels", "OST_Grids", "OST_Elev", "OST_Sections"])`.
- **Templates:** prefer the project's templates to setting graphics by hand.

## Annotation

Annotation belongs to a view. Pass the plan, not the sheet.

- **Dimensions:** `create.create_dimension(view, references, axis="x", position=y)` draws a chain through the references; `axis="x"` measures along X with the line at `Y = position`.
  - Face references: `query.get_face_references(wall, DB.XYZ.BasisX.Negate())[0]` is the wall's outer face looking west. It works for walls, floors and other host elements.
  - Doors and windows: `instance.GetReferences(DB.FamilyInstanceReferenceType.CenterLeftRight)`.
  - Keep dimension chains in lists of (references, axis, position) and build them in one loop; place the lines outside the model with room between chains.
- **Tags:** `create.tag_elements(view, elements, offset=1.8, tag_type=None)` tags by category. `offset` moves each tag along the element's facing direction, so window tags sit outside and door tags (negative offset) inside.
- **Room tags:** `create.create_room_tags(view, rooms=None, tag_type="Room Tag With Area")`; without `rooms` it tags every room visible in the view.
- **Text:** `DB.TextNote.Create(doc, view.Id, DB.XYZ(x, y, 0), "text", text_type.Id)`, with a type from `OfClass(DB.TextNoteType)`.

## Schedules

`create.create_schedule("OST_Rooms", ["Number", "Name", "Level", "Area"], view_name="Room Schedule", sort_by=["Number"], totals=["Area"])`. A field name that doesn't exist raises with the available names. For filters, grouping and formatting, see the `scheduling` skill.

## Sheets

```python
titleblock = query.find_family_symbol("D 22 x 34 Horizontal", family_name="D 22 x 34 Horizontal", category="OST_TitleBlocks")
sheet = create.create_sheet("A101", "Floor Plan", titleblock.Id)
create.place_on_sheet(sheet, plan_view, anchor="top_left")
create.place_on_sheet(sheet, schedule, anchor="top_right")
```

- **Placing:** `create.place_on_sheet(sheet, view_or_schedule, anchor, margin=0.1)` aligns the viewport or schedule to a corner (`top_left`, `top_right`, `bottom_left`, `bottom_right`) or the `center` of the title block. `margin` is in sheet feet (0.1 ft = 1.2 in).
- **One sheet per view:** a view can be placed on only one sheet; `place_on_sheet` raises when it's already on one. Duplicate it (`view.Duplicate(DB.ViewDuplicateOption.WithDetailing)`) for another. Schedules can repeat.
- **Fit:** if the viewport is bigger than the sheet, raise `view.Scale` or tighten the crop.
- **Title block parameters** such as drawn by and date are parameters on the title block instance on the sheet.
- **Re-runnable:** delete the previous sheet, view and schedule by number and name before creating them again.

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
