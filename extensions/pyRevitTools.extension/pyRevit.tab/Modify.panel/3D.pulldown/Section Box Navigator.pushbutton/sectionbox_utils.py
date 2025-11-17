from pyrevit import DB


def is_2d_view(view):
    """Check if a view is a 2D view (plan, elevation, section)."""
    view_type = view.ViewType
    return view_type in [
        DB.ViewType.FloorPlan,
        DB.ViewType.CeilingPlan,
        DB.ViewType.Section,
        DB.ViewType.Elevation,
    ]


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
