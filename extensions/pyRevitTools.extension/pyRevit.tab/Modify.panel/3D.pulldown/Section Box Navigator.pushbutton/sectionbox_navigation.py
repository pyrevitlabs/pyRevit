import clr
from pyrevit import DB


def get_all_levels(doc):
    """Get all levels sorted by elevation."""
    return sorted(
        list(DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()),
        key=lambda x: x.Elevation,
    )


def get_all_grids(doc):
    """Get all grid lines in the model."""
    return list(
        DB.FilteredElementCollector(doc)
        .OfClass(DB.Grid)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_cardinal_direction(direction_name):
    """
    Get the world direction vector for a cardinal direction.

    Args:
        direction_name: 'north', 'south', 'east', 'west'

    Returns:
        XYZ vector in world coordinates
    """
    # Base vectors in internal coordinates
    internal_vectors = {
        "north": DB.XYZ(0, 1, 0),  # +Y
        "south": DB.XYZ(0, -1, 0),  # -Y
        "east": DB.XYZ(1, 0, 0),  # +X
        "west": DB.XYZ(-1, 0, 0),  # -X
    }

    return internal_vectors[direction_name]


def get_next_level_above(z_coordinate, all_levels, tolerance):
    """Get the next level above the given Z coordinate."""
    for level in all_levels:
        if level.Elevation > z_coordinate + tolerance:
            return level, level.Elevation
    return None, None


def get_next_level_below(z_coordinate, all_levels, tolerance):
    """Get the next level below the given Z coordinate."""
    for level in reversed(all_levels):
        if level.Elevation < z_coordinate - tolerance:
            return level, level.Elevation
    return None, None


def find_next_grid_in_direction(start_point, direction_vector, grids, tolerance):
    """
    Find the next grid line from start_point in the given direction (in XY plane).
    """

    best_grid = None
    best_intersection = None
    min_distance = float("inf")

    # Flatten direction to XY
    direction_vector = DB.XYZ(direction_vector.X, direction_vector.Y, 0).Normalize()
    start_point_flat = DB.XYZ(start_point.X, start_point.Y, 0)

    # Create a 2D ray in XY plane
    ray = DB.Line.CreateUnbound(start_point_flat, direction_vector)

    for grid in grids:
        curve = grid.Curve
        if not isinstance(curve, DB.Line):
            continue

        # Flatten grid line to XY
        p1, p2 = curve.GetEndPoint(0), curve.GetEndPoint(1)
        grid_line = DB.Line.CreateBound(
            DB.XYZ(p1.X, p1.Y, 0),
            DB.XYZ(p2.X, p2.Y, 0)
        )

        # Try intersection
        # weird ironpython stuff - can be changed if cpython ever gets up and running:
        # https://forums.autodesk.com/t5/revit-api-forum/find-intersection-point-between-curves-using-cpython3/td-p/12413340
        result = clr.Reference[DB.IntersectionResultArray]()
        intersection_result = grid_line.Intersect(ray, result)

        if intersection_result != DB.SetComparisonResult.Overlap:
            continue

        if result.Value.Size == 0:
            continue

        intersection = result.Value.Item[0].XYZPoint
        to_intersection = intersection - start_point_flat

        distance_along_ray = to_intersection.DotProduct(direction_vector)
        if distance_along_ray < tolerance:
            continue

        distance = to_intersection.GetLength()
        if distance < min_distance:
            min_distance = distance
            best_grid = grid
            best_intersection = DB.XYZ(intersection.X, intersection.Y, start_point.Z)

    return best_grid, best_intersection
