import pickle

from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script
import viewport_placement_utils as vpu

__doc__ = 'Applies the copied state to the active view. '\
          'This works in conjunction with the Copy State tool.'

logger = script.get_logger()


class OriginalIsViewDrafting(Exception):
    pass


class OriginalIsViewPlan(Exception):
    pass


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
    vport = vpu.select_viewport()

    PINAFTERSET = False
    originalviewtype = ''

    selview = selvp = None
    vpboundaryoffset = 0.01
    activeSheet = revit.uidoc.ActiveGraphicalView

    datafile = \
        script.get_document_data_file(file_id='SaveViewportLocation',
                                      file_ext='pym',
                                      add_cmd_name=False)
                                      
    view = revit.doc.GetElement(vport.ViewId)
    if view is not None and isinstance(view, DB.ViewPlan):
        with revit.TransactionGroup('Paste Viewport Location'):
            revtransmatrix = vpu.set_tansform_matrix(vport, view, vpboundaryoffset, reverse=True)
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
                        vpu.transform_by_matrix(savedmodel_pt, revtransmatrix) - center
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
