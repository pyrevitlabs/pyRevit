# -*- coding: utf-8 -*-
"""Create a section box or crop box for a view that has none."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit.compat import get_elementid_value_func
from pyrevit.revit import query, update, selection
from sectionbox_geometry import get_crop_edit_blocker

logger = script.get_logger()
get_elementid_value = get_elementid_value_func()

SCOPE_BOX_CATEGORY = DB.BuiltInCategory.OST_VolumeOfInterest
NON_FRAMING_CATEGORY_IDS = (
    int(DB.BuiltInCategory.OST_Cameras),
    int(DB.BuiltInCategory.OST_VolumeOfInterest),
    int(DB.BuiltInCategory.OST_SectionBox),
)
VISIBLE_ELEMENTS_PADDING = 1.0
VISIBLE_ELEMENTS_CROP_PADDING = 3.0
HORIZONTAL_TOLERANCE = 1e-6


def get_scope_boxes(doc):
    """Return all scope boxes of a document."""
    return list(
        DB.FilteredElementCollector(doc)
        .OfCategory(SCOPE_BOX_CATEGORY)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_visible_model_elements(view):
    """Return the model elements visible in a view that can frame a box."""
    return [
        element
        for element in query.get_all_elements_in_view(view)
        if element.Category
        and element.Category.CategoryType == DB.CategoryType.Model
        and get_elementid_value(element.Category.Id) not in NON_FRAMING_CATEGORY_IDS
    ]


def scope_box_to_bounding_box(scope_box):
    """Build the oriented bounding box of a scope box.

    Scope boxes expose only their twelve edges. Their rotation is recovered
    from the first horizontal edge, and the corners are measured in that
    yaw-only frame, which is the frame View3D.SetSectionBox accepts.

    Args:
        scope_box (DB.Element): scope box element.

    Returns:
        DB.BoundingBoxXYZ | None: box with a yaw-only Transform and Min/Max in
            that frame; None when the scope box has no edge geometry.
    """
    edges = [
        edge
        for edge in scope_box.get_Geometry(DB.Options())
        if isinstance(edge, DB.Line)
    ]
    if not edges:
        return None
    corners = [edge.GetEndPoint(index) for edge in edges for index in (0, 1)]
    horizontal_edges = [
        edge for edge in edges if abs(edge.Direction.Z) < HORIZONTAL_TOLERANCE
    ]
    x_axis = horizontal_edges[0].Direction if horizontal_edges else DB.XYZ.BasisX
    y_axis = DB.XYZ.BasisZ.CrossProduct(x_axis)

    origin = DB.XYZ(
        sum(corner.X for corner in corners) / len(corners),
        sum(corner.Y for corner in corners) / len(corners),
        0,
    )
    local_x = [(corner - origin).DotProduct(x_axis) for corner in corners]
    local_y = [(corner - origin).DotProduct(y_axis) for corner in corners]
    world_z = [corner.Z for corner in corners]

    transform = DB.Transform.Identity
    transform.Origin = origin
    transform.BasisX = x_axis
    transform.BasisY = y_axis
    transform.BasisZ = DB.XYZ.BasisZ

    box = DB.BoundingBoxXYZ()
    box.Transform = transform
    box.Min = DB.XYZ(min(local_x), min(local_y), min(world_z))
    box.Max = DB.XYZ(max(local_x), max(local_y), max(world_z))
    return box


def _show_only_scope_boxes(view, category_id):
    entered_modes = []
    with revit.Transaction("Show Scope Boxes"):
        if view.GetCategoryHidden(category_id):
            try:
                view.SetCategoryHidden(category_id, False)
            except Exception as ex:
                logger.warning(
                    "Could not unhide scope boxes, revealing hidden elements: {}".format(
                        ex
                    )
                )
                view.EnableRevealHiddenMode()
                entered_modes.append(DB.TemporaryViewMode.RevealHiddenElements)
        if not view.IsInTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate):
            view.IsolateCategoriesTemporary(List[DB.ElementId]([category_id]))
            entered_modes.append(DB.TemporaryViewMode.TemporaryHideIsolate)
    return entered_modes


def pick_scope_box_on_screen(view, message):
    """Let the user click a scope box while the view shows nothing else.

    The view is put in a temporary isolate of the scope box category and the
    category is made visible if the view hides it. Everything is undone
    afterwards, also when the pick is cancelled: the whole step runs in a
    transaction group that is always rolled back, so the view and the undo
    stack end up as they were. A temporary isolate the user already had active
    is left alone.

    Returns:
        DB.Element | None: picked scope box; None when cancelled.
    """
    category_id = DB.ElementId(SCOPE_BOX_CATEGORY)
    with revit.DryTransactionGroup("Pick Scope Box", doc=view.Document):
        entered_modes = _show_only_scope_boxes(view, category_id)
        try:
            with forms.WarningBar(title=message):
                return revit.pick_element(
                    message,
                    pick_filter=selection.PickByCategorySelectionFilter(category_id),
                )
        finally:
            if entered_modes:
                with revit.Transaction("Restore View"):
                    for mode in entered_modes:
                        view.DisableTemporaryViewMode(mode)


def _get_corners_in_view(view, elements):
    to_view = view.CropBox.Transform.Inverse
    corners = []
    for element in elements:
        bounding_box = element.get_BoundingBox(None)
        if not bounding_box:
            continue
        for x in (bounding_box.Min.X, bounding_box.Max.X):
            for y in (bounding_box.Min.Y, bounding_box.Max.Y):
                for z in (bounding_box.Min.Z, bounding_box.Max.Z):
                    corners.append(to_view.OfPoint(DB.XYZ(x, y, z)))
    return corners


def fit_crop_box_to_elements(view, elements, padding=VISIBLE_ELEMENTS_CROP_PADDING):
    """Fit a view's crop box to elements and turn the crop on.

    Every element's corners are measured in the crop box's own frame before the
    bounds are combined, so a rotated view gets a tight crop instead of one
    around the elements' world-aligned bounds.

    Args:
        view (DB.View): plan, section or elevation view.
        elements (list[DB.Element]): elements to frame.
        padding (float): clearance around the elements in the view plane, in feet.

    Returns:
        bool: False when none of the elements has a bounding box.
    """
    corners = _get_corners_in_view(view, elements)
    if not corners:
        return False
    crop_box = view.CropBox
    crop_box.Min = DB.XYZ(
        min(corner.X for corner in corners) - padding,
        min(corner.Y for corner in corners) - padding,
        crop_box.Min.Z,
    )
    crop_box.Max = DB.XYZ(
        max(corner.X for corner in corners) + padding,
        max(corner.Y for corner in corners) + padding,
        crop_box.Max.Z,
    )
    view.CropBox = crop_box
    view.CropBoxActive = True
    return True


def _create_from_visible_elements(view, get_string):
    elements = get_visible_model_elements(view)
    if not elements:
        forms.alert(get_string("NoVisibleElements"))
        return None
    if not isinstance(view, DB.View3D):
        blocker = get_crop_edit_blocker(view)
        if blocker:
            forms.alert(
                get_string(
                    "CropBoxDrivenByScopeBox"
                    if blocker == "scope_box"
                    else "CropBoxHasCustomShape"
                )
            )
            return None
    with revit.Transaction("Create Box from Visible Elements"):
        if isinstance(view, DB.View3D):
            update.set_section_box(view, elements, padding=VISIBLE_ELEMENTS_PADDING)
        elif not fit_crop_box_to_elements(view, elements):
            forms.alert(get_string("NoVisibleElements"))
            return None
    return get_string("SourceVisibleElements")


def _apply_scope_box(view, scope_box, get_string):
    if isinstance(view, DB.View3D):
        box = scope_box_to_bounding_box(scope_box)
        if not box:
            forms.alert(get_string("ScopeBoxHasNoGeometry"))
            return None
        with revit.Transaction("Create Section Box from Scope Box"):
            view.SetSectionBox(box)
            view.IsSectionBoxActive = True
    else:
        scope_box_param = view.get_Parameter(
            DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP
        )
        if scope_box_param is None or scope_box_param.IsReadOnly:
            forms.alert(get_string("ScopeBoxNotSupported"))
            return None
        with revit.Transaction("Assign Scope Box to View"):
            view.CropBoxActive = True
            scope_box_param.Set(scope_box.Id)
    return scope_box.Name


def _create_from_scope_box_list(view, get_string):
    scope_boxes = get_scope_boxes(view.Document)
    if not scope_boxes:
        forms.alert(get_string("NoScopeBoxes"))
        return None
    choices = {
        "{} ({})".format(scope_box.Name, scope_box.Id): scope_box
        for scope_box in scope_boxes
    }
    chosen = forms.SelectFromList.show(
        sorted(choices),
        title=get_string("SelectScopeBox"),
        multiselect=False,
    )
    if not chosen:
        return None
    return _apply_scope_box(view, choices[chosen], get_string)


def _create_from_scope_box_pick(view, get_string):
    if not get_scope_boxes(view.Document):
        forms.alert(get_string("NoScopeBoxes"))
        return None
    scope_box = pick_scope_box_on_screen(view, get_string("PickScopeBox"))
    if not scope_box:
        return None
    return _apply_scope_box(view, scope_box, get_string)


def create_box_from_chosen_source(view, get_string):
    """Ask where a missing section or crop box should come from and create it.

    Offers the elements visible in the view, a scope box chosen from a list and
    a scope box clicked in the view. In a 3D view the result is a section box
    shaped like the source. In plan, section and elevation views it is the
    crop box: fitted to the visible elements, or driven by the scope box
    assigned to the view.

    Args:
        view (DB.View): 3D, plan, section or elevation view without a box.
        get_string (callable): maps a locale key to its translated string.

    Returns:
        str | None: name of the source that was used; None when the user
            cancelled or the box could not be created.
    """
    prompt_key = (
        "NoSectionBoxPrompt" if isinstance(view, DB.View3D) else "NoCropBoxPrompt"
    )
    creators = {
        get_string("SourceVisibleElements"): _create_from_visible_elements,
        get_string("SourceScopeBoxList"): _create_from_scope_box_list,
        get_string("SourceScopeBoxPick"): _create_from_scope_box_pick,
    }
    chosen = forms.CommandSwitchWindow.show(
        [
            get_string("SourceVisibleElements"),
            get_string("SourceScopeBoxList"),
            get_string("SourceScopeBoxPick"),
        ],
        message=get_string(prompt_key),
    )
    if not chosen:
        return None
    try:
        return creators[chosen](view, get_string)
    except Exception as ex:
        logger.exception("Could not create the box: {}".format(ex))
        forms.alert(get_string("AnErrorOccurredFormat").format(str(ex)))
        return None
