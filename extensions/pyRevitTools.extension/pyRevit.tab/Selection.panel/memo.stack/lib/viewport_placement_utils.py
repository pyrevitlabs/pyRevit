from pyrevit import revit, script, forms, DB
from pyrevit.framework import List

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


def set_tansform_matrix(selvp, selview, vpboundaryoffset, reverse=False):
    transmatrix = TransformationMatrix()
    # making sure the cropbox is active.
    cboxactive = selview.CropBoxActive
    cboxvisible = selview.CropBoxVisible
    cboxannoparam = selview.get_Parameter(
        DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
        )
    cboxannostate = cboxannoparam.AsInteger()
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
                and el.Category is not None:
            viewspecificelements.append(el.Id)

    basepoints = DB.FilteredElementCollector(revit.doc)\
                   .OfClass(DB.BasePoint)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

    excludecategories = ['Survey Point',
                         'Project Base Point']
    for el in basepoints:
        if el.Category and el.Category.Name in excludecategories:
            viewspecificelements.append(el.Id)

    with revit.TransactionGroup('Activate & Read Cropbox Boundary'):
        with revit.Transaction('Hiding all 2d elements'):
            if viewspecificelements:
                try:
                    selview.HideElements(List[DB.ElementId](viewspecificelements))
                except Exception as e:
                    logger.debug(e)

        with revit.Transaction('Activate & Read Cropbox Boundary'):
            selview.CropBoxActive = True
            selview.CropBoxVisible = False
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
                vptempmin = ol.MinimumPoint
                vpmin = DB.XYZ(vptempmin.X + vpboundaryoffset,
                               vptempmin.Y + vpboundaryoffset, 0.0)
                vptempmax = ol.MaximumPoint
                vpmax = DB.XYZ(vptempmax.X - vpboundaryoffset,
                               vptempmax.Y - vpboundaryoffset, 0.0)

                transmatrix.sourcemin = cropmin if reverse else vpmin
                transmatrix.sourcemax = cropmax if reverse else vpmax
                transmatrix.destmin = vpmin if reverse else cropmin
                transmatrix.destmax = vpmax if reverse else cropmax

                selview.CropBoxActive = cboxactive
                selview.CropBoxVisible = cboxvisible
                cboxannoparam.Set(cboxannostate)

                if viewspecificelements:
                    selview.UnhideElements(List[DB.ElementId](viewspecificelements))
    return transmatrix

def select_viewport():
    vport = None
    selected_els = revit.get_selection().elements
    if selected_els and isinstance(selected_els[0], DB.Viewport):
        vport = selected_els[0]
    if not vport:
        forms.alert('Select exactly one viewport.', exitscript=True)
    return vport


def get_title_block_placement(sheet):
    # get all title blocks on the sheet
    cl = DB.FilteredElementCollector(revit.doc, sheet.Id). \
         WhereElementIsNotElementType(). \
         OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
    title_blocks = cl.ToElements()
    if len(title_blocks) != 1:
        return

    return title_blocks[0].Location.Point
