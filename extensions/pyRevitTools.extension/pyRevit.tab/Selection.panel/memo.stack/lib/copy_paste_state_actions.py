# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
import pickle
import math
from pyrevit import revit, script, forms, DB
from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit.coreutils import logger

mlogger = logger.get_logger(__name__)


def is_close(a, b, rnd=5):
    return a == b or int(a*10**rnd) == int(b*10**rnd)


def copy_paste_action(func):
    func.is_copy_paste_action = True
    return func


def get_selected_viewports():
    selected_els = revit.get_selection().elements
    return [e for e in selected_els
            if isinstance(e, DB.Viewport)]


def get_selected_views():
    selected_els = revit.get_selection().elements
    return [e for e in selected_els
            if isinstance(e, DB.View)]


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
    crsm = view.GetCropRegionShapeManager()  # FIXME
    for cloop in curve_loops:
        if HOST_APP.is_newer_than(2015):
            crsm.SetCropShape(cloop)
        else:
            crsm.SetCropRegionShape(cloop)
    view.CropBoxActive = crop_active_saved


def view_plane(view):
    return DB.Plane.CreateByOriginAndBasis(
        view.Origin, view.RightDirection, view.UpDirection)


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


class DataFile(object):
    def __init__(self, action_name, mode='r'):
        self.datafile = script.get_document_data_file(
            file_id='CopyPasteState_' + action_name,
            file_ext='pym',
            add_cmd_name=False)
        self.mode = mode

    def __enter__(self):
        self.file = open(self.datafile, self.mode)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.close()
        if exception_value:
            forms.alert(str(exception_value))

    def dump(self, value):
        # make picklable (serialize)
        value_serialized = revit.serializable.serialize(value)
        pickle.dump(value_serialized, self.file)

    def load(self):
        # unpickle (deserialize)
        value_serialized = pickle.load(self.file)
        return revit.serializable.deserialize(value_serialized)


class CopyPasteStateAction(object):
    name = '-'

    def copy(self, datafile):
        pass

    def paste(self, datafile):
        pass

    @staticmethod
    def validate_context():
        return

    def copy_wrapper(self):
        # pylint: disable=assignment-from-none
        validate_msg = self.validate_context()
        if validate_msg:
            forms.alert(validate_msg)
        else:
            with DataFile(self.__class__.__name__, 'w') as datafile:
                self.copy(datafile)

    def paste_wrapper(self):
        # pylint: disable=assignment-from-none
        validate_msg = self.validate_context()
        if validate_msg:
            forms.alert(validate_msg)
        else:
            with DataFile(self.__class__.__name__, 'r') as datafile:
                self.paste(datafile)


@copy_paste_action
class ViewZoomPanState(CopyPasteStateAction):
    name = 'View Zoom/Pan State'

    def copy(self, datafile):
        datafile.dump(type(revit.active_view).__name__)
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        corner_list = active_ui_view.GetZoomCorners()
        datafile.dump(corner_list)
        # dump ViewOrientation3D
        if isinstance(revit.active_view, DB.View3D):
            orientation = revit.active_view.GetOrientation()
            datafile.dump(orientation)
        elif isinstance(revit.active_view, DB.ViewSection):
            direction = revit.active_view.ViewDirection
            datafile.dump(direction)

    def paste(self, datafile):
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        view_type_saved = datafile.load()
        if view_type_saved != type(revit.active_view).__name__:
            raise Exception(
                'Saved view type (%s) is different from active view (%s)' % (
                    view_type_saved, type(revit.active_view).__name__))
        vc1, vc2 = datafile.load()
        # load ViewOrientation3D
        if isinstance(revit.active_view, DB.View3D):
            if revit.active_view.IsLocked:
                raise Exception('Current view orientation is locked')
            view_orientation = datafile.load()
            revit.active_view.SetOrientation(view_orientation)
        elif isinstance(revit.active_view, DB.ViewSection):
            direction = datafile.load()
            angle = direction.AngleTo(revit.active_view.ViewDirection)
            if not is_close(angle, math.pi) and not is_close(angle, 0):
                raise Exception("Views are not parallel")
        active_ui_view.ZoomAndCenterRectangle(vc1, vc2)

    @staticmethod
    def validate_context():
        if not isinstance(revit.active_view, (
                DB.ViewPlan,
                DB.ViewSection,
                DB.View3D,
                DB.ViewSheet,
                DB.ViewDrafting)):
            return "Type of active view is not supported"


@copy_paste_action
class SectionBox3DState(CopyPasteStateAction):
    name = '3D Section Box State'

    def copy(self, datafile):
        section_box = revit.active_view.GetSectionBox()
        view_orientation = revit.active_view.GetOrientation()
        datafile.dump(section_box)
        datafile.dump(view_orientation)

    def paste(self, datafile):
        section_box = datafile.load()
        view_orientation = datafile.load()
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        with revit.Transaction('Paste Section Box Settings'):
            revit.active_view.SetSectionBox(section_box)
            revit.active_view.SetOrientation(view_orientation)
        active_ui_view.ZoomToFit()

    @staticmethod
    def validate_context():
        if not isinstance(revit.active_view, DB.View3D):
            return "You must be on a 3D view to copy and paste 3D section box."


@copy_paste_action
class VisibilityGraphics(CopyPasteStateAction):
    name = 'Visibility Graphics'

    def copy(self, datafile):
        datafile.dump(int(revit.active_view.Id))

    def paste(self, datafile):
        e_id = datafile.load()
        with revit.Transaction('Paste Visibility Graphics'):
            revit.active_view.ApplyViewTemplateParameters(
                revit.doc.GetElement(e_id))


@copy_paste_action
class CropRegion(CopyPasteStateAction):
    name = 'Crop Region'

    @staticmethod
    def is_cropable(view):
        return not isinstance(view, (DB.ViewSheet, DB.ViewSchedule)) \
            and view.ViewType not in (DB.ViewType.Legend, 
                                      DB.ViewType.DraftingView)
    
    @staticmethod
    def get_views():
        # try to use active view
        if CropRegion.is_cropable(revit.active_view):
            return [revit.active_view]
        # try to use selected viewports
        else:
            selected_viewports = get_selected_viewports()
            selected_views = [revit.doc.GetElement(viewport.ViewId) \
                              for viewport in selected_viewports]
            selected_views.extend(get_selected_views())
            return [view for view in selected_views
                    if CropRegion.is_cropable(view)]

    def copy(self, datafile):
        view = CropRegion.get_views()[0]
        curve_loops = get_crop_region(view)
        if curve_loops:
            datafile.dump(curve_loops)
        else:
            raise Exception('Cannot read crop region from selected view')

    def paste(self, datafile):
        crv_loops = datafile.load()
        with revit.Transaction('Paste Crop Region'):
            for view in CropRegion.get_views():
                set_crop_region(view, crv_loops)

        revit.uidoc.RefreshActiveView()

    @staticmethod
    def validate_context():
        if not CropRegion.get_views():
            return "Activate a view or select at least one cropable viewport"

ALIGNMENT_CROPBOX = 'Crop Box'
ALIGNMENT_BASEPOINT = 'Project Base Point'

ALIGNMENT_BOTTOM_LEFT = 'Bottom Left'
ALIGNMENT_BOTTOM_RIGHT = 'Bottom Right'
ALIGNMENT_TOP_LEFT = 'Top Left'
ALIGNMENT_TOP_RIGHT = 'Top Right'
ALIGNMENT_CENTER = 'Center'

@copy_paste_action
class ViewportPlacement(CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'

    @staticmethod
    def calculate_offset(view, saved_offset, alignment):
        if alignment == ALIGNMENT_CENTER:
            return DB.XYZ.Zero
        else:
            outline = view.Outline
            current_offset = (outline.Max - outline.Min) / 2
            offset_uv = saved_offset - current_offset
            if alignment == ALIGNMENT_TOP_LEFT:
                return DB.XYZ(-offset_uv.U, offset_uv.V, 0)
            elif alignment == ALIGNMENT_TOP_RIGHT:
                return DB.XYZ(offset_uv.U, offset_uv.V, 0)
            elif alignment == ALIGNMENT_BOTTOM_RIGHT:
                return DB.XYZ(offset_uv.U, -offset_uv.V, 0)
            elif alignment == ALIGNMENT_BOTTOM_LEFT:
                return DB.XYZ(-offset_uv.U, -offset_uv.V, 0)

    @staticmethod
    def isolate_axis(viewport, new_center, mode=None):
        if mode in ('X', 'Y'):
            current_center = viewport.GetBoxCenter()
            if mode == 'X':
                return DB.XYZ(new_center.X, current_center.Y, 0)
            else:
                return DB.XYZ(current_center.X, new_center.Y, 0)
        else:
            return new_center

    @staticmethod
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
                mlogger.warn(exc)
        return elements_to_hide

    @staticmethod
    def unhide_all_elements(view, elements):
        if elements:
            try:
                view.UnhideElements(List[DB.ElementId](elements))
            except Exception as exc:
                mlogger.warn(exc)

    @staticmethod
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

    @staticmethod
    def recover_cropbox(view, saved_values):
        saved_active, saved_visible, saved_annotations = saved_values
        cboxannoparam = view.get_Parameter(
            DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        view.CropBoxActive = saved_active
        view.CropBoxVisible = saved_visible
        if not cboxannoparam.IsReadOnly:
            cboxannoparam.Set(saved_annotations)

    @staticmethod
    def get_title_block_placement(viewport):
        sheet = viewport.Document.GetElement(viewport.SheetId)
        cl = DB.FilteredElementCollector(sheet.Document, sheet.Id). \
            WhereElementIsNotElementType(). \
            OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
        title_blocks = cl.ToElements()
        if len(title_blocks) == 1:
            return title_blocks[0].Location.Point
        else:
            return DB.XYZ.Zero

    @staticmethod
    def zero_cropbox(view):
        p1 = DB.XYZ(0, 0, 0)
        p3 = DB.XYZ(1, 1, 1)

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

    def copy(self, datafile):
        viewports = get_selected_viewports()
        if len(viewports) != 1:
            raise Exception('Exactly one viewport must be selected')
        viewport = viewports[0]
        view = revit.doc.GetElement(viewport.ViewId)

        title_block_pt = ViewportPlacement\
            .get_title_block_placement(viewport)

        if view.ViewType in [DB.ViewType.DraftingView, DB.ViewType.Legend]:
            alignment = ALIGNMENT_CROPBOX
        else:
            alignment = forms.CommandSwitchWindow.show(
                [ALIGNMENT_CROPBOX, ALIGNMENT_BASEPOINT],
                message='Select alignment')

        if not alignment:
            return

        datafile.dump(alignment)

        with revit.DryTransaction('Activate & Read Cropbox, Copy Center'):
            if alignment == ALIGNMENT_BASEPOINT:
                set_crop_region(view, ViewportPlacement.zero_cropbox(view))
            # use cropbox as alignment if it active
            if alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
                ViewportPlacement.activate_cropbox(view)
                ViewportPlacement.hide_all_elements(view)
                revit.doc.Regenerate()

            if alignment == ALIGNMENT_CROPBOX:
                outline = view.Outline
                offset_uv = (outline.Max - outline.Min) / 2
            center = viewport.GetBoxCenter() - title_block_pt

        datafile.dump(center)
        if alignment == ALIGNMENT_CROPBOX:
            datafile.dump(offset_uv)

    def paste(self, datafile):
        viewports = get_selected_viewports()
        align_axis = None
        if __shiftclick__:  # pylint: disable=undefined-variable
            align_axis = forms.CommandSwitchWindow.show(
                ['X', 'Y', 'XY'],
                message='Align specific axis?')
        # read saved values
        saved_alignment = datafile.load()
        saved_center = datafile.load()
        if saved_alignment == ALIGNMENT_CROPBOX:
            saved_offset = datafile.load()
            corner_alignment = forms.CommandSwitchWindow.show([ALIGNMENT_CENTER,
                ALIGNMENT_TOP_LEFT, ALIGNMENT_TOP_RIGHT, ALIGNMENT_BOTTOM_RIGHT,
                ALIGNMENT_BOTTOM_LEFT], message='Select alignment')

        with revit.TransactionGroup('Paste Viewport Location'):
            for viewport in viewports:
                view = revit.doc.GetElement(viewport.ViewId)
                title_block_pt = ViewportPlacement \
                    .get_title_block_placement(viewport)
                crop_region_current = None
                cropbox_values_current = None
                hidden_elements = None
                # set temporary settings: hide elements, set cropbox visibility
                #  if cropbox is not active, do nothing (use visible elements)
                if saved_alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
                    with revit.Transaction('Temporary settings'):
                        # 'base point' mode - set cropbox to 'zero' temporary
                        if saved_alignment == ALIGNMENT_BASEPOINT:
                            crop_region_current = get_crop_region(view)
                            set_crop_region(view,
                                            ViewportPlacement.zero_cropbox(view))
                        cropbox_values_current = ViewportPlacement\
                            .activate_cropbox(view)
                        hidden_elements = ViewportPlacement\
                            .hide_all_elements(view)

                with revit.Transaction('Apply Viewport Placement'):
                    new_center = saved_center
                    # 'crop box' mode - align to vp corner if necessary
                    if saved_alignment == ALIGNMENT_CROPBOX \
                            and corner_alignment:
                        offset_xyz = ViewportPlacement.calculate_offset(
                            view, saved_offset, corner_alignment)
                        new_center += offset_xyz
                    # isolate alignment by x- or y-axis if necessary
                    new_center = ViewportPlacement.isolate_axis(
                        viewport, new_center, align_axis)
                    # apply new viewport position
                    viewport.SetBoxCenter(new_center + title_block_pt)
                # unset temporary values
                if crop_region_current:
                    with revit.Transaction('Recover crop region form'):
                        set_crop_region(view, crop_region_current)
                if cropbox_values_current:
                    with revit.Transaction('Recover crop region values'):
                        ViewportPlacement.recover_cropbox(view,
                                                          cropbox_values_current)
                if hidden_elements:
                    with revit.Transaction('Recover hidden elements'):
                        ViewportPlacement.unhide_all_elements(view,
                                                              hidden_elements)

    @staticmethod
    def validate_context():
        if not get_selected_viewports():
            return 'At least one viewport must be selected'
