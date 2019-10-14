from pyrevit import revit, script, forms, DB
from pyrevit.framework import List
from pyrevit import HOST_APP

logger = script.get_logger()

class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class BBox:
    def __init__(self):
        self.minx = 0
        self.miny = 0
        self.minz = 0
        self.maxx = 0
        self.maxy = 0
        self.maxz = 0


class ViewOrient:
    def __init__(self):
        self.eyex = 0
        self.eyey = 0
        self.eyez = 0
        self.forwardx = 0
        self.forwardy = 0
        self.forwardz = 0
        self.upx = 0
        self.upy = 0
        self.upz = 0



class TransformationMatrix:
    def __init__(self):
        self.sourcemin = None
        self.sourcemax = None
        self.destmin = None
        self.destmax = None


def transform_by_matrix(coord, transmatrix):
    newx = \
        transmatrix.destmin.X \
        + (((coord.X - transmatrix.sourcemin.X)
            * (transmatrix.destmax.X - transmatrix.destmin.X))
           / (transmatrix.sourcemax.X - transmatrix.sourcemin.X))

    newy = \
        transmatrix.destmin.Y \
        + (((coord.Y - transmatrix.sourcemin.Y)
            * (transmatrix.destmax.Y - transmatrix.destmin.Y))
           / (transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))

    return DB.XYZ(newx, newy, 0.0)


def set_tansform_matrix(selvp, selview, vpboundaryoffset=0.1, reverse=False):
    # TODO support sections
    # TODO allow to run with view activated instead of viewport selected
    # TODO paste on many views at once
    transmatrix = TransformationMatrix()

    # making sure the cropbox is active.
    cboxannoparam = selview.get_Parameter(
        DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
        )
    curviewelements = \
        DB.FilteredElementCollector(revit.doc)\
          .OwnedByView(selview.Id)\
          .WhereElementIsNotElementType()\
          .ToElements()

    viewspecificelements = []
    for el in curviewelements:
        if el.ViewSpecific \
                and not el.IsHidden(selview) \
                and el.CanBeHidden(selview) \
                and el.Category:
            viewspecificelements.append(el.Id)

    hide_elements_categories = [
        DB.BuiltInCategory.OST_SharedBasePoint,
        DB.BuiltInCategory.OST_ProjectBasePoint,
        DB.BuiltInCategory.OST_Viewers,
        DB.BuiltInCategory.OST_ReferenceLines,
        DB.BuiltInCategory.OST_Grids,
        DB.BuiltInCategory.OST_Elev
    ]
    hide_elements_filters = []
    for cat in hide_elements_categories:
        hide_elements_filters.append(DB.ElementCategoryFilter(cat))

    hide_elements_filter = DB.LogicalOrFilter(hide_elements_filters)
    hide_elements = DB.FilteredElementCollector(revit.doc) \
                   .WherePasses(hide_elements_filter) \
                   .WhereElementIsNotElementType() \
                   .ToElements()
    for el in hide_elements:
        if el.Category\
            and not el.IsHidden(selview) \
            and el.CanBeHidden(selview):
            viewspecificelements.append(el.Id)


    if viewspecificelements:
        try:
            selview.HideElements(List[DB.ElementId](viewspecificelements))
        except Exception as e:
            logger.debug(e)

    selview.CropBoxActive = True
    selview.CropBoxVisible = False
    if not cboxannoparam.IsReadOnly:
        cboxannoparam.Set(0)

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
