---
name: views
description: Creating, framing and navigating views. Covers finding views, new plans, 3D views, sections and elevations, section boxes and crops, hiding categories, view templates, opening a view and zooming, and taking a picture of the result. Use it for "make a 3D view of the house", "cut a section through the stair", "show me the kitchen", "open the level 2 plan" and similar tasks.
---

# Views

Read `revit-scripting` and `pyrevit-library` first. The functions below are in pyrevitlib; check any of them with `lookup_pyrevit_api`.

```python
from pyrevit import revit
from pyrevit.revit.db import query, create, update
from pyrevit.revit import ui
```

## Which tool

| Goal | Use | Approval |
|---|---|---|
| See the model or a view as a picture | `capture_view` | none |
| Select, zoom to, or temporarily isolate elements in the active view | `show_elements` | none |
| Open a view, zoom it | `ui.request_view_change`, `ui.zoom_to_elements` in `run_query` | none |
| Create a view, or change its settings permanently | pyrevitlib view functions in `run_modify` | yes, under policy ask |

Don't create a view only to look at something: `capture_view(view="3d", elements=[...], direction="southwest")` renders a temporary 3D view of model categories, framed on those elements, and leaves nothing behind.

## Finding views

- `query.get_all_views(view_types=[DB.ViewType.FloorPlan])` lists views. Filter by type or name; projects have hundreds of views.
- `query.find_view("Level 1")` finds one by name or id, and raises with similar names when it's missing. `query.find_plan_view(level)` finds a floor plan of a level.

## Creating views

Run these in `run_modify`, inside `with revit.Transaction("..."):`. Names are made unique automatically (`"Name (2)"`).

- **Plan:** `create.create_plan_view(level="Level 1", view_name="L1 - Furniture", plan_type="floor")`. Plan types: floor, ceiling, structural.
- **3D:** `create.create_model_3d_view(view_name="House 3D", direction="southeast", elements=None, model_only=True)`.
  - `direction`: southeast, southwest, northeast, northwest, south, north, east, west, top.
  - `elements` frames the section box on those elements; the default frames the whole model.
  - `model_only` hides levels, grids and annotation. Leave it on: level and grid extents otherwise ruin the framing.
- **Section:** `create.create_section_view(start, end, view_name=None, bottom=None, top=None, depth=10)`. It looks to the left of start → end: a line drawn west to east looks north. `depth` is the far clip in feet.
- **Elevation:** `create.create_elevation_view(side="south", view_name=None)` looks at the whole model from that side.
- **Template:** pass `template="<template name>"` to any of these. Prefer the project's templates to setting graphics by hand.
- **Sheets:** `create.create_sheet(...)`; see the `drawings` skill.

## Framing and visibility

- `update.set_section_box(view3d, elements=None, padding=2)` fits a 3D view's section box.
- `update.orient_3d_view(view3d, "northwest")`, or `update.set_3d_view_camera(view3d, eye, target)` with `DB.XYZ` points.
- `update.crop_view_to_elements(view, elements=None, padding=3)` crops a plan, section or elevation to elements; `update.set_crop_region(view, curve_loops)` sets a non-rectangular crop.
- `update.hide_non_model_categories(view)` hides every non-model category.
- `update.hide_categories(view, ["OST_Furniture"])` hides categories permanently; `view.HideElements(ids)` hides elements. `SetCategoryHidden` takes a category's `Id`, not the Category; the function handles that.
- Scale and detail: `view.Scale = 50`, `view.DetailLevel = DB.ViewDetailLevel.Fine`, `view.DisplayStyle = DB.DisplayStyle.ShadingWithEdges`.

## Navigating

- `ui.request_view_change(view)` asks Revit to make the view active **after the script finishes**. Zoom it in the next call. Don't set `revit.active_view` inside an agent run: every run is inside a transaction group, where changing the active view directly can fail.
- `ui.zoom_to_elements(elements)` zooms the active view to elements; `ui.zoom_fit()` fits everything visible.
- Or use `show_elements(ids, zoom=true)` on the active view.

## Checking the result

- After creating a view, call `capture_view(view="<its name>")`. An empty or tiny image means the crop or section box is wrong, or the view is on the wrong level.
- Don't wrap view changes in `try/except: pass`. When a call fails for every category, the count you report looks like success.

## Raw API, when pyrevitlib doesn't cover it

- View types come from `DB.ViewFamilyType` filtered by `ViewFamily`.
- `DB.ViewPlan.Create(doc, type_id, level_id)`, `DB.View3D.CreateIsometric(doc, type_id)`, `DB.ViewSection.CreateSection(doc, type_id, box)`.
- `DB.ElevationMarker.CreateElevationMarker(doc, type_id, point, scale)`, then `marker.CreateElevation(doc, plan.Id, index)`. Index 0 to 3 is the direction; check `view.ViewDirection`.
- `view3d.SetOrientation(DB.ViewOrientation3D(eye, up, forward))`. The constructor is public; no reflection needed.
