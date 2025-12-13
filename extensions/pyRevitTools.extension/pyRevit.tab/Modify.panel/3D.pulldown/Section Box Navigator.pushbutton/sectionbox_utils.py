from pyrevit import DB
from pyrevit.compat import get_elementid_value_func, get_elementid_from_value_func
from pyrevit.coreutils import math

get_elementid_value = get_elementid_value_func()
get_elementid_from_value = get_elementid_from_value_func()


def is_2d_view(view, only_plan=False):
    """Check if a view is a 2D view (plan, elevation, section)."""
    view_type = view.ViewType
    if only_plan:
        return view_type in (
            DB.ViewType.FloorPlan,
            DB.ViewType.CeilingPlan,
        )

    return view_type in (
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.Section,
        DB.ViewType.Elevation,
    )


def get_view_range_and_crop(view, doc):
    """Extract view range and crop box information from a 2D view."""
    view_type = view.ViewType

    # For floor/ceiling plans, use view range
    if view_type in [DB.ViewType.FloorPlan, DB.ViewType.CeilingPlan]:
        view_range = view.GetViewRange()
        top_level_id = view_range.GetLevelId(DB.PlanViewPlane.TopClipPlane)
        top_offset = view_range.GetOffset(DB.PlanViewPlane.TopClipPlane)
        bottom_level_id = view_range.GetLevelId(DB.PlanViewPlane.BottomClipPlane)
        bottom_offset = view_range.GetOffset(DB.PlanViewPlane.BottomClipPlane)

        top_level = doc.GetElement(top_level_id)
        bottom_level = doc.GetElement(bottom_level_id)

        top_elevation = top_level.Elevation + top_offset if top_level else None
        bottom_elevation = (
            bottom_level.Elevation + bottom_offset if bottom_level else None
        )

        # Get crop box if active
        crop_box = None
        if view.CropBoxActive:
            crop_box = view.CropBox

        return {
            "top_elevation": top_elevation,
            "bottom_elevation": bottom_elevation,
            "crop_box": crop_box,
            "view": view,
            "is_section": False,
        }

    # For sections and elevations, just use the crop box directly
    elif view_type in [DB.ViewType.Section, DB.ViewType.Elevation]:
        if not view.CropBoxActive:
            return None

        crop_box = view.CropBox

        return {
            "crop_box": crop_box,
            "view": view,
            "is_section": True,
        }

    return None


def get_crop_element(doc, view):
    vid = get_elementid_value(view.Id)
    expected_name = view.get_Parameter(DB.BuiltInParameter.VIEW_NAME).AsString()
    cid = vid + 2
    crop_el = doc.GetElement(get_elementid_from_value(cid))
    if crop_el:
        param = crop_el.get_Parameter(DB.BuiltInParameter.VIEW_NAME)
        if param and param.AsString() == expected_name:
            return crop_el


def compute_rotation_angle(section_box, view):
    # 3D box X-axis projected to XY
    bx = section_box.Transform.BasisX
    angle_box = math.atan2(bx.Y, bx.X)

    # View X-axis in world
    vx = view.CropBox.Transform.BasisX
    angle_view = math.atan2(vx.Y, vx.X)

    # rotation needed to align view to box
    return angle_box - angle_view


def apply_plan_viewrange_from_sectionbox(doc, view, section_box):
    vr = view.GetViewRange()
    if not vr:
        return

    # ---- 1. Collect all level Z coordinates ----
    def lvl_z(plane):
        lvl = doc.GetElement(vr.GetLevelId(plane))
        return lvl.Elevation if lvl else 0.0

    z_bottom_lvl = lvl_z(DB.PlanViewPlane.BottomClipPlane)
    z_cut_lvl = lvl_z(DB.PlanViewPlane.CutPlane)
    z_top_lvl = lvl_z(DB.PlanViewPlane.TopClipPlane)
    z_depth_lvl = lvl_z(DB.PlanViewPlane.ViewDepthPlane)

    # ---- 2. Transform box coords into world space ----
    tf = section_box.Transform
    world_min = tf.OfPoint(section_box.Min)
    world_max = tf.OfPoint(section_box.Max)

    new_bottom_z = world_min.Z
    new_top_z = world_max.Z

    # ---- 3. Compute offsets relative to each plane's level ----
    bottom_offset = new_bottom_z - z_bottom_lvl
    top_offset = new_top_z - z_top_lvl

    # Safe cut plane: middle of range
    cut_z = (new_bottom_z + new_top_z) / 2.0
    cut_offset = cut_z - z_cut_lvl

    # Safe view depth: slightly below bottom
    depth_z = new_bottom_z - 3.0
    depth_offset = depth_z - z_depth_lvl

    # ---- 4. Apply all offsets ----
    vr.SetOffset(DB.PlanViewPlane.BottomClipPlane, bottom_offset)
    vr.SetOffset(DB.PlanViewPlane.CutPlane, cut_offset)
    vr.SetOffset(DB.PlanViewPlane.TopClipPlane, top_offset)
    vr.SetOffset(DB.PlanViewPlane.ViewDepthPlane, depth_offset)

    view.SetViewRange(vr)


def to_world_identity(bbox):
    t = bbox.Transform

    p1 = t.OfPoint(bbox.Min)
    p2 = t.OfPoint(bbox.Max)

    new_box = DB.BoundingBoxXYZ()
    new_box.Transform = DB.Transform.Identity
    new_box.Min = DB.XYZ(min(p1.X, p2.X), min(p1.Y, p2.Y), min(p1.Z, p2.Z))
    new_box.Max = DB.XYZ(max(p1.X, p2.X), max(p1.Y, p2.Y), max(p1.Z, p2.Z))
    return new_box
