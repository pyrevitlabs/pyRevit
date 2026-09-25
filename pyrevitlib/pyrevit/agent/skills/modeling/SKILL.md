---
name: modeling
description: Building and changing model geometry. Covers levels, walls, floors, roofs (including gable roofs), doors and windows, columns, rooms, and when DirectShape is acceptable. Use it for "model this house", "add walls", "put windows in" and similar tasks.
---

# Modeling

Read `revit-scripting` first. Every API name here can be checked with `lookup_revit_api`.

## Plan before you build

- **Build in steps, one `run_modify` each, with a dry run first:**
  1. levels and grids
  2. walls
  3. floors
  4. openings
  5. roofs
  6. rooms

  A failed or rejected step leaves the earlier steps intact, and each committed step is its own undo entry.
- **Find the types to use first** with a query: `FilteredElementCollector(doc).OfClass(DB.WallType)`, `DB.FloorType`, `DB.RoofType`, and `OfClass(DB.FamilySymbol)` filtered by category for doors and windows. Prefer the project's own types to generic ones.
- **Check the drawing adds up.** Sum the room dimensions along each band and compare them with the overall dimensions. If they conflict, tell the user what doesn't fit and ask which to keep before you build.
- **Coordinates are in feet.** Keep one consistent origin and write positions as named constants. Convert drawing dimensions (feet and inches) carefully.
- **Check after each step** with `capture_view(view="3d")`, plus a plan, before moving on.

## Levels

- **Create:** `DB.Level.Create(doc, elevation_ft)`, then set `level.Name`.
- **Existing levels:** `get_context` lists them.

## Walls

```python
line = DB.Line.CreateBound(DB.XYZ(x1, y1, 0), DB.XYZ(x2, y2, 0))
wall = DB.Wall.Create(doc, line, wall_type.Id, level.Id, height_ft, 0.0, False, False)
```

- **Centerlines:** walls are placed on their location line, usually the centerline. Wall thickness is `wall_type.Width` (in feet).
- **Joins:** end walls exactly on each other's endpoints so Revit joins them.
- **Openings:** leave room for them. An opening wider than its host wall segment fails with `revit_failure` ("can't cut instance").
- **Check enclosure early.** Place rooms right after the walls: a room that reports "not in a properly enclosed region" in `failures`, or spills into its neighbour, shows a gap in the walls.
- **Gable ends and walls under roofs:** walls don't trim to a roof by themselves. Keep the wall at eave height or taller and attach its top to the roof after the roof exists:

  ```python
  wall.AddAttachment(roof.Id, DB.AttachmentLocation.Top)
  ```

  Don't fill gables with DirectShape.

## Floors (Revit 2022 and later)

```python
from System.Collections.Generic import List
loop = DB.CurveLoop()
for a, b in edges:
    loop.Append(DB.Line.CreateBound(a, b))
floor = DB.Floor.Create(doc, List[DB.CurveLoop]([loop]), floor_type.Id, level.Id)
```

- **Loops must be closed:** each line ends where the next begins, and nothing self-intersects.
- **Ids, not objects:** the type and level arguments are ElementIds.
- **Offset from the level:** `floor.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).Set(offset_ft)`.
- **Ceilings** use the same loops: `DB.Ceiling.Create(doc, loops, ceiling_type.Id, level.Id)`. There is no `doc.Create.NewCeiling`.

## Roofs

- **Native roofs first.** They carry the roof type's layers and materials, and stay editable.
- **Footprint roof:** a closed `CurveArray` footprint on the eave outline, including the overhang. `NewFootPrintRoof` has an out parameter that must not be null, and it gives back the `ModelCurve` for each footprint edge. The slope methods take those model curves, not your `Line`s:

  ```python
  import clr
  footprint = DB.CurveArray()
  for a, b in edges:
      footprint.Append(DB.Line.CreateBound(a, b))
  mapping = clr.Reference[DB.ModelCurveArray](DB.ModelCurveArray())
  roof = doc.Create.NewFootPrintRoof(footprint, level, roof_type, mapping)

  ridge_along_x = True
  for model_curve in mapping.Value:
      curve = model_curve.GeometryCurve
      direction = curve.GetEndPoint(1) - curve.GetEndPoint(0)
      runs_along_x = abs(direction.X) > abs(direction.Y)
      is_eave = runs_along_x == ridge_along_x
      roof.set_DefinesSlope(model_curve, is_eave)
      if is_eave:
          roof.set_SlopeAngle(model_curve, 0.5)
  ```

- **Gable roof:** slope the two edges parallel to the ridge (the eaves) only; the gable-end edges keep `DefinesSlope` False. Slope is rise over run: `0.5` is 6:12.
- **Hip roof:** set `DefinesSlope` on all four edges.
- **Shed roof:** set `DefinesSlope` on one edge.
- **Check the orientation.** Compute the expected ridge height (eave height + half the span × slope) and compare it with `roof.get_BoundingBox(None).Max.Z`. A mismatch means the slopes are on the wrong edges.
- **There is no `FootPrintRoof.Create`,** and a footprint can't contain internal ridge lines. Build a cross gable as a second roof.
- **Height:** raise the whole roof with its level offset parameter (`DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM`), and the overhang with the footprint position.

## Doors, windows and other hosted families

```python
symbol = ...  # DB.FamilySymbol of the right category
if not symbol.IsActive:
    symbol.Activate()
    doc.Regenerate()
inst = doc.Create.NewFamilyInstance(DB.XYZ(x, y, 0), symbol, host_wall, level, DB.Structure.StructuralType.NonStructural)
```

- **Activate inside the transaction.** `symbol.Activate()` changes the document, so it fails with `ModificationOutsideTransactionException` before `t.Start()`.
- **Sill height:** set it with the instance's sill height parameter after placement. Use `inspect_elements` to find its name.
- **Placement:** keep openings clear of wall ends and of each other.

## Columns

- **Structural columns** use `DB.Structure.StructuralType.Column`.
- **Architectural columns** use `NonStructural`, with the level as the host.

## Rooms

```python
room = doc.Create.NewRoom(level, DB.UV(x, y))
room.Name = "Kitchen"
```

- **Placement:** the point must be inside an area enclosed by room-bounding walls. `room.Location` is read-only.
- **Tags:** `doc.Create.NewRoomTag(DB.LinkElementId(room.Id), DB.UV(x, y), plan_view.Id)`.

## DirectShape (last resort)

- **Only when native elements can't express the geometry.** It isn't editable, and it doesn't take part in joins, roof attachment or schedules the way native elements do.
- **Create it empty, then set the shape.** There is no `DirectShape.Create`:

  ```python
  from System.Collections.Generic import List
  shape = DB.DirectShape.CreateElement(doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel))
  shape.SetShape(List[DB.GeometryObject]([solid]))
  ```
- **Material:** build the solid with a material, or it will have none:

  ```python
  solid = DB.GeometryCreationUtilities.CreateExtrusionGeometry(loops, direction, distance, DB.SolidOptions(material_id, DB.ElementId.InvalidElementId))
  ```

## Materials and appearance

- **Materials:** `FilteredElementCollector(doc).OfClass(DB.Material)`. Assign them through the element type's compound structure (`wall_type.GetCompoundStructure()`, change a layer's `MaterialId`, then `SetCompoundStructure`), or through material parameters.
