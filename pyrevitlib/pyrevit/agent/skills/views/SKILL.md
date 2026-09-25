---
name: views
description: Creating, framing and navigating views. Covers finding views, new plans, 3D views, sections and elevations, section boxes and crops, hiding categories, view templates, opening a view and zooming, and taking a picture of the result. Use it for "make a 3D view of the house", "cut a section through the stair", "show me the kitchen", "open the level 2 plan" and similar tasks.
---

# Views

Read `revit-scripting` first. Use the `kit` helpers below; they are tested recipes and raise a `KitError` that says what to fix.

## Which tool

| Goal | Use | Approval |
|---|---|---|
| See the model or a view as a picture | `capture_view` | none |
| Select, zoom to, or temporarily isolate elements in the active view | `show_elements` | none |
| Open a view, zoom it | `kit.open`, `kit.zoom_to` in `run_query` | none |
| Create a view, or change its settings permanently | `kit` view helpers in `run_modify` | yes, under policy ask |

Don't create a view only to look at something: `capture_view(view="3d", elements=[...], direction="southwest")` renders a temporary 3D view of model categories, framed on those elements, and leaves nothing behind.

## Finding views

- `kit.views(kind=None, name_contains=None)` lists views as `{id, name, type, level}`. Kinds: plan, ceiling, structural, area, 3d, section, elevation, detail, drafting, legend, schedule, sheet. Always filter; projects have hundreds of views.
- `kit.view("Level 1")` finds one by name or id, and raises with similar names when it's missing.

## Creating views

Run these in `run_modify`, inside `with kit.transaction("..."):`. Names are made unique automatically (`"Name (2)"`).

- **Plan:** `kit.plan(level="Level 1", name="L1 - Furniture", kind="plan")`. Kinds: plan, ceiling, structural.
- **3D:** `kit.view3d(name="House 3D", direction="southeast", elements=None, model_only=True)`.
  - `direction`: southeast, southwest, northeast, northwest, south, north, east, west, top.
  - `elements` frames the section box on those elements; the default frames the whole model.
  - `model_only` hides levels, grids and annotations. Leave it on: level and grid extents otherwise ruin the framing.
- **Section:** `kit.section(start, end, name=None, bottom=None, top=None, depth=10)`. It looks to the left of start → end: a line drawn west to east looks north. `depth` is the far clip in feet.
- **Elevation:** `kit.elevation(side="south", name=None)` looks at the whole model from that side (south, north, east, west).
- **Template:** pass `template="..."` to any of these, or call `kit.apply_template(view, "name")`. Prefer the project's templates to setting graphics by hand.

## Framing and visibility

- `kit.section_box(view3d, elements=None, padding=2)` fits a 3D view's section box.
- `kit.orient(view3d, "northwest")`, or `kit.look_at(view3d, eye=(x, y, z), target=(x, y, z))` for a specific camera.
- `kit.crop_to(view, elements=None, padding=3)` crops a plan, section or elevation to elements.
- `kit.model_only(view)` hides every non-model category.
- `kit.hide(view, categories=["OST_Furniture"], elements=[...])` hides permanently. `SetCategoryHidden` takes a category's `Id`, not the Category; the helper handles that.
- Scale and detail: `view.Scale = 50`, `view.DetailLevel = DB.ViewDetailLevel.Fine`, `view.DisplayStyle = DB.DisplayStyle.ShadingWithEdges`.

## Navigating

- `kit.open(view)` asks Revit to make the view active **after the script finishes**. Zoom it in the next call.
- `kit.zoom_to(elements=None)` zooms the active view to elements, or to the whole model. `kit.zoom_fit()` fits everything visible.
- Or use `show_elements(ids, zoom=true)` on the active view.

## Checking the result

- After creating a view, call `capture_view(view="<its name>")`. An empty or tiny image means the crop or section box is wrong, or the view is on the wrong level.
- Don't wrap view changes in `try/except: pass`. When a call fails for every category, the count you report looks like success.

## Raw API, when kit doesn't cover it

- View types come from `DB.ViewFamilyType` filtered by `ViewFamily`.
- `DB.ViewPlan.Create(doc, type_id, level_id)`, `DB.View3D.CreateIsometric(doc, type_id)`, `DB.ViewSection.CreateSection(doc, type_id, box)`.
- `DB.ElevationMarker.CreateElevationMarker(doc, type_id, point, scale)`, then `marker.CreateElevation(doc, plan.Id, index)`. Index 0 to 3 is the direction; check `view.ViewDirection`.
- `view3d.SetOrientation(DB.ViewOrientation3D(eye, up, forward))`. The constructor is public; no reflection needed.
