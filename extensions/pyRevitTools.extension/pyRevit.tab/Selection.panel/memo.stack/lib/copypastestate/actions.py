"""Copy/Paste State Actions"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import math

from pyrevit import PyRevitException
from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit.coreutils import logger
from pyrevit.coreutils import moduleutils
from pyrevit.coreutils import pyutils
from pyrevit import forms
from pyrevit import script

from copypastestate import basetypes


mlogger = logger.get_logger(__name__)


# =============================================================================


class ViewZoomPanStateData(object):
    def __init__(self, view_type, corner_pts, dir_orient):
        self._view_type = revit.serialize(view_type)
        self._corner_pts = [revit.serialize(x) for x in corner_pts]
        self._dir_orient = revit.serialize(dir_orient)

    @property
    def view_type(self):
        return self._view_type.deserialize()

    @property
    def corner_pts(self):
        return [x.deserialize() for x in self._corner_pts]

    @property
    def dir_orient(self):
        return self._dir_orient.deserialize()


@moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
class ViewZoomPanStateAction(basetypes.CopyPasteStateAction):
    name = 'View Zoom/Pan State'
    invalid_context_msg = "Type of active view is not supported"

    def copy(self):
        active_view = revit.active_view
        active_ui_view = revit.uidoc.GetOpenUIViews()[0]

        dir_orient = None
        if isinstance(revit.active_view, DB.View3D):
            dir_orient = revit.active_view.GetOrientation()
        elif isinstance(revit.active_view, DB.ViewSection):
            dir_orient = revit.active_view.ViewDirection

        script.store_data(
            slot_name=self.__class__.__name__,
            data=ViewZoomPanStateData(
                view_type=active_view.ViewType,
                corner_pts=active_ui_view.GetZoomCorners(),
                dir_orient=dir_orient
            )
        )

    def paste(self):
        # load data
        vzps_data = script.load_data(slot_name=self.__class__.__name__)

        view_type = vzps_data.view_type
        vc1, vc2 = vzps_data.corner_pts
        dir_orient = vzps_data.dir_orient

        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        if revit.active_view.ViewType == view_type:
            raise PyRevitException(
                'Saved view type (%s) is different from active view (%s)'
                % (vzps_data.view_type, type(revit.active_view).__name__))
        # load ViewOrientation3D
        if isinstance(revit.active_view, DB.View3D):
            if revit.active_view.IsLocked:
                raise PyRevitException('Current view orientation is locked')
            revit.active_view.SetOrientation(dir_orient)
        elif isinstance(revit.active_view, DB.ViewSection):
            angle = dir_orient.AngleTo(revit.active_view.ViewDirection)
            if not pyutils.almost_equal(angle, math.pi) \
                    and not pyutils.almost_equal(angle, 0):
                raise PyRevitException("Views are not parallel")
        active_ui_view.ZoomAndCenterRectangle(vc1, vc2)

    @staticmethod
    def validate_context():
        return revit.get_selection().is_empty \
            and isinstance(
                revit.active_view,
                (
                    DB.ViewPlan,
                    DB.ViewSection,
                    DB.View3D,
                    DB.ViewSheet,
                    DB.ViewDrafting
                ))


# =============================================================================


class SectionBox3DStateData(object):
    def __init__(self, section_box, view_orientation):
        self._section_box = revit.serialize(section_box)
        self._view_orientation = revit.serialize(view_orientation)

    @property
    def section_box(self):
        return self._section_box.deserialize()

    @property
    def view_orientation(self):
        return self._view_orientation.deserialize()


@moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
class SectionBox3DStateAction(basetypes.CopyPasteStateAction):
    name = '3D Section Box State'
    invalid_context_msg = \
        "You must be on a 3D view to copy and paste 3D section box."

    def copy(self):
        section_box = revit.active_view.GetSectionBox()
        view_orientation = revit.active_view.GetOrientation()

        script.store_data(
            slot_name=self.__class__.__name__,
            data=SectionBox3DStateData(
                section_box=section_box,
                view_orientation=view_orientation
            )
        )

    def paste(self):
        sb3d_data = script.load_data(slot_name=self.__class__.__name__)

        active_ui_view = revit.uidoc.GetOpenUIViews()[0]
        with revit.Transaction('Paste Section Box Settings'):
            revit.active_view.SetSectionBox(sb3d_data.section_box)
            revit.active_view.SetOrientation(sb3d_data.view_orientation)
        active_ui_view.ZoomToFit()

    @staticmethod
    def validate_context():
        return isinstance(revit.active_view, DB.View3D)


# =============================================================================


class VisibilityGraphicsData(object):
    def __init__(self, source_viewid):
        self._source_viewid = revit.serialize(source_viewid)

    @property
    def source_viewid(self):
        return self._source_viewid.deserialize()


@moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
class VisibilityGraphicsAction(basetypes.CopyPasteStateAction):
    name = 'Visibility Graphics'
    invalid_context_msg = "View does not support Visibility Graphics settings"

    def copy(self):
        script.store_data(
            slot_name=self.__class__.__name__,
            data=VisibilityGraphicsData(
                source_viewid=revit.active_view.Id,
            )
        )

    def paste(self):
        vg_data = script.load_data(slot_name=self.__class__.__name__)
        with revit.Transaction('Paste Visibility Graphics'):
            revit.active_view.ApplyViewTemplateParameters(
                revit.doc.GetElement(vg_data.source_viewid))

    @staticmethod
    def validate_context():
        return revit.get_selection().is_empty \
            and not isinstance(revit.active_view,
                               (DB.ViewSheet, DB.ViewSchedule))


# =============================================================================


class CropRegionData(object):
    def __init__(self, cropregion_curveloop, is_active):
        self._cropregion_curveloop = revit.serialize(cropregion_curveloop)
        self._is_active = is_active

    @property
    def cropregion_curveloop(self):
        return self._cropregion_curveloop.deserialize()

    @property
    def is_active(self):
        return self._is_active


# TODO: correct so split crop regions can be copied as well
@moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
class CropRegionAction(basetypes.CopyPasteStateAction):
    name = 'Crop Region'
    invalid_context_msg = \
        "Activate a view or select at least one cropable viewport"

    @staticmethod
    def get_cropable_views():
        # py3 returns a filter object but py3 returns filtered list
        # list() makes it consistent
        # py2 filter does not support keyword arguments
        selected_views = revit.get_selection().only_views()
        if not selected_views:
            selected_views = [revit.active_view]
        return list(filter(revit.query.is_cropable_view, selected_views))

    @staticmethod
    def get_first_cropable_view():
        views = CropRegionAction.get_cropable_views()
        if views:
            return views[0]

    def copy(self):
        view = CropRegionAction.get_first_cropable_view()

        cropregion_curve_loops = revit.query.get_crop_region(view)
        if cropregion_curve_loops:
            script.store_data(
                slot_name=self.__class__.__name__,
                data=CropRegionData(
                    cropregion_curveloop=cropregion_curve_loops[0],
                    is_active=view.CropBoxActive
                )
            )
        else:
            raise PyRevitException(
                'Cannot read crop region of selected view'
                )

    def paste(self):
        cr_data = script.load_data(slot_name=self.__class__.__name__)
        crv_loop = cr_data.cropregion_curveloop
        with revit.Transaction('Paste Crop Region'):
            for view in CropRegionAction.get_cropable_views():
                revit.update.set_crop_region(view, crv_loop)
                view.CropBoxActive = cr_data.is_active
        revit.uidoc.RefreshActiveView()

    @staticmethod
    def validate_context():
        return CropRegionAction.get_first_cropable_view()


# =============================================================================


ALIGNMENT_CROPBOX = 'Align to CROP BOX CORNER on Paste'
ALIGNMENT_BASEPOINT = 'Align to BASE POINT on Paste'

ALIGNMENT_OPTIONS_COPY = [
    ALIGNMENT_CROPBOX,
    ALIGNMENT_BASEPOINT,
    ]

ALIGNMENT_CENTER = 'Align to CENTER of Copied Crop Box'
ALIGNMENT_TOP_LEFT = 'Align to TOP LEFT Corner of Copied Crop Box'
ALIGNMENT_TOP_RIGHT = 'Align to TOP RIGHT Corner of Copied Crop Box'
ALIGNMENT_BOTTOM_LEFT = 'Align to BOTTOM LEFT Corner of Copied Crop Box'
ALIGNMENT_BOTTOM_RIGHT = 'Align to BOTTOM RIGHT Corner of Copied Crop Box'

ALIGNMENT_OPTIONS = [
    ALIGNMENT_CENTER,
    ALIGNMENT_TOP_LEFT,
    ALIGNMENT_TOP_RIGHT,
    ALIGNMENT_BOTTOM_LEFT,
    ALIGNMENT_BOTTOM_RIGHT,
    ]


class ViewportPlacementData(object):
    def __init__(self, alignment, center, offset_uv):
        self._alignment = alignment
        self._center = revit.serialize(center)
        self._offset_uv = revit.serialize(offset_uv)

    @property
    def alignment(self):
        return self._alignment

    @property
    def center(self):
        return self._center.deserialize()

    @property
    def offset_uv(self):
        return self._offset_uv.deserialize()


@moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
class ViewportPlacementAction(basetypes.CopyPasteStateAction):
    name = 'Viewport Placement on Sheet'
    invalid_context_msg = "At least one viewport must be selected"

    @staticmethod
    def calculate_offset(view, offset_uv, alignment):
        """For usage in 'align by viewport corners' mode.
        Calculates XY-distance between viewport center and specified corner.

        Args:
            view (DB.View): [description]
            offset_uv (DB.UV): [description]
            alignment (str): alignment name (e.g. 'Top Left')

        Returns:
            DB.XYZ: distance between vp-center and specified corner
        """
        if alignment == ALIGNMENT_CENTER:
            return DB.XYZ.Zero
        else:
            outline = view.Outline
            current_offset = (outline.Max - outline.Min) / 2
            offset_uv = offset_uv - current_offset
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
        uv1 = revit.units.project_to_viewport(p1, view)
        uv3 = revit.units.project_to_viewport(p3, view)
        # uv's of upper left and lower right corners of rectangle
        uv2 = DB.UV(uv1.U, uv3.V)
        uv4 = DB.UV(uv3.U, uv1.V)
        # project all points back to model coordinates
        p2 = revit.units.project_to_world(uv2, view)
        p4 = revit.units.project_to_world(uv4, view)
        p1 = revit.units.project_to_world(
            revit.units.project_to_viewport(p1, view),
            view
            )
        p3 = revit.units.project_to_world(
            revit.units.project_to_viewport(p3, view),
            view
            )
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

    def copy(self):
        viewports = revit.get_selection().include(DB.Viewport)
        if len(viewports) != 1:
            raise Exception('Exactly one viewport must be selected')
        viewport = viewports[0]
        view = revit.doc.GetElement(viewport.ViewId)

        title_block_pt = \
            ViewportPlacementAction.get_title_block_placement(viewport)

        if view.ViewType in [DB.ViewType.DraftingView, DB.ViewType.Legend]:
            alignment = ALIGNMENT_CROPBOX
        else:
            alignment = forms.CommandSwitchWindow.show(
                ALIGNMENT_OPTIONS_COPY,
                message='Select Alignment Option')

        if not alignment:
            return

        with revit.DryTransaction('Activate & Read Cropbox, Copy Center'):
            if alignment == ALIGNMENT_BASEPOINT:
                revit.update.set_crop_region(
                    view,
                    ViewportPlacementAction.zero_cropbox(view)
                    )
            # use cropbox as alignment if it active
            if alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
                ViewportPlacementAction.activate_cropbox(view)
                ViewportPlacementAction.hide_all_elements(view)
                revit.doc.Regenerate()

            if alignment == ALIGNMENT_CROPBOX:
                outline = view.Outline
                offset_uv = (outline.Max - outline.Min) / 2
            center = viewport.GetBoxCenter() - title_block_pt

        script.store_data(
            slot_name=self.__class__.__name__,
            data=ViewportPlacementData(
                alignment=alignment,
                center=center,
                offset_uv=offset_uv if alignment == ALIGNMENT_CROPBOX else None
            )
        )

    def paste(self):
        vp_data = script.load_data(slot_name=self.__class__.__name__)

        viewports = revit.get_selection().include(DB.Viewport)
        align_axis = None
        if __shiftclick__:  # pylint: disable=undefined-variable
            align_axis = forms.CommandSwitchWindow.show(
                ['X', 'Y', 'XY'],
                message='Align specific axis?')
        # read saved values
        alignment = vp_data.alignment
        center = vp_data.center
        offset_uv = vp_data.offset_uv
        if alignment == ALIGNMENT_CROPBOX:
            corner_alignment = forms.CommandSwitchWindow.show(
                ALIGNMENT_OPTIONS,
                message='Select Alignment Option'
                )

        with revit.TransactionGroup('Paste Viewport Location'):
            for viewport in viewports:
                view = revit.doc.GetElement(viewport.ViewId)
                title_block_pt = \
                    ViewportPlacementAction.get_title_block_placement(viewport)
                crop_region_current = None
                cropbox_values_current = None
                hidden_elements = None
                # set temporary settings: hide elements, set cropbox visibility
                #  if cropbox is not active, do nothing (use visible elements)
                if alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
                    with revit.Transaction('Temporary settings'):
                        # 'base point' mode - set cropbox to 'zero' temporary
                        if alignment == ALIGNMENT_BASEPOINT:
                            crop_region_current = revit.query.get_crop_region(view)
                            revit.update.set_crop_region(
                                view, ViewportPlacementAction.zero_cropbox(view)
                                )
                        cropbox_values_current = \
                            ViewportPlacementAction.activate_cropbox(view)
                        hidden_elements = \
                            ViewportPlacementAction.hide_all_elements(view)

                with revit.Transaction('Apply Viewport Placement'):
                    new_center = center
                    # 'crop box' mode - align to vp corner if necessary
                    if alignment == ALIGNMENT_CROPBOX \
                            and corner_alignment:
                        offset_xyz = ViewportPlacementAction.calculate_offset(
                            view, offset_uv, corner_alignment)
                        new_center += offset_xyz
                    # isolate alignment by x- or y-axis if necessary
                    new_center = ViewportPlacementAction.isolate_axis(
                        viewport, new_center, align_axis)
                    # apply new viewport position
                    viewport.SetBoxCenter(new_center + title_block_pt)
                # unset temporary values
                if crop_region_current:
                    with revit.Transaction('Recover crop region form'):
                        revit.update.set_crop_region(view, crop_region_current)
                if cropbox_values_current:
                    with revit.Transaction('Recover crop region values'):
                        ViewportPlacementAction.recover_cropbox(
                            view,
                            cropbox_values_current
                            )
                if hidden_elements:
                    with revit.Transaction('Recover hidden elements'):
                        ViewportPlacementAction.unhide_elements(
                            view,
                            hidden_elements
                            )

    @staticmethod
    def validate_context():
        return revit.get_selection().include(DB.Viewport)


# =============================================================================


class FilterOverridesData(object):
    def __init__(self, source_viewid, filter_ids):
        self._source_viewid = revit.serialize(source_viewid)
        self._filter_ids = [revit.serialize(x) for x in filter_ids]

    @property
    def source_viewid(self):
        return self._source_viewid.deserialize()

    @property
    def filter_ids(self):
        return [x.deserialize() for x in self._filter_ids]


@moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
class FilterOverridesAction(basetypes.CopyPasteStateAction):
    name = 'Filter Overrides'
    invalid_context_msg = ""

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

    def copy(self):
        views = revit.get_selection().only_views()
        if views:
            view = views[0]
            view_filters = revit.query.get_view_filters(view)
            if not view_filters:
                raise PyRevitException('Active view has no fitlers applied')

            selected_filters = forms.SelectFromList.show(
                view_filters,
                name_attr='Name',
                title='Select filters to copy',
                button_name='Select filters',
                multiselect=True
            )

            if not selected_filters:
                raise PyRevitException('No filters selected. Cancelled.')

            script.store_data(
                slot_name=self.__class__.__name__,
                data=FilterOverridesData(
                    source_viewid=view.Id,
                    filter_ids=[f.Id for f in view_filters]
                )
            )

    def paste(self):
        fo_data = script.load_data(slot_name=self.__class__.__name__)

        source_view = revit.doc.GetElement(fo_data.source_viewid)
        source_filter_ids = fo_data.filter_ids

        # to view template or to selected view
        mode_templates = \
            forms.CommandSwitchWindow.show(
                ['Active View', 'Select View Templates'],
                message='Where do you want to paste filters?'
                ) == 'Select Templates'
        if mode_templates:
            views = forms.select_viewtemplates()
        else:
            views = [revit.active_view]
            views_controlled_by_template = \
                [x for x in views
                 if FilterOverridesAction.controlled_by_template(x)]
            if views_controlled_by_template:
                forms.alert(
                    'You have selected views with template applied.'
                    ' They will be skipped'
                    )
        if not views:
            raise PyRevitException('Nothing selected')

        # check if there are views controlled by template
        with revit.TransactionGroup('Paste Filter Overrides'):
            for view in views:
                with revit.Transaction('Paste filter'):
                    # check if filters are controlled by template
                    if FilterOverridesAction.controlled_by_template(view):
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

    @staticmethod
    def validate_context():
        return revit.get_selection().is_empty
