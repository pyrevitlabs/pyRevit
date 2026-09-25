"""Read-only query: basic execution, output capture and result serialization.

Expected: status ok, decision rolled_back, no changes, result with counts,
element summaries and an XYZ as a list.
"""

walls = (
    DB.FilteredElementCollector(doc)
    .OfClass(DB.Wall)
    .WhereElementIsNotElementType()
    .ToElements()
)
by_type = {}
for wall in walls:
    type_name = wall.WallType.Name
    by_type[type_name] = by_type.get(type_name, 0) + 1

print("found %d walls" % len(walls))

first = walls[0] if len(walls) else None
result = {
    "count": len(walls),
    "by_type": by_type,
    "first_wall": first,
    "first_wall_id": first.Id if first else None,
    "first_wall_midpoint": first.Location.Curve.Evaluate(0.5, True) if first else None,
    "inputs_echo": inputs,
}
