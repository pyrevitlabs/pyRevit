---
name: modeling
description: Building and changing model geometry. Covers levels, walls, floors, ceilings, roofs (gable, hip, shed), doors and windows, columns, rooms, re-runnable build stages, and when DirectShape is acceptable. Use it for "model this house", "add walls", "put windows in" and similar tasks.
---

# Modeling

Read `revit-scripting` first. Use the `kit` helpers below: each one is a tested recipe for a step agents often get wrong, and each raises a `KitError` that says what to fix. Fall back to the raw API only for what `kit` doesn't cover.

## Plan before you build

- **Check the drawing adds up.** Sum the room dimensions along each band and compare them with the overall dimensions. If they conflict, tell the user what doesn't fit and ask which to keep before you build.
- **Find the types first** with one query:

  ```python
  result = {
      "walls": kit.type_names(DB.WallType),
      "floors": kit.type_names(DB.FloorType),
      "roofs": kit.type_names(DB.RoofType),
      "doors": kit.symbols(category="OST_Doors"),
      "windows": kit.symbols(category="OST_Windows"),
      "levels": [(l.Name, l.Elevation) for l in kit.levels()],
  }
  ```

  Names differ between templates; use the names this returns, never names from memory.
- **Keep plan data in one file in the workspace** (dimensions, wall lines, openings, rooms) and load it in each script with `plan = kit.load(r"C:\path\house_plan.py")`. It is read fresh on every run and sees `doc`, `DB` and `kit`. Don't paste the same helpers into every script.
- **Coordinates are in feet**, with one origin. Convert drawing dimensions with `kit.ft("32'-6\"")` or `kit.ft("900mm")`.

## Build in stages

One `run_modify` per stage, dry run first:

1. levels
2. walls
3. rooms (they check the walls: see below)
4. floors and ceilings
5. openings
6. roofs, then attach the walls to them

Make each stage re-runnable: clear what it made last time, then tag what it makes now.

```python
with kit.transaction("Stage 2 - walls"):
    kit.clear("walls")
    made = kit.walls(kit.rect(0, 0, 65, 32), "Generic - 8\"", level="Level 1", height=9)
    kit.mark(made, "walls")
result = {"walls": len(made)}
```

A failed or rejected stage leaves the earlier ones intact, and each committed stage is one undo entry.

**Check after each stage** with `capture_view(view="3d")`, or `capture_view(view="3d", elements=[...])` to frame part of the model, plus a plan.

## Levels

- **Create:** `DB.Level.Create(doc, elevation_ft)`, then set `level.Name`.
- **Look up:** `kit.level("Level 1")`, or `kit.level()` for the active plan's level.

## Walls

- `kit.wall(start, end, wall_type, level=None, height=10, top_level=None, base_offset=0)` places one wall on its location line (usually the centerline).
- `kit.walls(points, wall_type, ...)` walls a closed outline; pass `closed=False` for an open run.
- **Joins:** end walls exactly on each other's endpoints so Revit joins them. Wall thickness is `wall_type.Width` (feet).
- **Openings:** leave room for them. An opening wider than its host segment fails with `revit_failure` ("can't cut instance").

## Rooms: the layout check

- `kit.room(x, y, name, number=None, level=None)` places a room and **raises when the point isn't enclosed**. Place rooms right after the walls: a raise names the room whose walls have a gap.
- `kit.room_separation(points, level=None)` separates rooms in an open plan without a wall.
- **Tags:** `doc.Create.NewRoomTag(DB.LinkElementId(room.Id), DB.UV(x, y), plan_view.Id)`.

## Floors and ceilings

- `kit.floor(points, floor_type, level=None, offset=0)`: points are the closed outline; `offset` is feet above the level.
- `kit.ceiling(points, ceiling_type, level=None, offset=8)`.

## Roofs

- **Native roofs only.** They carry the roof type's layers and materials, stay editable, and walls can attach to them.
- `kit.gable_roof(x1, y1, x2, y2, roof_type, pitch="8:12", ridge="x", level=None, offset=9)`: the rectangle is the eave outline, overhangs included; `ridge="x"` runs the ridge along X; `offset` is the eave height above the level.
- `kit.hip_roof(...)`, and `kit.shed_roof(..., low_side="south")`.
- `kit.footprint_roof(points, roof_type, level, slopes={0: "8:12", 2: "8:12"}, offset=9)` for any other outline: edge `i` runs from `points[i]` to `points[i+1]`.
- **Pitch** is `"8:12"`, `"30deg"`, or a rise/run number. The raw API `set_SlopeAngle` takes rise over run: not degrees, not radians.
- The gable, hip and shed helpers **measure the built roof and raise** when its rise doesn't match the pitch, which catches slopes on the wrong edges.
- **Cross gables** are a second roof. A footprint can't contain internal ridge lines.
- **Gable end walls:** build the end walls to eave height or taller, then attach them so they follow the rake: `kit.attach_top(end_walls, roof)`. Don't fill gables with DirectShape.

## Doors, windows, columns and other families

- `kit.opening(symbol, wall, x, y, sill=None)` hosts a door or window on `wall` at plan point (x, y). `symbol` is a type name, or pass `kit.symbol("36\" x 84\"", family="Single-Flush")`.
- `kit.place(symbol, x, y, level=None, rotation=0)` places furniture, fixtures and other level-based families.
- `kit.column(symbol, x, y, level, top_level, structural=True)`.
- `kit.symbol` activates the type, so call it inside the transaction.
- Keep openings clear of wall ends and of each other.

## Parameters

- `kit.get(element, "Comments")`, `kit.set(element, "FLOOR_HEIGHTABOVELEVEL_PARAM", 0.5)`. Names can be UI names or `BuiltInParameter` names; a missing name raises with the element's parameter names. Length strings such as `'6"'` are converted.

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

- `FilteredElementCollector(doc).OfClass(DB.Material)`. Assign them through the element type's compound structure (`wall_type.GetCompoundStructure()`, change a layer's `MaterialId`, then `SetCompoundStructure`), or through material parameters.
