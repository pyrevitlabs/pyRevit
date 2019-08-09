import os
import os.path as op
import pickle

from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


__doc__ = 'Copies the state of desired parameter of the active'\
          ' view to memory. e.g. Visibility Graphics settings or'\
          ' Zoom state. Run it and see how it works.'

__authors__ = ['Gui Talarico', '{{author}}']


class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class BasePoint:
    def __init__(self):
        self.x = 0
        self.y = 0


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


def make_picklable_list(curve_loops):
    all_cloops = []
    for curve_loop in curve_loops:
        cloop_lines = []
        for rvt_line in curve_loop:
            p1 = (rvt_line.GetEndPoint(0).X, rvt_line.GetEndPoint(0).Y)
            p2 = (rvt_line.GetEndPoint(1).X, rvt_line.GetEndPoint(1).Y)
            cloop_lines.append((p1, p2))
        
        all_cloops.append(cloop_lines)
    return all_cloops


selected_option = \
    forms.CommandSwitchWindow.show(
        ['View Zoom/Pan State',
         '3D Section Box State',
         'Viewport Placement on Sheet',
         'Visibility Graphics',
         'Crop Region'],
        message='Select property to be copied to memory:'
        )


if selected_option == 'View Zoom/Pan State':
    datafile = \
        script.get_document_data_file(file_id='SaveRevitActiveViewZoomState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    av = revit.uidoc.GetOpenUIViews()[0]
    cornerlist = av.GetZoomCorners()

    vc1 = cornerlist[0]
    vc2 = cornerlist[1]
    p1 = BasePoint()
    p2 = BasePoint()
    p1.x = vc1.X
    p1.y = vc1.Y
    p2.x = vc2.X
    p2.y = vc2.Y

    f = open(datafile, 'w')
    pickle.dump(p1, f)
    pickle.dump(p2, f)
    f.close()

elif selected_option == '3D Section Box State':
    datafile = \
        script.get_document_data_file(file_id='SaveSectionBoxState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    av = revit.active_view
    avui = revit.uidoc.GetOpenUIViews()[0]

    if isinstance(av, DB.View3D):
        sb = av.GetSectionBox()
        viewOrientation = av.GetOrientation()

        sbox = BBox()
        sbox.minx = sb.Min.X
        sbox.miny = sb.Min.Y
        sbox.minz = sb.Min.Z
        sbox.maxx = sb.Max.X
        sbox.maxy = sb.Max.Y
        sbox.maxz = sb.Max.Z

        vo = ViewOrient()
        vo.eyex = viewOrientation.EyePosition.X
        vo.eyey = viewOrientation.EyePosition.Y
        vo.eyez = viewOrientation.EyePosition.Z
        vo.forwardx = viewOrientation.ForwardDirection.X
        vo.forwardy = viewOrientation.ForwardDirection.Y
        vo.forwardz = viewOrientation.ForwardDirection.Z
        vo.upx = viewOrientation.UpDirection.X
        vo.upy = viewOrientation.UpDirection.Y
        vo.upz = viewOrientation.UpDirection.Z

        f = open(datafile, 'w')
        pickle.dump(sbox, f)
        pickle.dump(vo, f)
        f.close()
    else:
        forms.alert('You must be on a 3D view to copy Section Box settings.')

elif selected_option == 'Viewport Placement on Sheet':
    """
    Copyright (c) 2016 Gui Talarico

    CopyPasteViewportPlacemenet
    Copy and paste the placement of viewports across sheets
    github.com/gtalarico

    --------------------------------------------------------
    pyrevit Notice:
    pyrevit: repository at https://github.com/eirannejad/pyrevit
    """
    originalviewtype = ''

    selview = selvp = None
    vpboundaryoffset = 0.01
    activeSheet = revit.active_view
    transmatrix = TransformationMatrix()
    revtransmatrix = TransformationMatrix()

    def sheet_to_view_transform(sheetcoord):
        global transmatrix
        newx = \
            transmatrix.destmin.X \
            + (((sheetcoord.X - transmatrix.sourcemin.X)
                * (transmatrix.destmax.X - transmatrix.destmin.X))
               / (transmatrix.sourcemax.X - transmatrix.sourcemin.X))

        newy = \
            transmatrix.destmin.Y \
            + (((sheetcoord.Y - transmatrix.sourcemin.Y)
                * (transmatrix.destmax.Y - transmatrix.destmin.Y))
               / (transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))

        return DB.XYZ(newx, newy, 0.0)

    def set_tansform_matrix(selvp, selview):
        # making sure the cropbox is active.
        cboxactive = selview.CropBoxActive
        cboxvisible = selview.CropBoxVisible
        cboxannoparam = selview.get_Parameter(
            DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
            )

        cboxannostate = cboxannoparam.AsInteger()
        curviewelements = DB.FilteredElementCollector(revit.doc)\
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

                    transmatrix.sourcemin = vpmin
                    transmatrix.sourcemax = vpmax
                    transmatrix.destmin = cropmin
                    transmatrix.destmax = cropmax

                    revtransmatrix.sourcemin = cropmin
                    revtransmatrix.sourcemax = cropmax
                    revtransmatrix.destmin = vpmin
                    revtransmatrix.destmax = vpmax

                    selview.CropBoxActive = cboxactive
                    selview.CropBoxVisible = cboxvisible
                    cboxannoparam.Set(cboxannostate)

                    if viewspecificelements:
                        selview.UnhideElements(
                            List[DB.ElementId](viewspecificelements)
                            )

    datafile = \
        script.get_document_data_file(file_id='SaveViewportLocation',
                                      file_ext='pym',
                                      add_cmd_name=False)

    selected_ids = revit.get_selection().element_ids

    if len(selected_ids) == 1:
        vport_id = selected_ids[0]
        try:
            vport = revit.doc.GetElement(vport_id)
        except Exception:
            forms.alert('Select exactly one viewport.')

        if isinstance(vport, DB.Viewport):
            view = revit.doc.GetElement(vport.ViewId)
            if view is not None and isinstance(view, DB.ViewPlan):
                with revit.TransactionGroup('Copy Viewport Location'):
                    set_tansform_matrix(vport, view)
                    center = vport.GetBoxCenter()
                    modelpoint = sheet_to_view_transform(center)
                    center_pt = Point(center.X, center.Y, center.Z)
                    model_pt = Point(modelpoint.X, modelpoint.Y, modelpoint.Z)
                    with open(datafile, 'wb') as fp:
                        originalviewtype = 'ViewPlan'
                        pickle.dump(originalviewtype, fp)
                        pickle.dump(center_pt, fp)
                        pickle.dump(model_pt, fp)

            elif view is not None and isinstance(view, DB.ViewDrafting):
                center = vport.GetBoxCenter()
                center_pt = Point(center.X, center.Y, center.Z)
                with open(datafile, 'wb') as fp:
                    originalviewtype = 'ViewDrafting'
                    pickle.dump(originalviewtype, fp)
                    pickle.dump(center_pt, fp)
            else:
                forms.alert('This tool only works with Plan, '
                            'RCP, and Detail views and viewports.')
    else:
        forms.alert('Select exactly one viewport.')

elif selected_option == 'Visibility Graphics':
    datafile = \
        script.get_document_data_file(file_id='SaveVisibilityGraphicsState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    av = revit.active_view

    f = open(datafile, 'w')
    pickle.dump(int(av.Id.IntegerValue), f)
    f.close()

elif selected_option == 'Crop Region':
    datafile = \
        script.get_document_data_file(file_id='SaveCropRegionState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    av = revit.active_view
    crsm = av.GetCropRegionShapeManager()

    crsm_valid = False
    if HOST_APP.is_newer_than(2015):
        crsm_valid = crsm.CanHaveShape
    else:
        crsm_valid = crsm.Valid

    if crsm_valid:
        with open(datafile, 'w') as f:
            if HOST_APP.is_newer_than(2015):
                curve_loops = list(crsm.GetCropShape())
            else:
                curve_loops = [crsm.GetCropRegionShape()]
            
            if curve_loops:
                pickle.dump(make_picklable_list(curve_loops), f)
