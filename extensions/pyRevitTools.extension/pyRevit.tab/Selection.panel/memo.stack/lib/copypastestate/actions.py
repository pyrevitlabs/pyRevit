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
from copypastestate import utils


mlogger = logger.get_logger(__name__)


ALIGNMENT_CROPBOX = 'Crop Box'
ALIGNMENT_BASEPOINT = 'Project Base Point'
ALIGNMENT_BOTTOM_LEFT = 'Bottom Left'
ALIGNMENT_BOTTOM_RIGHT = 'Bottom Right'
ALIGNMENT_TOP_LEFT = 'Top Left'
ALIGNMENT_TOP_RIGHT = 'Top Right'
ALIGNMENT_CENTER = 'Center'


class ViewZoomPanStateActionData(object):
    def __init__(self, view_type, corner_pts, dir_orient):
        self.view_type = revit.serialize(view_type)
        self.corner_pts = revit.serialize(corner_pts)
        self.dir_orient = revit.serialize(dir_orient)


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

        script.memorize(
            slot_name=self.__class__.__name__,
            data=ViewZoomPanStateActionData(
                view_type=active_view.ViewType,
                corner_pts=active_ui_view.GetZoomCorners(),
                dir_orient=dir_orient
            )
        )

    def paste(self):
        # load data
        vzps_data = script.remember(slot_name=self.__class__.__name__)
        view_type = vzps_data.view_type.deserialize()
        vc1, vc2 = [x.deserialize() for x in vzps_data.corner_pts]
        dir_orient = vzps_data.dir_orient.deserialize()

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
        return isinstance(
            revit.active_view,
            (
                DB.ViewPlan,
                DB.ViewSection,
                DB.View3D,
                DB.ViewSheet,
                DB.ViewDrafting
            ))


# @moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
# class SectionBox3DState(basetypes.CopyPasteStateAction):
#     name = '3D Section Box State'
#     invalid_context_msg = \
#         "You must be on a 3D view to copy and paste 3D section box."

#     def copy(self):
#         section_box = revit.active_view.GetSectionBox()
#         view_orientation = revit.active_view.GetOrientation()
#         datafile.dump(section_box)
#         datafile.dump(view_orientation)

#     def paste(self):
#         section_box = datafile.load()
#         view_orientation = datafile.load()
#         active_ui_view = revit.uidoc.GetOpenUIViews()[0]
#         with revit.Transaction('Paste Section Box Settings'):
#             revit.active_view.SetSectionBox(section_box)
#             revit.active_view.SetOrientation(view_orientation)
#         active_ui_view.ZoomToFit()

#     @staticmethod
#     def validate_context():
#         return isinstance(revit.active_view, DB.View3D)


# @moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
# class VisibilityGraphics(basetypes.CopyPasteStateAction):
#     name = 'Visibility Graphics'
#     invalid_context_msg = "View does not support Visibility Graphics settings"

#     def copy(self):
#         datafile.dump(revit.active_view.Id)

#     def paste(self):
#         e_id = datafile.load()
#         with revit.Transaction('Paste Visibility Graphics'):
#             revit.active_view.ApplyViewTemplateParameters(
#                 revit.doc.GetElement(e_id))

#     @staticmethod
#     def validate_context():
#         return not isinstance(
#             revit.active_view,
#             (DB.ViewSheet, DB.ViewSchedule)
#             )


# @moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
# class CropRegion(basetypes.CopyPasteStateAction):
#     name = 'Crop Region'
#     invalid_context_msg = \
#         "Activate a view or select at least one cropable viewport"

#     @staticmethod
#     def is_cropable(view):
#         """Check if view can be cropped"""
#         return not isinstance(view, (DB.ViewSheet, DB.TableView)) \
#             and view.ViewType not in (DB.ViewType.Legend,
#                                       DB.ViewType.DraftingView)

#     def copy(self):
#         view = utils.get_views(filter_func=CropRegion.is_cropable)[0]
#         curve_loops = utils.get_crop_region(view)
#         if curve_loops:
#             datafile.dump(curve_loops)
#         else:
#             raise PyRevitException(
#                 'Cannot read crop region of selected view'
#                 )

#     def paste(self):
#         crv_loops = datafile.load()
#         with revit.Transaction('Paste Crop Region'):
#             for view in utils.get_views():
#                 utils.set_crop_region(view, crv_loops)
#         revit.uidoc.RefreshActiveView()

#     @staticmethod
#     def validate_context():
#         return utils.get_views(filter_func=CropRegion.is_cropable) 


# @moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
# class ViewportPlacement(basetypes.CopyPasteStateAction):
#     name = 'Viewport Placement on Sheet'
#     invalid_context_msg = "At least one viewport must be selected"

#     @staticmethod
#     def calculate_offset(view, saved_offset, alignment):
#         """For usage in 'align by viewport corners' mode.
#         Calculates XY-distance between viewport center and specified corner.

#         Args:
#             view (DB.View): [description]
#             saved_offset (DB.UV): [description]
#             alignment (str): alignment name (e.g. 'Top Left')

#         Returns:
#             DB.XYZ: distance between vp-center and specified corner
#         """
#         if alignment == ALIGNMENT_CENTER:
#             return DB.XYZ.Zero
#         else:
#             outline = view.Outline
#             current_offset = (outline.Max - outline.Min) / 2
#             offset_uv = saved_offset - current_offset
#             if alignment == ALIGNMENT_TOP_LEFT:
#                 return DB.XYZ(-offset_uv.U, offset_uv.V, 0)
#             elif alignment == ALIGNMENT_TOP_RIGHT:
#                 return DB.XYZ(offset_uv.U, offset_uv.V, 0)
#             elif alignment == ALIGNMENT_BOTTOM_RIGHT:
#                 return DB.XYZ(offset_uv.U, -offset_uv.V, 0)
#             elif alignment == ALIGNMENT_BOTTOM_LEFT:
#                 return DB.XYZ(-offset_uv.U, -offset_uv.V, 0)

#     @staticmethod
#     def isolate_axis(viewport, new_center, mode=None):
#         """Modifies `new_center` so only one of axises will be changed
#          in comparison with `viewport` center.

#         Args:
#             viewport (DB.Viewport): viewport to compare with
#             new_center (DB.XYZ): a point to modify
#             mode (str, optional): 'X' or 'Y'. Defaults to None.

#         Returns:
#             DB.XYZ: modified point
#         """
#         if mode in ('X', 'Y'):
#             current_center = viewport.GetBoxCenter()
#             if mode == 'X':
#                 return DB.XYZ(new_center.X, current_center.Y, 0)
#             else:
#                 return DB.XYZ(current_center.X, new_center.Y, 0)
#         else:
#             return new_center

#     @staticmethod
#     def hide_all_elements(view):
#         """Hides all elements visible in provided view.

#         Args:
#             view (DB.View): view to search on

#         Returns:
#             list[DB.ElementId]: list of hidden element ids
#         """
#         # hide all elements in the view
#         cl_view_elements = DB.FilteredElementCollector(view.Document, view.Id) \
#             .WhereElementIsNotElementType()
#         elements_to_hide = [el.Id for el in cl_view_elements.ToElements()
#                             if not el.IsHidden(view) and el.CanBeHidden(view)]
#         if elements_to_hide:
#             try:
#                 view.HideElements(List[DB.ElementId](elements_to_hide))
#             except Exception as exc:
#                 mlogger.warn(exc)
#         return elements_to_hide

#     @staticmethod
#     def unhide_elements(view, element_ids):
#         """Unhide elements in a view

#         Args:
#             view (DB.View): view to apply visibility changes
#             element_ids (list[DB.ElementId]): list of element ids to unhide
#         """
#         if element_ids:
#             try:
#                 view.UnhideElements(List[DB.ElementId](element_ids))
#             except Exception as exc:
#                 mlogger.warn(exc)

#     @staticmethod
#     def activate_cropbox(view):
#         """Make cropbox active and visible in a view
#         Args:
#             view (DB.View): view to apply changes

#         Returns:
#             (bool, bool, int): previous values of CropBoxActive, CropBoxVisible
#                                and "Annotation Crop Active"
#         """
#         cboxannoparam = view.get_Parameter(
#             DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
#         current_active = view.CropBoxActive
#         current_visible = view.CropBoxVisible
#         current_annotations = cboxannoparam.AsInteger()
#         # making sure the cropbox is active.
#         view.CropBoxActive = True
#         view.CropBoxVisible = True
#         if not cboxannoparam.IsReadOnly:
#             cboxannoparam.Set(0)
#         return current_active, current_visible, current_annotations

#     @staticmethod
#     def recover_cropbox(view, saved_values):
#         """Recovers saved cropbox visibility

#         Args:
#             view (DB.View): view to apply changes
#             saved_values ((bool, bool, int)): saved values of CropBoxActive,
#                 CropBoxVisible and "Annotation Crop Active"
#         """
#         saved_active, saved_visible, saved_annotations = saved_values
#         cboxannoparam = view.get_Parameter(
#             DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
#         view.CropBoxActive = saved_active
#         view.CropBoxVisible = saved_visible
#         if not cboxannoparam.IsReadOnly:
#             cboxannoparam.Set(saved_annotations)

#     @staticmethod
#     def get_title_block_placement(viewport):
#         """Search for a TitleBlock on a viewport sheet.
#         Returns TitleBlock location on sheet if there is exactly one.

#         Args:
#             viewport (DB.Viewport): viewport to get sheet from

#         Returns:
#             DB.XYZ: TitleBlock location or DB.XYZ.Zero
#         """
#         sheet = viewport.Document.GetElement(viewport.SheetId)
#         cl = DB.FilteredElementCollector(sheet.Document, sheet.Id). \
#             WhereElementIsNotElementType(). \
#             OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
#         title_blocks = cl.ToElements()
#         if len(title_blocks) == 1:
#             return title_blocks[0].Location.Point
#         else:
#             return DB.XYZ.Zero

#     @staticmethod
#     def zero_cropbox(view):
#         """Generates a rectangular curve loop in model coordinates
#         (0,0; 0,1; 1,1; 1,0) parallel to a provided view.

#         Args:
#             view (DB.View): view, to which the curves should be projected

#         Returns:
#             DB.CurveLoop: result curve loop
#         """
#         # model points (lower left and upper right corners)
#         p1 = DB.XYZ(0, 0, 0)
#         p3 = DB.XYZ(1, 1, 1)
#         # uv's of model points projected to a view
#         uv1 = utils.project_to_viewport(p1, view)
#         uv3 = utils.project_to_viewport(p3, view)
#         # uv's of upper left and lower right corners of rectangle
#         uv2 = DB.UV(uv1.U, uv3.V)
#         uv4 = DB.UV(uv3.U, uv1.V)
#         # project all points back to model coordinates
#         p2 = utils.project_to_world(uv2, view)
#         p4 = utils.project_to_world(uv4, view)
#         p1 = utils.project_to_world(utils.project_to_viewport(p1, view), view)
#         p3 = utils.project_to_world(utils.project_to_viewport(p3, view), view)
#         # create lines between points
#         l1 = DB.Line.CreateBound(p1, p2)
#         l2 = DB.Line.CreateBound(p2, p3)
#         l3 = DB.Line.CreateBound(p3, p4)
#         l4 = DB.Line.CreateBound(p4, p1)
#         # generate curve loop
#         crv_loop = DB.CurveLoop()
#         for crv in (l1, l2, l3, l4):
#             crv_loop.Append(crv)
#         return crv_loop

#     def copy(self):
#         viewports = utils.get_selected_viewports()
#         if len(viewports) != 1:
#             raise Exception('Exactly one viewport must be selected')
#         viewport = viewports[0]
#         view = revit.doc.GetElement(viewport.ViewId)

#         title_block_pt = ViewportPlacement\
#             .get_title_block_placement(viewport)

#         if view.ViewType in [DB.ViewType.DraftingView, DB.ViewType.Legend]:
#             alignment = ALIGNMENT_CROPBOX
#         else:
#             alignment = forms.CommandSwitchWindow.show(
#                 [ALIGNMENT_CROPBOX, ALIGNMENT_BASEPOINT],
#                 message='Select alignment')

#         if not alignment:
#             return

#         datafile.dump(alignment)

#         with revit.DryTransaction('Activate & Read Cropbox, Copy Center'):
#             if alignment == ALIGNMENT_BASEPOINT:
#                 utils.set_crop_region(view,
#                                         ViewportPlacement.zero_cropbox(view))
#             # use cropbox as alignment if it active
#             if alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
#                 ViewportPlacement.activate_cropbox(view)
#                 ViewportPlacement.hide_all_elements(view)
#                 revit.doc.Regenerate()

#             if alignment == ALIGNMENT_CROPBOX:
#                 outline = view.Outline
#                 offset_uv = (outline.Max - outline.Min) / 2
#             center = viewport.GetBoxCenter() - title_block_pt

#         datafile.dump(center)
#         if alignment == ALIGNMENT_CROPBOX:
#             datafile.dump(offset_uv)

#     def paste(self):
#         viewports = utils.get_selected_viewports()
#         align_axis = None
#         if __shiftclick__:  # pylint: disable=undefined-variable
#             align_axis = forms.CommandSwitchWindow.show(
#                 ['X', 'Y', 'XY'],
#                 message='Align specific axis?')
#         # read saved values
#         saved_alignment = datafile.load()
#         saved_center = datafile.load()
#         if saved_alignment == ALIGNMENT_CROPBOX:
#             saved_offset = datafile.load()
#             corner_alignment = forms.CommandSwitchWindow.show(
#                 [ALIGNMENT_CENTER, ALIGNMENT_TOP_LEFT, ALIGNMENT_TOP_RIGHT,
#                     ALIGNMENT_BOTTOM_RIGHT, ALIGNMENT_BOTTOM_LEFT],
#                 message='Select alignment')

#         with revit.TransactionGroup('Paste Viewport Location'):
#             for viewport in viewports:
#                 view = revit.doc.GetElement(viewport.ViewId)
#                 title_block_pt = ViewportPlacement \
#                     .get_title_block_placement(viewport)
#                 crop_region_current = None
#                 cropbox_values_current = None
#                 hidden_elements = None
#                 # set temporary settings: hide elements, set cropbox visibility
#                 #  if cropbox is not active, do nothing (use visible elements)
#                 if saved_alignment == ALIGNMENT_BASEPOINT or view.CropBoxActive:
#                     with revit.Transaction('Temporary settings'):
#                         # 'base point' mode - set cropbox to 'zero' temporary
#                         if saved_alignment == ALIGNMENT_BASEPOINT:
#                             crop_region_current = utils.get_crop_region(view)
#                             utils.set_crop_region(
#                                 view, ViewportPlacement.zero_cropbox(view)
#                                 )
#                         cropbox_values_current = ViewportPlacement\
#                             .activate_cropbox(view)
#                         hidden_elements = ViewportPlacement\
#                             .hide_all_elements(view)

#                 with revit.Transaction('Apply Viewport Placement'):
#                     new_center = saved_center
#                     # 'crop box' mode - align to vp corner if necessary
#                     if saved_alignment == ALIGNMENT_CROPBOX \
#                             and corner_alignment:
#                         offset_xyz = ViewportPlacement.calculate_offset(
#                             view, saved_offset, corner_alignment)
#                         new_center += offset_xyz
#                     # isolate alignment by x- or y-axis if necessary
#                     new_center = ViewportPlacement.isolate_axis(
#                         viewport, new_center, align_axis)
#                     # apply new viewport position
#                     viewport.SetBoxCenter(new_center + title_block_pt)
#                 # unset temporary values
#                 if crop_region_current:
#                     with revit.Transaction('Recover crop region form'):
#                         utils.set_crop_region(view, crop_region_current)
#                 if cropbox_values_current:
#                     with revit.Transaction('Recover crop region values'):
#                         ViewportPlacement.recover_cropbox(
#                             view, cropbox_values_current)
#                 if hidden_elements:
#                     with revit.Transaction('Recover hidden elements'):
#                         ViewportPlacement.unhide_elements(
#                             view, hidden_elements)

#     @staticmethod
#     def validate_context():
#         return utils.get_selected_viewports()


# @moduleutils.mark(basetypes.COPYPASTE_MARKER_PROPNAME)
# class FilterOverrides(basetypes.CopyPasteStateAction):
#     name = 'Filter Overrides'
#     invalid_context_msg = ""

#     @staticmethod
#     def get_view_filters(view):
#         view_filters = []
#         for filter_id in view.GetFilters():
#             filter_element = view.Document.GetElement(filter_id)
#             view_filters.append(filter_element)
#         return view_filters

#     @staticmethod
#     def controlled_by_template(view):
#         if view.ViewTemplateId != DB.ElementId.InvalidElementId:
#             view_template = view.Document.GetElement(view.ViewTemplateId)
#             non_controlled_params = view_template \
#                 .GetNonControlledTemplateParameterIds()
#             # check if filters are controlled by template
#             if DB.ElementId(int(DB.BuiltInParameter.VIS_GRAPHICS_FILTERS)) \
#                     not in non_controlled_params:
#                 return True
#         return False

#     def copy(self):
#         view = utils.get_views()[0]
#         view_filters = FilterOverrides.get_view_filters(view)
#         if not view_filters:
#             raise PyRevitException('Active view has no fitlers applied')
#         selected_filters = forms.SelectFromList.show(
#             view_filters,
#             name_attr='Name',
#             title='Select filters to copy',
#             button_name='Select filters',
#             multiselect=True
#         )
#         if not selected_filters:
#             raise PyRevitException('No filters selected. Cancelled.')

#         datafile.dump(view.Id)
#         filter_ids = [f.Id for f in view_filters]
#         datafile.dump(filter_ids)

#     def paste(self):
#         source_view_id = datafile.load()
#         source_view = revit.doc.GetElement(source_view_id)
#         source_filter_ids = datafile.load()

#         # to view template or to selected view
#         mode_templates = \
#             forms.CommandSwitchWindow.show(
#                 ['Active/selected Views', 'Select Templates'],
#                 message='Where do you want to paste filters?'
#                 ) == 'Select Templates'
#         if mode_templates:
#             views = forms.select_viewtemplates()
#         else:
#             views = utils.get_views()
#             views_controlled_by_template = \
#                 [x for x in x if FilterOverrides.controlled_by_template(x)]
#             if views_controlled_by_template:
#                 forms.alert(
#                     'You have selected views with template applied.'
#                     ' They will be skipped'
#                     )
#         if not views:
#             raise PyRevitException('Nothing selected')

#         # check if there are views controlled by template
#         with revit.TransactionGroup('Paste Filter Overrides'):
#             for view in views:
#                 with revit.Transaction('Paste filter'):
#                     # check if filters are controlled by template
#                     if FilterOverrides.controlled_by_template(view):
#                         mlogger.warn('Skip view \'{}\''.format(
#                             revit.query.get_name(view)))
#                         continue

#                     view_filters_ids = view.GetFilters()
#                     for filter_id in source_filter_ids:
#                         # remove filter override if exists
#                         if filter_id in view_filters_ids:
#                             view.RemoveFilter(filter_id)
#                         # add new fitler override
#                         filter_overrides = source_view.GetFilterOverrides(
#                             filter_id)
#                         view.SetFilterOverrides(filter_id, filter_overrides)

#     @staticmethod
#     def validate_context():
#         return True
