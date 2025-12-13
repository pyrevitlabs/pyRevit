from pyrevit import revit, script
from pyrevit.compat import get_elementid_value_func
from pyrevit import DB

get_elementid_value = get_elementid_value_func()


def get_section_box_info(view, datafilename):
    """Get section box information from the current view."""
    if not isinstance(view, DB.View3D):
        return
    if not view.IsSectionBoxActive:
        try:
            view_boxes = script.load_data(datafilename)
        except Exception:
            return None
        view_id_value = get_elementid_value(view.Id)
        bbox_data = view_boxes.get(view_id_value)
        if not bbox_data:
            return None
        section_box = revit.deserialize(bbox_data)
    else:
        section_box = view.GetSectionBox()
    transform = section_box.Transform
    min_point = section_box.Min
    max_point = section_box.Max

    transformed_min = transform.OfPoint(min_point)
    transformed_max = transform.OfPoint(max_point)

    return {
        "box": section_box,
        "transform": transform,
        "min_point": min_point,
        "max_point": max_point,
        "transformed_min": transformed_min,
        "transformed_max": transformed_max,
    }


def get_section_box_face_info(info):
    """
    Get information about the 4 vertical faces of the section box.
    Returns dict with keys: 'north', 'south', 'east', 'west'
    Each containing: center_point, normal, and face identifier
    """
    box = info["box"]
    transform = info["transform"]

    # Get the 8 corners of the box in world coordinates
    min_pt = box.Min
    max_pt = box.Max

    # Calculate face centers in local coordinates, then transform to world
    # For vertical faces, we use the middle Z coordinate
    mid_z = (min_pt.Z + max_pt.Z) / 2.0

    faces = {}

    # Define faces in local coordinate system
    # Each face: center point, outward normal
    local_faces = {
        "north": {
            "center": DB.XYZ((min_pt.X + max_pt.X) / 2.0, max_pt.Y, mid_z),
            "normal": DB.XYZ(0, 1, 0),  # +Y
        },
        "south": {
            "center": DB.XYZ((min_pt.X + max_pt.X) / 2.0, min_pt.Y, mid_z),
            "normal": DB.XYZ(0, -1, 0),  # -Y
        },
        "east": {
            "center": DB.XYZ(max_pt.X, (min_pt.Y + max_pt.Y) / 2.0, mid_z),
            "normal": DB.XYZ(1, 0, 0),  # +X
        },
        "west": {
            "center": DB.XYZ(min_pt.X, (min_pt.Y + max_pt.Y) / 2.0, mid_z),
            "normal": DB.XYZ(-1, 0, 0),  # -X
        },
    }

    # Transform to world coordinates
    for key, face_data in local_faces.items():
        world_center = transform.OfPoint(face_data["center"])
        world_normal = transform.OfVector(face_data["normal"]).Normalize()

        faces[key] = {
            "center": world_center,
            "normal": world_normal,
            "local_center": face_data["center"],
        }

    return faces


def select_best_face_for_direction(faces, direction_vector):
    """
    Select the face whose normal is most parallel to the given direction.

    Args:
        faces: Dict of face info from get_section_box_face_info
        direction_vector: XYZ vector indicating desired direction

    Returns:
        Tuple of (face_key, face_info)
    """
    best_face = None
    best_dot = -1.0

    for key, face_info in faces.items():
        dot = face_info["normal"].DotProduct(direction_vector)
        if dot > best_dot:
            best_dot = dot
            best_face = (key, face_info)

    return best_face


def make_xy_transform_only(crop_transform):
    """Return a transform with only the XY rotation of crop_transform."""
    origin = crop_transform.Origin

    origin_no_z = DB.XYZ(origin.X, origin.Y, 0)

    x_axis = crop_transform.BasisX
    y_axis = crop_transform.BasisY

    # Force them to lie flat in the XY plane (remove any Z component)
    x_axis_flat = DB.XYZ(x_axis.X, x_axis.Y, 0).Normalize()
    y_axis_flat = DB.XYZ(y_axis.X, y_axis.Y, 0).Normalize()

    z_axis_world = DB.XYZ(0, 0, 1)

    t = DB.Transform.Identity
    t.Origin = origin_no_z
    t.BasisX = x_axis_flat
    t.BasisY = y_axis_flat
    t.BasisZ = z_axis_world

    return t
