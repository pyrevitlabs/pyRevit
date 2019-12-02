# pylint: disable=import-error,invalid-name,attribute-defined-outside-init,
# pylint: disable=broad-except,missing-docstring
import pickle
import math
from pyrevit import revit, script, forms, DB
from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit.coreutils import logger

mlogger = logger.get_logger(__name__)

# alignment names for ViewportPosition

ALIGNMENT_CROPBOX = 'Crop Box'
ALIGNMENT_BASEPOINT = 'Project Base Point'

ALIGNMENT_BOTTOM_LEFT = 'Bottom Left'
ALIGNMENT_BOTTOM_RIGHT = 'Bottom Right'
ALIGNMENT_TOP_LEFT = 'Top Left'
ALIGNMENT_TOP_RIGHT = 'Top Right'
ALIGNMENT_CENTER = 'Center'


# common methods

def almost_equal(a, b, rnd=5):
    """Check if two numerical values almost equal

    Args:
        a (float): value a
        b (float): value b
        rnd (int, optional): n digits after comma. Defaults to 5.

    Returns:
        bool: True if almost equal
    """
    return a == b or int(a*10**rnd) == int(b*10**rnd)


def get_selected_viewports():
    """Extract only viewports from selected elements

    Returns:
        list[DB.Element]: list of viewport elements
    """
    selected_els = revit.get_selection().elements
    return [e for e in selected_els
            if isinstance(e, DB.Viewport)]


def get_selected_views():
    """Extract only views from selected elements

    Returns:
        list[DB.Element]: list of views
    """
    selected_els = revit.get_selection().elements
    return [e for e in selected_els
            if isinstance(e, DB.View)]


def get_views(allow_viewports=True, filter_func=None):
    """Takes either active view or selected view(s) (cropable only)

    Returns:
        list: list of views
    """
    # try to use active view
    # pylint: disable=no-else-return
    if not filter_func or filter_func(revit.active_view):
        return [revit.active_view]
    # try to use selected viewports
    else:
        selected_views = []
        if allow_viewports:
            selected_viewports = get_selected_viewports()
            selected_views.extend([revit.doc.GetElement(viewport.ViewId)
                                   for viewport in selected_viewports])
        selected_views.extend(get_selected_views())
        if filter_func:
            return [view for view in selected_views if filter_func(view)]
        else:
            return selected_views


def get_crop_region(view):
    """Takes crop region of a view

    Args:
        view (DB.View): view to get crop region from

    Returns:
        list[DB.CurveLoop]: list of curve loops
    """
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
    """Sets crop region to a view

    Args:
        view (DB.View): view to change
        curve_loops (list[DB.CurveLoop]): list of curve loops
    """
    if not isinstance(curve_loops, list):
        curve_loops = [curve_loops]

    crop_active_saved = view.CropBoxActive
    view.CropBoxActive = True
    crsm = view.GetCropRegionShapeManager()
    for cloop in curve_loops:
        if HOST_APP.is_newer_than(2015):
            crsm.SetCropShape(cloop)
        else:
            crsm.SetCropRegionShape(cloop)
    view.CropBoxActive = crop_active_saved


def view_plane(view):
    """Get a plane parallel to a view
    Args:
        view (DB.View): view to align plane

    Returns:
        DB.Plane: result plane
    """
    return DB.Plane.CreateByOriginAndBasis(
        view.Origin, view.RightDirection, view.UpDirection)


def project_to_viewport(xyz, view):
    """Project a point to viewport coordinates

    Args:
        xyz (DB.XYZ): point to project
        view (DB.View): target view

    Returns:
        DB.UV: [description]
    """
    plane = view_plane(view)
    uv, dist = plane.Project(xyz)
    return uv


def project_to_world(uv, view):
    """Get view-based point (UV) back to model coordinates.

    Args:
        uv (DB.UV): point on a view
        view (DB.View): view to get coordinates from

    Returns:
        DB.XYZ: point in world coordinates
    """
    plane = view_plane(view)
    trf = DB.Transform.Identity
    trf.BasisX = plane.XVec
    trf.BasisY = plane.YVec
    trf.BasisZ = plane.Normal
    trf.Origin = plane.Origin
    return trf.OfPoint(DB.XYZ(uv.U, uv.V, 0))


# action logic and base clases

def copy_paste_action(func):
    """Decorates Copy/Paste Action"""
    func.is_copy_paste_action = True
    return func


class DataFile(object):
    """Wraps pickle module and pyrevit datafile for using with `with`.
    Pickle methods `dump` and `load` can be used without pointing to file.

    Args:
        action_name (str): suffix for .pym file
        mode (str, optional): mode passed to `open`. Defaults to 'r'.

    Example:
        >>>with DataFile('something', 'w') as datafile:
        >>>    view_name = revit.active_view.Name
        >>>    datafile.dump(view_name)
        >>>with DataFile('something', 'r') as datafile:
        >>>    view_name_saved = datafile.load()
    """

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
            mlogger.warn(exception_value)

    def dump(self, value):
        """Wraps pickle.dump. Serializes data before saving (if possible)

        Args:
            value (object): data to dump
        """
        # make picklable (serialize)
        value_serialized = revit.serializable.serialize(value)
        pickle.dump(value_serialized, self.file)

    def load(self):
        """Wraps pickle.load. Deserializes data (if possible)

        Returns:
            object: deserialized data
        """
        # unpickle (deserialize)
        value_serialized = pickle.load(self.file)
        return revit.serializable.deserialize(value_serialized)


class CopyPasteStateAction(object):
    """Base class for creating Copy/Paste State Actions.

    Example:
        >>>@copy_paste_action
        >>>class ViewScale(CopyPasteStateAction):
        >>>    name = 'View Scale'
        >>>
        >>>def copy(self, datafile):
        >>>    view_scale = revit.active_view.Scale
        >>>    datafile.dump(view_scale)
        >>>
        >>>def paste(self, datafile):
        >>>    view_scale_saved = datafile.load()
        >>>    revit.active_view.Scale = view_scale_saved
        >>>
        >>>@staticmethod
        >>>def validate_context():
        >>>    if not isinstance(revit.active_view, DB.TableView):
        >>>        return "Geometrical view must be active. Not a schedule."

    Usage:
        >>>if not ViewScale.validate_context():
        >>>   view_scale_action = ViewScale()
        >>>   view_scale_action.copy()
        ...
        >>>view_scale_action.paste()
    """
    name = '-'

    def copy(self, datafile):
        """Performs copy action.

        Args:
            datafile (DataFile): instance of DataFile in `write` mode

        Example:
            >>>def copy(self, datafile):
            >>>    view_scale = revit.active_view.Scale
            >>>    datafile.dump(view_scale)
        """
        pass

    def paste(self, datafile):
        """Performs paste action.

        Args:
            datafile (DataFile): instance of DataFile in `read` mode

        Example:
            >>>def paste(self, datafile):
            >>>    view_scale_saved = datafile.load()
            >>>    with revit.Transacction('Paste view scale'):
            >>>        try:
            >>>            revit.active_view.Scale = view_scale_saved
            >>>        except:
            >>>            raise Exception('Cannot paste view scale')
        """
        pass

    @staticmethod
    def validate_context():
        """Validating context before running the action. E.g. if certain view
        type must be active, certail element type selected.
        To be run 'silently', therefore should contain no ui or forms.

        Returns:
            str: message describing the failure; None if validation successful

        Example:
            >>>@staticmethod
            >>>def validate_context():
            >>>    if not isinstance(revit.active_view, DB.TableView):
            >>>        return "Geometrical view must be active. Not a schedule."
        """
        return

    def copy_wrapper(self):
        """A method to trigger `copy`, wraps it with `DataFile`
        """
        with DataFile(self.__class__.__name__, 'w') as datafile:
            try:
                self.copy(datafile)
                return True
            except IOError:
                forms.alert('Cannot save data')
            except Exception as exc:
                forms.alert('Error:\n{}'.format(exc))
            return False

    def paste_wrapper(self):
        """A method to trigger `paste`, wraps it with `DataFile`.
        Validates context before paste and alert on failure.

        Returns:
            bool: True on success
        """
        # pylint: disable=assignment-from-none
        validate_msg = self.validate_context()
        if validate_msg:
            forms.alert(validate_msg)
            return False
        else:
            with DataFile(self.__class__.__name__, 'r') as datafile:
                try:
                    self.paste(datafile)
                    return True
                except IOError:
                    forms.alert('Cannot load data')
                except Exception as exc:
                    forms.alert('Error:\n{}'.format(exc))
            return False


# available actions

@copy_paste_action
class ViewZoomPanState(CopyPasteStateAction):
    name = 'View Zoom/Pan State'

    def copy(self, datafile):
        datafile.dump(type(revit.active_view).__name__)
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        corner_list = active_ui_view.GetZoomCorners()
        datafile.dump(corner_list)
        # dump ViewOrientation3D to compare with target view
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
            if not almost_equal(angle, math.pi) and not almost_equal(angle, 0):
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
        datafile.dump(revit.active_view.Id)

    def paste(self, datafile):
        e_id = datafile.load()
        with revit.Transaction('Paste Visibility Graphics'):
            revit.active_view.ApplyViewTemplateParameters(
                revit.doc.GetElement(e_id))

    @staticmethod
    def validate_context():
        if isinstance(revit.active_view, (DB.ViewSheet, DB.ViewSchedule)):
            return "View does not support Visibility Graphics settings"

@copy_paste_action
class CropRegion(CopyPasteStateAction):
    name = 'Crop Region'

    @staticmethod
    def is_cropable(view):
        """Check if view can be cropped"""
        return not isinstance(view, (DB.ViewSheet, DB.TableView)) \
            and view.ViewType not in (DB.ViewType.Legend,
                                      DB.ViewType.DraftingView)

    def copy(self, datafile):
        view = get_views(filter_func=CropRegion.is_cropable)[0]
        curve_loops = get_crop_region(view)
        if curve_loops:
            datafile.dump(curve_loops)
        else:
            raise Exception('Cannot read crop region of selected view')

    def paste(self, datafile):
        crv_loops = datafile.load()
        with revit.Transaction('Paste Crop Region') as t:
            for view in CropRegion.get_views():
                set_crop_region(view, crv_loops)

        revit.uidoc.RefreshActiveView()

    @staticmethod
    def validate_context():
        if not get_views(filter_func=CropRegion.is_cropable):
            return "Activate a view or select at least one cropable viewport"


@copy_paste_action
class ViewportPlacement(CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'

    @staticmethod
    def calculate_offset(view, saved_offset, alignment):
        """For usage in 'align by viewport corners' mode.
        Calculates XY-distance between viewport center and specified corner.

        Args:
            view (DB.View): [description]
            saved_offset (DB.UV): [description]
            alignment (str): alignment name (e.g. 'Top Left')

        Returns:
            DB.XYZ: distance between vp-center and specified corner
        """
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
        """Modifies `new_center` so only one of axises will be changed
         in comparison with `viewport` center.

        Args:
            viewport (DB.Viewport): viewport to compare with
            new_center (DB.XYZ): a point to modify
            mode (str, optional): 'X' or 'Y'. Defaults to None.

        Returns:
            DB.XYZ: modified point
        """
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
        """Hides all elements visible in provided view.

        Args:
            view (DB.View): view to search on

        Returns:
            list[DB.ElementId]: list of hidden element ids
        """
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
    def unhide_elements(view, element_ids):
        """Unhide elements in a view

        Args:
            view (DB.View): view to apply visibility changes
            element_ids (list[DB.ElementId]): list of element ids to unhide
        """
        if element_ids:
            try:
                view.UnhideElements(List[DB.ElementId](element_ids))
            except Exception as exc:
                mlogger.warn(exc)

    @staticmethod
    def activate_cropbox(view):
        """Make cropbox active and visible in a view
        Args:
            view (DB.View): view to apply changes

        Returns:
            (bool, bool, int): previous values of CropBoxActive, CropBoxVisible
                               and "Annotation Crop Active"
        """
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
        """Recovers saved cropbox visibility

        Args:
            view (DB.View): view to apply changes
            saved_values ((bool, bool, int)): saved values of CropBoxActive,
                CropBoxVisible and "Annotation Crop Active"
        """
        saved_active, saved_visible, saved_annotations = saved_values
        cboxannoparam = view.get_Parameter(
            DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        view.CropBoxActive = saved_active
        view.CropBoxVisible = saved_visible
        if not cboxannoparam.IsReadOnly:
            cboxannoparam.Set(saved_annotations)

    @staticmethod
    def get_title_block_placement(viewport):
        """Search for a TitleBlock on a viewport sheet.
        Returns TitleBlock location on sheet if there is exactly one.

        Args:
            viewport (DB.Viewport): viewport to get sheet from

        Returns:
            DB.XYZ: TitleBlock location or DB.XYZ.Zero
        """
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
        """Generates a rectangular curve loop in model coordinates
        (0,0; 0,1; 1,1; 1,0) parallel to a provided view.

        Args:
            view (DB.View): view, to which the curves should be projected

        Returns:
            DB.CurveLoop: result curve loop
        """
        # model points (lower left and upper right corners)
        p1 = DB.XYZ(0, 0, 0)
        p3 = DB.XYZ(1, 1, 1)
        # uv's of model points projected to a view
        uv1 = project_to_viewport(p1, view)
        uv3 = project_to_viewport(p3, view)
        # uv's of upper left and lower right corners of rectangle
        uv2 = DB.UV(uv1.U, uv3.V)
        uv4 = DB.UV(uv3.U, uv1.V)
        # project all points back to model coordinates
        p2 = project_to_world(uv2, view)
        p4 = project_to_world(uv4, view)
        p1 = project_to_world(project_to_viewport(p1, view), view)
        p3 = project_to_world(project_to_viewport(p3, view), view)
        # create lines between points
        l1 = DB.Line.CreateBound(p1, p2)
        l2 = DB.Line.CreateBound(p2, p3)
        l3 = DB.Line.CreateBound(p3, p4)
        l4 = DB.Line.CreateBound(p4, p1)
        # generate curve loop
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
            corner_alignment = forms.CommandSwitchWindow.show(
                [ALIGNMENT_CENTER, ALIGNMENT_TOP_LEFT, ALIGNMENT_TOP_RIGHT,
                 ALIGNMENT_BOTTOM_RIGHT, ALIGNMENT_BOTTOM_LEFT],
                message='Select alignment')

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
                            set_crop_region(
                                view, ViewportPlacement.zero_cropbox(view))
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
                        ViewportPlacement.recover_cropbox(
                            view, cropbox_values_current)
                if hidden_elements:
                    with revit.Transaction('Recover hidden elements'):
                        ViewportPlacement.unhide_elements(
                            view, hidden_elements)

    @staticmethod
    def validate_context():
        if not get_selected_viewports():
            return 'At least one viewport must be selected'


@copy_paste_action
class FilterOverrides(CopyPasteStateAction):
    name = 'Filter Overrides'

    @staticmethod
    def get_view_filters(view):
        view_filters = []
        for filter_id in view.GetFilters():
            filter_element = view.Document.GetElement(filter_id)
            view_filters.append(filter_element)
        return view_filters

    @staticmethod
    def controlled_by_template(view):
        if view.ViewTemplateId != DB.ElementId.InvalidElementId:
            view_template = view.Document.GetElement(view.ViewTemplateId)
            non_controlled_params = view_template \
                .GetNonControlledTemplateParameterIds()
            # check if filters are controlled by template
            if DB.ElementId(int(DB.BuiltInParameter.VIS_GRAPHICS_FILTERS)) \
                    not in non_controlled_params:
                return True
        return False

    def copy(self, datafile):
        view = get_views()[0]
        view_filters = FilterOverrides.get_view_filters(view)
        if not view_filters:
            raise Exception('Active view has no fitlers applied')
        selected_filters = forms.SelectFromList.show(
            view_filters,
            name_attr='Name',
            title='Select filters to copy',
            button_name='Select filters',
            multiselect=True
        )
        if not selected_filters:
            raise 'No filters selected. Cancelled.'        
        datafile.dump(view.Id)
        filter_ids = [f.Id for f in view_filters]
        datafile.dump(filter_ids)

    def paste(self, datafile):
        source_view_id = datafile.load()
        source_view = revit.doc.GetElement(source_view_id)
        source_filter_ids = datafile.load()
        # to view template or to selected view
        mode_templates = forms.CommandSwitchWindow.show(
            ['Active/selected Views', 'Select Templates'],
            message='Where do you want to paste filters?') == 'Select Templates'
        if mode_templates:
            views = forms.select_viewtemplates()
        else:
            views = get_views()
            views_controlled_by_template = [view for view in views
                                            if FilterOverrides\
                                                .controlled_by_template(view)]
            if views_controlled_by_template:
                forms.alert('You have selected views with template applied.'\
                    ' They will be skipped')
        if not views:
            raise Exception('Nothing selected')

        # check if there are views controlled by template
        with revit.TransactionGroup('Paste Filter Overrides'):
            for view in views:
                with revit.Transaction('Paste filter'):
                    # check if filters are controlled by template
                    if FilterOverrides.controlled_by_template(view):
                        mlogger.warn('Skip view \'{}\''.format(
                            revit.query.get_name(view)))
                        continue

                    view_filters_ids = view.GetFilters()
                    for filter_id in source_filter_ids:
                        # remove filter override if exists
                        if filter_id in view_filters_ids:
                            view.RemoveFilter(filter_id)
                        # add new fitler override
                        filter_overrides = source_view.GetFilterOverrides(
                            filter_id)
                        view.SetFilterOverrides(filter_id, filter_overrides)
