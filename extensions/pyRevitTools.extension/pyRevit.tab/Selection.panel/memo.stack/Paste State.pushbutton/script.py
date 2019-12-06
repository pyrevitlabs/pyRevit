import os
import os.path as op
import pickle

from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


__doc__ = 'Applies the copied state to the active view. '\
          'This works in conjunction with the Copy State tool.'

logger = script.get_logger()


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


class OriginalIsViewDrafting(Exception):
    pass


class OriginalIsViewPlan(Exception):
    pass


class TransformationMatrix:
    def __init__(self):
        self.sourcemin = None
        self.sourcemax = None
        self.destmin = None
        self.destmax = None


def unpickle_line_list(all_cloops_data):
    all_cloops = []
    for cloop_lines in all_cloops_data:
        curveloop = DB.CurveLoop()
        for line in cloop_lines:
            p1 = DB.XYZ(line[0][0], line[0][1], 0)
            p2 = DB.XYZ(line[1][0], line[1][1], 0)
            curveloop.Append(DB.Line.CreateBound(p1, p2))
        
        all_cloops.append(curveloop)

    return all_cloops


selected_switch = \
    forms.CommandSwitchWindow.show(
        ['View Zoom/Pan State',
         '3D Section Box State',
         'Viewport Placement on Sheet',
         'Visibility Graphics',
         'Crop Region'],
        message='Select property to be applied to current view:'
        )


if selected_switch == 'View Zoom/Pan State':
    datafile = \
        script.get_document_data_file(file_id='SaveRevitActiveViewZoomState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    try:
        f = open(datafile, 'r')
        p2 = pickle.load(f)
        p1 = pickle.load(f)
        f.close()
        vc1 = DB.XYZ(p1.x, p1.y, 0)
        vc2 = DB.XYZ(p2.x, p2.y, 0)
        av = revit.uidoc.GetOpenUIViews()[0]
        av.ZoomAndCenterRectangle(vc1, vc2)
    except Exception:
        logger.error('CAN NOT FIND ZOOM STATE FILE:\n{0}'.format(datafile))

elif selected_switch == '3D Section Box State':
    datafile = \
        script.get_document_data_file(file_id='SaveSectionBoxState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    try:
        f = open(datafile, 'r')
        sbox = pickle.load(f)
        vo = pickle.load(f)
        f.close()

        sb = DB.BoundingBoxXYZ()
        sb.Min = DB.XYZ(sbox.minx, sbox.miny, sbox.minz)
        sb.Max = DB.XYZ(sbox.maxx, sbox.maxy, sbox.maxz)

        vor = DB.ViewOrientation3D(DB.XYZ(vo.eyex,
                                          vo.eyey,
                                          vo.eyez),
                                   DB.XYZ(vo.upx,
                                          vo.upy,
                                          vo.upz),
                                   DB.XYZ(vo.forwardx,
                                          vo.forwardy,
                                          vo.forwardz))

        av = revit.active_view
        avui = revit.uidoc.GetOpenUIViews()[0]
        if isinstance(av, DB.View3D):
            with revit.Transaction('Paste Section Box Settings'):
                av.SetSectionBox(sb)
                av.SetOrientation(vor)

            avui.ZoomToFit()
        else:
            forms.alert('You must be on a 3D view to paste '
                        'Section Box settings.')
    except Exception:
        forms.alert('Can not find any section box '
                    'settings in memory:\n{0}'.format(datafile))

elif selected_switch == 'Viewport Placement on Sheet':
    """
    Copyright (c) 2016 Gui Talarico

    CopyPasteViewportPlacemenet
    Copy and paste the placement of viewports across sheets
    github.com/gtalarico

    --------------------------------------------------------
    pyrevit Notice:
    pyrevit: repository at https://github.com/eirannejad/pyrevit
    """
    PINAFTERSET = False
    originalviewtype = ''

    selview = selvp = None
    vpboundaryoffset = 0.01
    activeSheet = revit.uidoc.ActiveGraphicalView
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

    def view_to_sheet_transform(modelcoord):
        global revtransmatrix
        newx = \
            revtransmatrix.destmin.X \
            + (((modelcoord.X - revtransmatrix.sourcemin.X)
                * (revtransmatrix.destmax.X - revtransmatrix.destmin.X))
               / (revtransmatrix.sourcemax.X - revtransmatrix.sourcemin.X))

        newy = \
            revtransmatrix.destmin.Y \
            + (((modelcoord.Y - revtransmatrix.sourcemin.Y)
                * (revtransmatrix.destmax.Y - revtransmatrix.destmin.Y))
               / (revtransmatrix.sourcemax.Y - revtransmatrix.sourcemin.Y))

        return DB.XYZ(newx, newy, 0.0)

    def set_tansform_matrix(selvp, selview):
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
            DB.TaskDialog.Show('pyrevit',
                               'Select exactly one viewport.')

        if isinstance(vport, DB.Viewport):
            view = revit.doc.GetElement(vport.ViewId)
            if view is not None and isinstance(view, DB.ViewPlan):
                with revit.TransactionGroup('Paste Viewport Location'):
                    set_tansform_matrix(vport, view)
                    try:
                        with open(datafile, 'rb') as fp:
                            originalviewtype = pickle.load(fp)
                            if originalviewtype == 'ViewPlan':
                                savedcen_pt = pickle.load(fp)
                                savedmdl_pt = pickle.load(fp)
                            else:
                                raise OriginalIsViewDrafting
                    except IOError:
                        forms.alert('Could not find saved viewport '
                                    'placement.\n'
                                    'Copy a Viewport Placement first.')
                    except OriginalIsViewDrafting:
                        forms.alert('Viewport placement info is from a '
                                    'drafting view and can not '
                                    'be applied here.')
                    else:
                        savedcenter_pt = DB.XYZ(savedcen_pt.x,
                                                savedcen_pt.y,
                                                savedcen_pt.z)
                        savedmodel_pt = DB.XYZ(savedmdl_pt.x,
                                               savedmdl_pt.y,
                                               savedmdl_pt.z)
                        with revit.Transaction('Apply Viewport Placement'):
                            center = vport.GetBoxCenter()
                            centerdiff = \
                                view_to_sheet_transform(savedmodel_pt) - center
                            vport.SetBoxCenter(savedcenter_pt - centerdiff)
                            if PINAFTERSET:
                                vport.Pinned = True

            elif view is not None and isinstance(view, DB.ViewDrafting):
                try:
                    with open(datafile, 'rb') as fp:
                        originalviewtype = pickle.load(fp)
                        if originalviewtype == 'ViewDrafting':
                            savedcen_pt = pickle.load(fp)
                        else:
                            raise OriginalIsViewPlan
                except IOError:
                    forms.alert('Could not find saved viewport '
                                'placement.\n'
                                'Copy a Viewport Placement first.')
                except OriginalIsViewPlan:
                    forms.alert('Viewport placement info is from '
                                'a model view and can not be '
                                'applied here.')
                else:
                    savedcenter_pt = DB.XYZ(savedcen_pt.x,
                                            savedcen_pt.y,
                                            savedcen_pt.z)
                    with revit.Transaction('Apply Viewport Placement'):
                        vport.SetBoxCenter(savedcenter_pt)
                        if PINAFTERSET:
                            vport.Pinned = True
            else:
                forms.alert('This tool only works with Plan, '
                            'RCP, and Detail views and viewports.')
    else:
        forms.alert('Select exactly one viewport.')

elif selected_switch == 'Visibility Graphics':
    datafile = \
        script.get_document_data_file(file_id='SaveVisibilityGraphicsState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    try:
        f = open(datafile, 'r')
        id = pickle.load(f)
        f.close()
        with revit.Transaction('Paste Visibility Graphics'):
            revit.active_view.ApplyViewTemplateParameters(
                revit.doc.GetElement(DB.ElementId(id))
                )
    except Exception:
        logger.error('CAN NOT FIND ANY VISIBILITY GRAPHICS '
                     'SETTINGS IN MEMORY:\n{0}'.format(datafile))

elif selected_switch == 'Crop Region':
    datafile = \
        script.get_document_data_file(file_id='SaveCropRegionState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    try:
        f = open(datafile, 'r')
        cloops_data = pickle.load(f)
        f.close()
        with revit.Transaction('Paste Crop Region'):
            revit.active_view.CropBoxVisible = True
            crsm = revit.active_view.GetCropRegionShapeManager()
            all_cloops = unpickle_line_list(cloops_data)
            for cloop in all_cloops:
                if HOST_APP.is_newer_than(2015):
                    crsm.SetCropShape(cloop)
                else:
                    crsm.SetCropRegionShape(cloop)

        revit.uidoc.RefreshActiveView()
    except Exception:
        logger.error('CAN NOT FIND ANY CROP REGION '
                     'SETTINGS IN MEMORY:\n{0}'.format(datafile))
