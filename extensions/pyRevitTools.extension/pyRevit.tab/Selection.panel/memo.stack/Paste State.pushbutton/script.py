# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
import os
import os.path as op
import pickle
import math
import inspect
from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script
import copy_paste_state_actions

__doc__ = 'Applies the copied state to the active view. '\
          'This works in conjunction with the Copy State tool.'

logger = script.get_logger()

available_actions = {}
for mem in inspect.getmembers(copy_paste_state_actions):
    moduleobject = mem[1]
    if inspect.isclass(moduleobject) \
            and hasattr(moduleobject, 'is_copy_paste_action'):
        if hasattr(moduleobject, 'validate_context') \
                and not moduleobject.validate_context():
            available_actions[moduleobject.name] = moduleobject

selected_option = \
    forms.CommandSwitchWindow.show(available_actions.keys(),
        message='Select property to be copied to memory:'
        )
if selected_option:
    action = available_actions[selected_option]()
    action.paste_wrapper()

script.exit()

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
    except Exception:
        logger.error('CAN NOT FIND ZOOM STATE FILE:\n{0}'.format(datafile))
    else:
        try:
            av = revit.uidoc.GetOpenUIViews()[0]
            view_type_saved = pickle.load(f)
            if view_type_saved != type(revit.active_view).__name__:
                forms.alert('Saved view type is different from active view',
                            exitscript=True)
            vc1, vc2 = pickle.load(f)
            # load ViewOrientation3D
            if isinstance(revit.active_view, DB.View3D):
                if revit.active_view.IsLocked:
                    f.close()
                    forms.alert('Current view orientation is locked', 
                                exitscript=True)
                view_orientation = pickle.load(f)
                revit.active_view.SetOrientation(view_orientation.deserialize())
            elif isinstance(revit.active_view, DB.ViewSection):
                direction = pickle.load(f)
                angle = direction.deserialize().AngleTo(
                            revit.active_view.ViewDirection)
                if not is_close(angle, math.pi) and not is_close(angle, 0):
                    f.close()
                    forms.alert("Views are not parallel", exitscript=True)
            f.close()
            av.ZoomAndCenterRectangle(vc1.deserialize(), vc2.deserialize())
        except Exception as exc:
            logger.error('ERROR OCCURED:\n{}'.format(exc))

elif selected_switch == '3D Section Box State':
    datafile = \
        script.get_document_data_file(file_id='SaveSectionBoxState',
                                      file_ext='pym',
                                      add_cmd_name=False)

    try:
        f = open(datafile, 'r')
        section_box = pickle.load(f)
        view_orientation = pickle.load(f)
        f.close()
    except Exception:
        forms.alert('Can not find any section box '
                    'settings in memory:\n{0}'.format(datafile))
    else:
        av = revit.active_view
        avui = revit.uidoc.GetOpenUIViews()[0]
        if isinstance(av, DB.View3D):
            with revit.Transaction('Paste Section Box Settings'):
                av.SetSectionBox(section_box.deserialize())
                av.SetOrientation(view_orientation.deserialize())

            avui.ZoomToFit()
        else:
            forms.alert('You must be on a 3D view to paste '
                        'Section Box settings.')


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
                        selview.HideElements(
                            List[DB.ElementId](viewspecificelements))
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
