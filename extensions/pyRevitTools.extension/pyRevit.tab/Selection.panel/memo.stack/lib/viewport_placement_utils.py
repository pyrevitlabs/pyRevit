from pyrevit import revit, script, forms, DB
from pyrevit.framework import List
from pyrevit import HOST_APP

logger = script.get_logger()

def hide_all_elements(view):
    # hide all elements in the view
    cl_view_elements = DB.FilteredElementCollector(view.Document, view.Id) \
                   .WhereElementIsNotElementType()
    elements_to_hide = [el.Id for el in cl_view_elements.ToElements()
                        if not el.IsHidden(view) and el.CanBeHidden(view)]
    if elements_to_hide:
        try:
            view.HideElements(List[DB.ElementId](elements_to_hide))
        except Exception as exc:
            logger.warn(exc)
    return elements_to_hide

def unhide_all_elements(view, elements):
    if elements:
        try:
            view.UnhideElements(List[DB.ElementId](elements))
        except Exception as exc:
            logger.warn(exc)

def activate_cropbox(view):
    cboxannoparam = view.get_Parameter(
        DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    current_active = view.CropBoxActive
    current_visible = view.CropBoxVisible
    current_annotations = cboxannoparam.AsInteger()
    # making sure the cropbox is active.
    view.CropBoxActive = True
    view.CropBoxVisible = True
    if not cboxannoparam.IsReadOnly:
        cboxannoparam.Set(0)
    return current_active, current_visible, current_annotations


def recover_cropbox(view, saved_values):
    saved_active, saved_visible, saved_annotations = saved_values
    cboxannoparam = view.get_Parameter(
        DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
    view.CropBoxActive = saved_active
    view.CropBoxVisible = saved_visible
    if not cboxannoparam.IsReadOnly:
        cboxannoparam.Set(saved_annotations)


def set_tansform_matrix(selvp, selview, vpboundaryoffset=0.1, reverse=False):
    # TODO support sections
    # TODO allow to run with view activated instead of viewport selected
    # TODO paste on many views at once
    transmatrix = TransformationMatrix()

    hide_all_elements(selview)
    activate_cropbox(selview)

    # get view min max points in modelUCS.
    modelucsx = []
    modelucsy = []
    crsm = selview.GetCropRegionShapeManager()

    cllist = crsm.GetCropShape()
    if len(cllist) == 1:
        cl = cllist[0]
        for l in cl:
            modelucsx.append(l.GetEndPoint(0).X)
            modelucsy.append(l.GetEndPoint(0).Y)
        cropmin = DB.XYZ(min(modelucsx), min(modelucsy), 0.0)
        cropmax = DB.XYZ(max(modelucsx), max(modelucsy), 0.0)

        # get vp min max points in sheetUCS
        ol = selvp.GetBoxOutline()
        vptempmin = ol.MinimumPoint # in viewport units
        vpmin = DB.XYZ(vptempmin.X + vpboundaryoffset,
                       vptempmin.Y + vpboundaryoffset,
                       0.0)
        vptempmax = ol.MaximumPoint
        vpmax = DB.XYZ(vptempmax.X - vpboundaryoffset,
                       vptempmax.Y - vpboundaryoffset,
                       0.0)

        transmatrix.sourcemin = cropmin if reverse else vpmin
        transmatrix.sourcemax = cropmax if reverse else vpmax
        transmatrix.destmin = vpmin if reverse else cropmin
        transmatrix.destmax = vpmax if reverse else cropmax
    return transmatrix


def select_viewport():
    vport = None
    selected_els = revit.get_selection().elements
    if selected_els and isinstance(selected_els[0], DB.Viewport):
        vport = selected_els[0]
    if not vport:
        forms.alert('Select exactly one viewport.', exitscript=True)

    view = revit.doc.GetElement(vport.ViewId)
    if not view and not(isinstance(view, DB.ViewPlan) or isinstance(view, DB.ViewDrafting)):
        forms.alert('This tool only works with Plan, '
                    'RCP, and Detail views and viewports.', exitscript=True)
    return vport

def get_title_block_placement_by_vp(viewport):
    title_block_pt = None
    if viewport.SheetId and viewport.SheetId != DB.ElementId.InvalidElementId:
        title_block_pt = get_title_block_placement(
            viewport.Document.GetElement(viewport.SheetId))
    if not title_block_pt:
        title_block_pt = DB.XYZ.Zero
    return title_block_pt


def get_title_block_placement(sheet):
    # get all title blocks on the sheet
    cl = DB.FilteredElementCollector(sheet.Document, sheet.Id). \
         WhereElementIsNotElementType(). \
         OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
    title_blocks = cl.ToElements()
    if len(title_blocks) != 1:
        return

    return title_blocks[0].Location.Point


def get_crop_region(view):
    crsm = view.GetCropRegionShapeManager()
    if HOST_APP.is_newer_than(2015):
        crsm_valid = crsm.CanHaveShape
    else:
        crsm_valid = crsm.Valid

    if crsm_valid:
        if HOST_APP.is_newer_than(2015):
            curve_loops = list(crsm.GetCropShape())
        else:
            curve_loops = [crsm.GetCropRegionShape()]

        if curve_loops:
            return curve_loops


def set_crop_region(view, curve_loops):
    if not isinstance(curve_loops, list):
        curve_loops = [curve_loops]

    crop_active_saved = view.CropBoxActive
    view.CropBoxActive = True
    crsm = view.GetCropRegionShapeManager() # FIXME
    for cloop in curve_loops:
        if HOST_APP.is_newer_than(2015):
            crsm.SetCropShape(cloop)
        else:
            crsm.SetCropRegionShape(cloop)
    view.CropBoxActive = crop_active_saved


def view_plane(view):
    return DB.Plane.CreateByOriginAndBasis(view.Origin, view.RightDirection, view.UpDirection)


def project_to_viewport(xyz, view):
    plane = view_plane(view)
    uv, dist = plane.Project(xyz)
    return uv


def project_to_world(uv, view):
    plane = view_plane(view)
    trf = DB.Transform.Identity
    trf.BasisX = plane.XVec
    trf.BasisY = plane.YVec
    trf.BasisZ = plane.Normal
    trf.Origin = plane.Origin
    return trf.OfPoint(DB.XYZ(uv.U, uv.V, 0))


def zero_cropbox(view):
    p1 = DB.XYZ(0,0,0)
    p3 = DB.XYZ(1,1,1)

    uv1 = project_to_viewport(p1, view)
    uv3 = project_to_viewport(p3, view)

    uv2 = DB.UV(uv1.U, uv3.V)
    uv4 = DB.UV(uv3.U, uv1.V)

    p2 = project_to_world(uv2, view)
    p4 = project_to_world(uv4, view)

    p1 = project_to_world(project_to_viewport(p1, view), view)
    p3 = project_to_world(project_to_viewport(p3, view), view)

    l1 = DB.Line.CreateBound(p1, p2)
    l2 = DB.Line.CreateBound(p2, p3)
    l3 = DB.Line.CreateBound(p3, p4)
    l4 = DB.Line.CreateBound(p4, p1)

    crv_loop = DB.CurveLoop()
    for crv in (l1, l2, l3, l4):
        crv_loop.Append(crv)

    return crv_loop