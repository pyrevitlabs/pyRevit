from pyrevit import revit
from pyrevit import DB
from pyrevit.compat import get_elementid_value_func, get_elementid_from_value_func
from pyrevit.coreutils import math

get_elementid_value = get_elementid_value_func()
get_elementid_from_value = get_elementid_from_value_func()


def is_2d_view(view, only_plan=False):
    """Check if a view is a 2D view (plan, elevation, section)."""

    if isinstance(view, DB.ViewPlan):
        return True

    if only_plan:
        return False

    return view.ViewType in (
        DB.ViewType.Section,
        DB.ViewType.Elevation,
    )


def get_view_range_and_crop(view, doc):
    """Extract view range and crop box information from a 2D view."""
    view_type = view.ViewType

    # For floor, ceiling, ... use view range
    if isinstance(view, DB.ViewPlan):
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
    # https://jeremytammik.github.io/tbc/a/1622_get_crop_box_for_view.html
    provider = DB.ParameterValueProvider(DB.ElementId(DB.BuiltInParameter.ID_PARAM))
    rule = DB.FilterElementIdRule(provider, DB.FilterNumericEquals(), view.Id)
    param_filter = DB.ElementParameterFilter(rule)
    collector = (
        DB.FilteredElementCollector(doc).WherePasses(param_filter).ToElementIds()
    )
    if collector:
        for id in collector:
            if id != view.Id:
                return doc.GetElement(id)


def compute_rotation_angle(section_box, view):
    # 3D box X-axis projected to XY
    bx = section_box.Transform.BasisX
    angle_box = math.atan2(bx.Y, bx.X)

    # View X-axis in world
    vx = view.CropBox.Transform.BasisX
    angle_view = math.atan2(vx.Y, vx.X)

    # rotation needed to align view to box
    return angle_box - angle_view


def align_crop_by_transform(doc, view, section_box):
    """
    Align a plan view to a 3D section box by moving and rotating
    the view's crop element. This rotates plan, so it no longer faces
    Project North.

    Returns:
        bool: True if the crop element was successfully aligned.
    """
    with revit.Transaction("Align 2D View to 3D Section Box - Plan"):
        crop_el = get_crop_element(doc, view)
        if not crop_el:
            return False

        # Get the actual four corners of the section box footprint.
        world_corners = get_section_box_footprint(section_box)

        # The center of the section box footprint in world coordinates.
        sb_centroid = DB.XYZ(
            sum(point.X for point in world_corners) / 4.0,
            sum(point.Y for point in world_corners) / 4.0,
            0,
        )

        # Get the current crop element center.
        crop_box = crop_el.get_BoundingBox(view)
        crop_centroid = DB.XYZ(
            (crop_box.Min.X + crop_box.Max.X) / 2.0,
            (crop_box.Min.Y + crop_box.Max.Y) / 2.0,
            0,
        )

        # Move crop element so its center matches the section box center.
        translation = sb_centroid - crop_centroid

        DB.ElementTransformUtils.MoveElement(
            doc,
            crop_el.Id,
            translation,
        )

        # Rotate crop element around the section box center.
        angle = compute_rotation_angle(
            section_box,
            view,
        )

        axis = DB.Line.CreateBound(
            DB.XYZ(sb_centroid.X, sb_centroid.Y, 0),
            DB.XYZ(sb_centroid.X, sb_centroid.Y, 1),
        )

        DB.ElementTransformUtils.RotateElement(
            doc,
            crop_el.Id,
            axis,
            angle,
        )

        align_crop_by_shape(doc, view, section_box)

    return True


def align_crop_by_shape(doc, view, section_box):
    """
    Align a plan view to a 3D section box by setting the crop region
    to the section box's world-space footprint.

    Returns:
        bool: True if a custom crop shape was successfully applied.
    """
    with revit.Transaction("Align 2D View to 3D Section Box - Shape"):
        world_corners = get_section_box_footprint(section_box)

        crsm = view.GetCropRegionShapeManager()

        if not crsm or not crsm.CanHaveShape:
            # This view does not support custom crop shapes.
            # Preserve the previous fallback behavior.
            view.CropBox = section_box

            apply_plan_viewrange_from_sectionbox(
                doc,
                view,
                section_box,
            )

            return False

        loop = DB.CurveLoop()

        for i in range(4):
            loop.Append(
                DB.Line.CreateBound(
                    world_corners[i],
                    world_corners[(i + 1) % 4],
                )
            )

        crsm.SetCropShape(loop)

        apply_plan_viewrange_from_sectionbox(
            doc,
            view,
            section_box,
        )

    return True


def get_section_box_footprint(section_box):
    """
    Return the four world-space corners of a section box's XY footprint.

    The corners are returned in perimeter order.
    """
    tf = section_box.Transform
    min_pt = section_box.Min
    max_pt = section_box.Max

    local_corners = [
        DB.XYZ(min_pt.X, min_pt.Y, 0),
        DB.XYZ(max_pt.X, min_pt.Y, 0),
        DB.XYZ(max_pt.X, max_pt.Y, 0),
        DB.XYZ(min_pt.X, max_pt.Y, 0),
    ]

    world_corners = [tf.OfPoint(corner) for corner in local_corners]

    # A plan crop shape should be planar.
    z = world_corners[0].Z

    return [DB.XYZ(point.X, point.Y, z) for point in world_corners]


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


def section_box_from_crop(crop_box):
    """Build a section box that reproduces a section/elevation crop.

    SetSectionBox only supports yaw rotation: it expects Transform.BasisZ
    to be world-up (0,0,1), with BasisX/BasisY horizontal. A section or
    elevation view's own CropBox.Transform uses a different convention
    -- BasisY is the vertical "view up" and BasisZ is the horizontal
    view direction -- so copying it straight through gets its vertical
    and horizontal roles swapped by SetSectionBox (the box ends up
    "on its side"). Instead, build a proper yaw-only frame from the
    view's horizontal right vector, and remap Min/Max onto it: the
    view's vertical extent (old local Y) becomes the new local Z, and
    the view's depth extent (old local Z) becomes the new local Y.

    Assumes crop_box.Transform.BasisY is world-up, which holds for any
    normal (non-tilted) Section or Elevation view -- those view types
    are always vertical cutting planes in Revit.
    """
    t = crop_box.Transform
    min_pt = crop_box.Min
    max_pt = crop_box.Max

    up = DB.XYZ.BasisZ
    right = t.BasisX
    forward = up.CrossProduct(right)

    new_transform = DB.Transform.Identity
    new_transform.Origin = t.Origin
    new_transform.BasisX = right
    new_transform.BasisY = forward
    new_transform.BasisZ = up

    new_box = DB.BoundingBoxXYZ()
    new_box.Transform = new_transform
    new_box.Min = DB.XYZ(min_pt.X, -max_pt.Z, min_pt.Y)
    new_box.Max = DB.XYZ(max_pt.X, -min_pt.Z, max_pt.Y)

    return new_box
