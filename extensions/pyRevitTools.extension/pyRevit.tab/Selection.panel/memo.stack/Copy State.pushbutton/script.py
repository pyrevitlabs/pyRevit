import pickle

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script
import viewport_placement_utils as vpu

__doc__ = 'Copies the state of desired parameter of the active'\
          ' view to memory. e.g. Visibility Graphics settings or'\
          ' Zoom state. Run it and see how it works.'

__authors__ = ['Gui Talarico', '{{author}}']

logger = script.get_logger()


class BasePoint:
    def __init__(self):
        self.x = 0
        self.y = 0


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

        sbox = vpu.BBox()
        sbox.minx = sb.Min.X
        sbox.miny = sb.Min.Y
        sbox.minz = sb.Min.Z
        sbox.maxx = sb.Max.X
        sbox.maxy = sb.Max.Y
        sbox.maxz = sb.Max.Z

        vo = vpu.ViewOrient()
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

    CopyPasteViewportPlacement
    Copy and paste the placement of viewports across sheets
    github.com/gtalarico

    --------------------------------------------------------
    pyrevit Notice:
    pyrevit: repository at https://github.com/eirannejad/pyrevit
    """
    vport = vpu.select_viewport()

    originalviewtype = ''

    datafile = \
        script.get_document_data_file(file_id='SaveViewportLocation',
                                      file_ext='pym',
                                      add_cmd_name=False)

    view = revit.doc.GetElement(vport.ViewId)
    if isinstance(view, DB.ViewPlan):
        # TODO ask use to choose a mode
        #  if SectionBoxes either None
        #  and CropRegions (and SectionBoxes) are not identical
        #  and ViewNormal are identical
        #  (optional) if difference between CropRegions is too big
        # TODO use LeftTop alignment by default,
        #  choose CropBox alignment (LeftTop, RightTop etc.)
        use_base_point = forms.CommandSwitchWindow.show(
            ['Crop Box','Project Base Point'],
            message='Select alignment'
        ) == 'Project Base Point'
        with revit.DryTransaction('Activate & Read Cropbox Boundary'):
            transmatrix = vpu.set_tansform_matrix(vport, view)
            if use_base_point:
                crop_region_curves = vpu.get_crop_region(view)
            else:
                crop_region_curves = None
        with revit.TransactionGroup('Copy Viewport Location'):
            title_block_pt = vpu.get_title_block_placement_by_vp(vport)
            # Vport center on a sheet (sheet UCS)
            center = vport.GetBoxCenter() - title_block_pt
            # Vport center on a sheet (model UCS)
            modelpoint = vpu.transform_by_matrix(center, transmatrix)
            center_pt = vpu.Point(center.X, center.Y, center.Z)
            model_pt = vpu.Point(modelpoint.X, modelpoint.Y, modelpoint.Z)
            with open(datafile, 'wb') as fp:
                originalviewtype = 'ViewPlan'
                pickle.dump(originalviewtype, fp)
                pickle.dump(center_pt, fp)
                pickle.dump(model_pt, fp)
                if crop_region_curves:
                    pickle.dump(make_picklable_list(crop_region_curves), fp)
                else:
                    pickle.dump(None, fp)

    elif isinstance(view, DB.ViewDrafting):
        center = vport.GetBoxCenter()
        center_pt = vpu.Point(center.X, center.Y, center.Z)
        with open(datafile, 'wb') as fp:
            originalviewtype = 'ViewDrafting'
            pickle.dump(originalviewtype, fp)
            pickle.dump(center_pt, fp)

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

    selected_els = revit.get_selection().elements
    if selected_els and isinstance(selected_els[0], DB.Viewport):
        vport = selected_els[0]
        av = revit.doc.GetElement(vport.ViewId)
    else:
        av = revit.activeview # FIXME
    curve_loops = vpu.get_crop_region(av)

    if curve_loops:
        with open(datafile, 'w') as f:
            pickle.dump(make_picklable_list(curve_loops), f)
    else:
        logger.error("Crop regions is not valid")