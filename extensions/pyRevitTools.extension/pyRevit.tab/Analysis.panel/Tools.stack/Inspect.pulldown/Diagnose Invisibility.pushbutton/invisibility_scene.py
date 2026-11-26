# -*- coding: utf-8 -*-
"""3D preview scene for the Diagnose Invisibility report.

Builds a JSON description of the diagnosed elements' geometry together with
the view's clipping context (section box, crop region, view range or cut
planes) for the report page's WebGL viewer.

Invariant:
    All coordinates are model feet relative to the scene ``origin`` so the
    page can upload them as 32-bit floats without visible jitter on models
    far from the internal origin.
"""

from pyrevit import DB
from scene3d.meshing import (
    BOX_EDGES,
    FloatArray,
    IntArray,
    box_corners,
    element_bbox,
    flat,
    relative,
    tessellate_element,
    union_bbox,
    vector,
)

from invisibility_checks import (
    format_length_with_symbol,
    id_value,
    local_extents,
    resolve_view_range_elevation,
    t,
)


MAX_SCENE_VERTICES = 60000
MAX_ELEMENT_VERTICES = 20000
_MIN_PLANE_HALF_SIZE_FT = 10.0


def _wire_box(kind, label, low, high, transform, origin):
    corners = box_corners(low, high, transform)
    segments = []
    for a, b in BOX_EDGES:
        segments.extend((corners[a], corners[b]))
    return {"kind": kind, "label": label, "lines": flat(segments, origin)}


def _quad(kind, label, corners, origin):
    return {"kind": kind, "label": label, "corners": flat(corners, origin)}


def _plane_rect(transform, scene_bbox, clip=None):
    """Return the local XY corners of a plane drawn around the elements.

    The rectangle covers the elements' extents in ``transform`` space with
    generous padding, clamped to ``clip`` (a crop box in the same space) when
    given, so planes stay readable instead of spanning a whole crop region.
    """
    low, high = local_extents(transform, scene_bbox)
    center_x = (low.X + high.X) / 2.0
    center_y = (low.Y + high.Y) / 2.0
    half_x = max((high.X - low.X) * 0.75, _MIN_PLANE_HALF_SIZE_FT)
    half_y = max((high.Y - low.Y) * 0.75, _MIN_PLANE_HALF_SIZE_FT)
    min_x, max_x = center_x - half_x, center_x + half_x
    min_y, max_y = center_y - half_y, center_y + half_y
    if clip is not None:
        clamped = (
            max(min_x, clip.Min.X),
            min(max_x, clip.Max.X),
            max(min_y, clip.Min.Y),
            min(max_y, clip.Max.Y),
        )
        if clamped[0] < clamped[1] and clamped[2] < clamped[3]:
            min_x, max_x, min_y, max_y = clamped
    return ((min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y))


def _plan_overlays(view, scene_bbox, origin):
    """View range planes and crop outline for a plan view.

    Planes are labelled like Revit's View Range dialog: level plus offset.
    """
    doc = view.Document
    overlays = {"planes": [], "boxes": []}
    crop = view.CropBox if view.CropBoxActive else None
    transform = crop.Transform if crop is not None else DB.Transform.Identity
    plane_corners = [
        transform.OfPoint(DB.XYZ(x, y, 0))
        for x, y in _plane_rect(transform, scene_bbox, crop)
    ]
    crop_corners = None
    if crop is not None:
        crop_corners = [
            transform.OfPoint(DB.XYZ(x, y, 0))
            for x, y in (
                (crop.Min.X, crop.Min.Y),
                (crop.Max.X, crop.Min.Y),
                (crop.Max.X, crop.Max.Y),
                (crop.Min.X, crop.Max.Y),
            )
        ]
    try:
        view_range = view.GetViewRange()
    except Exception:
        return overlays
    planes = (
        ("top", DB.PlanViewPlane.TopClipPlane, t("plane_top", "Top")),
        ("cut", DB.PlanViewPlane.CutPlane, t("plane_cut", "Cut plane")),
        ("bottom", DB.PlanViewPlane.BottomClipPlane, t("plane_bottom", "Bottom")),
        ("depth", DB.PlanViewPlane.ViewDepthPlane, t("plane_depth", "View depth")),
    )
    cut_z = None
    for kind, plane, name in planes:
        z = resolve_view_range_elevation(doc, view_range, plane)
        if z is None:
            continue
        if kind == "cut":
            cut_z = z
        level = doc.GetElement(view_range.GetLevelId(plane))
        offset = view_range.GetOffset(plane)
        sign = "+" if offset >= 0 else "-"
        label = "{}: {} {} {}".format(
            name,
            level.Name if level else "?",
            sign,
            format_length_with_symbol(doc, abs(offset)),
        )
        corners = [DB.XYZ(c.X, c.Y, z) for c in plane_corners]
        overlays["planes"].append(_quad(kind, label, corners, origin))
    if crop_corners:
        z = cut_z if cut_z is not None else scene_bbox.Min.Z
        ring = [DB.XYZ(c.X, c.Y, z) for c in crop_corners]
        segments = []
        for index in range(4):
            segments.extend((ring[index], ring[(index + 1) % 4]))
        overlays["boxes"].append(
            {
                "kind": "crop",
                "label": t("overlay_crop", "Crop region"),
                "lines": flat(segments, origin),
            }
        )
    return overlays


def _section_overlays(view, scene_bbox, origin):
    """Cut plane, far clip plane and crop outline of a section or elevation.

    The far plane appears only when far clipping is on. The crop outline
    appears only when the crop region is active: as a box when the far plane
    bounds it, otherwise as a rectangle on the cut plane.
    """
    overlays = {"planes": [], "boxes": []}
    crop = view.CropBox
    transform = crop.Transform
    rect = _plane_rect(transform, scene_bbox, crop)

    def plane_at(z):
        return [transform.OfPoint(DB.XYZ(x, y, z)) for x, y in rect]

    overlays["planes"].append(
        _quad(
            "cut",
            t("plane_section", "Section / elevation plane"),
            plane_at(crop.Max.Z),
            origin,
        )
    )
    far_param = view.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING)
    far_clipped = far_param is not None and far_param.AsInteger() != 0
    if far_clipped:
        overlays["planes"].append(
            _quad(
                "far",
                "{}: {}".format(
                    t("plane_far", "Far clip"),
                    format_length_with_symbol(view.Document, crop.Max.Z - crop.Min.Z),
                ),
                plane_at(crop.Min.Z),
                origin,
            )
        )
    if view.CropBoxActive:
        label = t("overlay_crop", "Crop region")
        if far_clipped:
            overlays["boxes"].append(
                _wire_box("crop", label, crop.Min, crop.Max, transform, origin)
            )
        else:
            ring = [
                transform.OfPoint(DB.XYZ(x, y, crop.Max.Z))
                for x, y in (
                    (crop.Min.X, crop.Min.Y),
                    (crop.Max.X, crop.Min.Y),
                    (crop.Max.X, crop.Max.Y),
                    (crop.Min.X, crop.Max.Y),
                )
            ]
            segments = []
            for index in range(4):
                segments.extend((ring[index], ring[(index + 1) % 4]))
            overlays["boxes"].append(
                {"kind": "crop", "label": label, "lines": flat(segments, origin)}
            )
    return overlays


def _three_d_overlays(view, origin):
    overlays = {"planes": [], "boxes": []}
    if view.IsSectionBoxActive:
        box = view.GetSectionBox()
        overlays["boxes"].append(
            _wire_box(
                "section_box",
                t("overlay_section_box", "Section box"),
                box.Min,
                box.Max,
                box.Transform,
                origin,
            )
        )
    return overlays


def _camera(view, origin):
    camera = {
        "forward": vector(view.ViewDirection.Negate()),
        "up": vector(view.UpDirection),
        "perspective": False,
    }
    if isinstance(view, DB.View3D):
        try:
            orientation = view.GetOrientation()
            camera["forward"] = vector(orientation.ForwardDirection)
            camera["up"] = vector(orientation.UpDirection)
            camera["eye"] = relative(orientation.EyePosition, origin)
            camera["perspective"] = bool(view.IsPerspective)
        except Exception:
            pass
    return camera


def build_scene(view, element_states, label_for):
    """Describe the preview scene for one view.

    Args:
        view (DB.View): the diagnosed view.
        element_states (list[tuple[DB.Element, bool]]): elements and whether
            they are visible in the view.
        label_for (callable): element -> display label.

    Returns:
        (dict | None): scene description, or None when no element has
        extents. Elements over the per-element vertex budget, or past the
        scene budget, are drawn as their bounding box with ``approx`` set.
    """
    boxes = [
        (element, visible, element_bbox(element)) for element, visible in element_states
    ]
    scene_bbox = union_bbox([b for _, _, b in boxes])
    if scene_bbox is None:
        return None
    origin = (scene_bbox.Min + scene_bbox.Max) * 0.5

    meshes = []
    remaining = MAX_SCENE_VERTICES
    for element, visible, bbox in boxes:
        if bbox is None:
            continue
        builder, approx = tessellate_element(
            element, bbox, origin, min(MAX_ELEMENT_VERTICES, remaining)
        )
        remaining = max(remaining - builder.point_count, 0)
        meshes.append(
            {
                "id": id_value(element.Id),
                "label": label_for(element),
                "visible": visible,
                "approx": approx,
                "positions": FloatArray(builder.positions),
                "indices": IntArray(builder.indices),
                "edges": FloatArray(builder.edges),
            }
        )

    if isinstance(view, DB.ViewPlan):
        overlays = _plan_overlays(view, scene_bbox, origin)
    elif isinstance(view, DB.ViewSection):
        overlays = _section_overlays(view, scene_bbox, origin)
    elif isinstance(view, DB.View3D):
        overlays = _three_d_overlays(view, origin)
    else:
        overlays = {"planes": [], "boxes": []}

    return {
        "viewId": id_value(view.Id),
        "origin": vector(origin),
        "bounds": {
            "min": relative(scene_bbox.Min, origin),
            "max": relative(scene_bbox.Max, origin),
        },
        "camera": _camera(view, origin),
        "meshes": meshes,
        "planes": overlays["planes"],
        "boxes": overlays["boxes"],
    }
