---
name: modeling
description: Building and changing model geometry. Covers levels, walls, floors, ceilings, roofs (gable, hip, shed), doors and windows, columns, rooms, re-runnable build stages, and when DirectShape is acceptable. Use it for "model this house", "add walls", "put windows in" and similar tasks.
---

# Modeling

Read `revit-scripting` and `pyrevit-library` first. The functions below are in pyrevitlib; check any of them with `lookup_pyrevit_api`. Fall back to the raw API only for what they don't cover.

```python
from pyrevit import revit
from pyrevit.revit.db import query, create, update
from pyrevit.revit import units
```

## Plan before you build

- **Check the drawing adds up.** Sum the room dimensions along each band and compare them with the overall dimensions. If they conflict, tell the user what doesn't fit and ask which to keep before you build.
- **Find the types first** with one query:

  ```python
  def names(elements):
      return sorted(query.get_name(e) for e in elements)

  result = {
      "walls": names(query.get_types_by_class(DB.WallType)),
      "floors": names(query.get_types_by_class(DB.FloorType)),
      "roofs": names(query.get_types_by_class(DB.RoofType)),
      "doors": sorted("%s : %s" % (s.FamilyName, query.get_name(s)) for s in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_Doors)),
      "levels": [(l.Name, l.Elevation) for l in DB.FilteredElementCollector(doc).OfClass(DB.Level)],
  }
  ```

  Names differ between templates; use the names this returns, never names from memory.
- **Keep plan data in the workspace.** Put dimensions, wall lines, openings and rooms in a module such as `house_plan.py` in a folder, pass that folder as `workspace` to `run_query` and `run_modify`, and `import house_plan`. It is re-imported fresh on every run. Don't paste the same data into every script.
- **Coordinates are in feet**, with one origin. The create functions accept drawing strings (`"32'-6\""`, `"900mm"`); for your own arithmetic, convert with `units.parse_length`.

## Build in stages

One `run_modify` per stage, dry run first:

1. levels
2. walls
3. rooms (they check the walls: see below)
4. floors and ceilings
5. openings
6. roofs, then attach the gable walls to them

Make each stage re-runnable: tag what it makes in Comments, and delete last run's output first.

```python
from pyrevit.revit.db import delete

STAGE = "agent:walls"
with revit.Transaction("Stage 2 - walls"):
    stale = query.get_elements_by_parameter("Comments", STAGE)
    if stale:
        delete.delete_elements(stale)
    walls = create.create_walls(create.rectangle_points(0, 0, 65, 32), "Generic - 8\"", level="Level 1", height=9)
    for wall in walls:
        wall.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(STAGE)
result = {"walls": len(walls)}
```

A failed or rejected stage leaves the earlier ones intact, and each committed stage is one undo entry.

**Check after each stage** with `capture_view(view="3d")`, or `capture_view(view="3d", elements=[...])` to frame part of the model, plus a plan. Read back a number too: a height, an area, a count.

## Levels

- **Create:** `DB.Level.Create(doc, elevation_ft)`, then set `level.Name`.
- **Look up:** `query.find_level("Level 1")`, or `query.find_level()` for the active plan's level.

## Walls

- `create.create_wall(start, end, wall_type, level=None, height=10, top_level=None, base_offset=0)` places one wall on its location line (usually the centerline).
- `create.create_walls(points, wall_type, ...)` walls a closed outline; `closed=False` for an open run. `create.rectangle_points(x1, y1, x2, y2)` gives the corners of a rectangle.
- **Joins:** end walls exactly on each other's endpoints so Revit joins them. Wall thickness is `wall_type.Width` (feet).
- **Openings:** leave room for them. An opening wider than its host segment fails with `revit_failure` ("can't cut instance").

## Rooms: the layout check

- `create.create_room((x, y), level=None, name=None, number=None)` places a room and **raises when the point isn't enclosed**. Place rooms right after the walls: a raise names the room whose walls have a gap.
- `create.create_room_separation_lines(points, level=None)` separates rooms in an open plan without a wall.
- **Tags:** `doc.Create.NewRoomTag(DB.LinkElementId(room.Id), DB.UV(x, y), plan_view.Id)`.

## Floors and ceilings

- `create.create_floor(points, floor_type, level=None, offset=0)`: `points` is the closed outline; `offset` is the height above the level.
- `create.create_ceiling(points, ceiling_type, level=None, offset=8)`.

## Roofs

- **Native roofs only.** They carry the roof type's layers and materials, stay editable, and walls can attach to them.
- `create.create_gable_roof(x1, y1, x2, y2, roof_type, "8:12", ridge="x", level=None, offset=9)`: the rectangle is the eave outline, overhangs included; `ridge="x"` runs the ridge along X; `offset` is the eave height above the level.
- `create.create_hip_roof(...)`, and `create.create_shed_roof(..., low_side="south")`.
- `create.create_footprint_roof(points, roof_type, level, slopes={0: "8:12", 2: "8:12"}, offset=9)` for any other outline: edge `i` runs from `points[i]` to `points[i+1]`.
- **Pitch** is `"8:12"`, `"30deg"`, or a rise/run number. The raw `set_SlopeAngle` takes rise over run: not degrees, not radians.
- The gable, hip and shed functions **measure the built roof and raise** when its rise doesn't match the pitch, which catches slopes on the wrong edges.
- **Cross gables** are a second roof. A footprint can't contain internal ridge lines.
- **Gable end walls:** build them to eave height or taller, then `update.attach_wall_tops(end_walls, roof)` so they follow the rake. Don't fill gables with DirectShape.

## Doors, windows, columns and other families

- `create.place_hosted_instance(symbol, wall, (x, y), sill_height=None)` hosts a door or window on a wall at a plan point on its location line.
- `create.place_family_instance(symbol, (x, y), level=None, rotation=0)` places furniture, fixtures and other level-based families.
- `create.create_column(symbol, (x, y), level, top_level, structural=True)`.
- `symbol` is a `FamilySymbol` or its type name; pass `query.find_family_symbol('36" x 84"', family_name="Single-Flush")` when several families share the type name. These functions activate the type.
- Keep openings clear of wall ends and of each other.

## Parameters

- Read: `query.get_param(element, "Comments")`, then `AsString()`, `AsDouble()` and so on; or rpw: `db.Element(element).parameters["Comments"].value`.
- Write: `element.get_Parameter(DB.BuiltInParameter.X).Set(value)` or `update.update_param_value(param, value)`. Prefer built-in parameters to UI names, which are localized.

## DirectShape (last resort)

- **Only when native elements can't express the geometry.** It isn't editable, and it doesn't take part in joins, roof attachment or schedules.
- Create it empty, then set the shape, with a material or it will have none:

  ```python
  from System.Collections.Generic import List
  options = DB.SolidOptions(material_id, DB.ElementId.InvalidElementId)
  solid = DB.GeometryCreationUtilities.CreateExtrusionGeometry(loops, DB.XYZ.BasisZ, height, options)
  shape = DB.DirectShape.CreateElement(doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
  shape.SetShape(List[DB.GeometryObject]([solid]))
  ```

## Materials

- `query.get_types_by_class(DB.Material)`. Assign them through the element type's compound structure (`wall_type.GetCompoundStructure()`, change a layer's `MaterialId`, then `SetCompoundStructure`), or through material parameters.
