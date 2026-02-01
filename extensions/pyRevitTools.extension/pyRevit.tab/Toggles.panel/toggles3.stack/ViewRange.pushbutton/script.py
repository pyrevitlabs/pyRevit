# -*- coding: UTF-8 -*-

from pyrevit import script, forms, revit, HOST_APP, DB, UI
from pyrevit.revit import events
from pyrevit.framework import Convert, List, Color, SolidColorBrush
from pyrevit.compat import get_elementid_value_func
import traceback
from Autodesk.Revit.Exceptions import InvalidOperationException
from collections import OrderedDict


doc = HOST_APP.doc
uidoc = HOST_APP.uidoc
logger = script.get_logger()
output = script.get_output()

PLANES = OrderedDict([
    (DB.PlanViewPlane.TopClipPlane, ([0, 255, 0], "Top Clip Plane", "topplane")),
    (DB.PlanViewPlane.CutPlane, ([255, 0, 0], "Cut Plane", "cutplane")),
    (DB.PlanViewPlane.BottomClipPlane, ([0, 0, 255], "Bottom Clip Plane", "bottomplane")),
    (DB.PlanViewPlane.ViewDepthPlane, ([255, 127, 0], "View Depth Plane", "viewdepth")),
])

get_elementid_value = get_elementid_value_func()
INVALID_ID_VALUE = get_elementid_value(DB.ElementId.InvalidElementId)


class SimpleEventHandler(UI.IExternalEventHandler):
    def __init__(self, do_this):
        self.do_this = do_this

    def Execute(self, uiapp):
        try:
            self.do_this(uiapp)
        except InvalidOperationException:
            pass

    def GetName(self):
        return "SimpleEventHandler"


class UpdateViewRangeEventHandler(UI.IExternalEventHandler):
    def __init__(self):
        self.new_values = None
        self.new_levels = None
        self.context = None

    def Execute(self, uiapp):
        try:
            if self.context and self.new_values:
                self.context._update_view_range_internal(
                    self.new_values, self.new_levels
                )
        except Exception as e:
            if hasattr(self.context, "view_model"):
                self.context.view_model.warning_message = (
                    "Error executing view range update: {}".format(str(e))
                )

    def GetName(self):
        return "UpdateViewRangeEventHandler"


class Context(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Context, cls).__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self, view_model):
        self._active_view = None
        self._source_view = None
        self.length_unit = (
            doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
        )
        self.height_data = {}
        self.offset_data = {}
        self.level_data = {}
        self.original_offset_data = {}
        self.original_level_data = {}
        self.view_model = view_model
        self._levels_populated = False  # Track if levels have been populated
        view_model.unit_label = DB.LabelUtils.GetLabelForUnit(self.length_unit)

    @property
    def active_view(self):
        if self._active_view and not self._active_view.IsValidObject:
            self._active_view = None
        return self._active_view

    @active_view.setter
    def active_view(self, value):
        if not compare_views(self._active_view, value):
            self._active_view = value
            self.context_changed()

    @property
    def source_view(self):
        if self._source_view and not self._source_view.IsValidObject:
            self._source_view = None
        return self._source_view

    @source_view.setter
    def source_view(self, value):
        if not compare_views(self._source_view, value):
            self._source_view = value
            self._levels_populated = False  # Reset when view changes
            self.context_changed()

    def update_view_range(self, new_values, new_levels=None):
        if not self.source_view or not isinstance(self.source_view, DB.ViewPlan):
            self.view_model.warning_message = "No valid plan view selected"
            return False
        if self.source_view.IsTemplate:
            self.view_model.warning_message = (
                "Cannot modify view range - this is a view template"
            )
            return False

        update_view_range_handler.new_values = new_values
        update_view_range_handler.new_levels = new_levels or {}
        update_view_range_handler.context = self
        update_view_range_event.Raise()
        return True

    def _update_view_range_internal(self, new_values, new_levels=None):
        try:
            if not self._validate_view_range_order(new_values, new_levels):
                return False

            with revit.Transaction("Update View Range", doc=revit.doc):
                view_range = self.source_view.GetViewRange()

                # First, update levels if provided
                if new_levels:
                    for plane, new_level_id in new_levels.items():
                        current_level_id = view_range.GetLevelId(plane)

                        # Handle Unlimited (InvalidElementId)
                        if new_level_id == DB.ElementId.InvalidElementId:
                            # For View Depth, Unlimited is common - set to InvalidElementId
                            if current_level_id != DB.ElementId.InvalidElementId:
                                try:
                                    # Note: Not all planes support InvalidElementId
                                    # View Depth typically does, others may not
                                    view_range.SetLevelId(
                                        plane, DB.ElementId.InvalidElementId
                                    )
                                except Exception:
                                    pass
                        # Handle regular level changes
                        elif new_level_id and current_level_id != new_level_id:
                            try:
                                view_range.SetLevelId(plane, new_level_id)
                            except Exception:
                                pass

                # Then, update offsets (only for planes that have valid levels)
                for plane, offset_str in new_values.items():
                    # Skip offset update if level is set to Unlimited
                    level_id = view_range.GetLevelId(plane)
                    if not level_id or level_id == DB.ElementId.InvalidElementId:
                        continue

                    if (
                        offset_str
                        and offset_str.strip()
                        and offset_str != "-"
                        and offset_str.upper() != "N/A"
                    ):
                        try:
                            offset_display = float(offset_str)
                            offset_internal = DB.UnitUtils.ConvertToInternalUnits(
                                offset_display, self.length_unit
                            )
                            current_offset = view_range.GetOffset(plane)

                            # Only update if different
                            if abs(current_offset - offset_internal) > 0.0001:
                                view_range.SetOffset(plane, offset_internal)
                        except ValueError:
                            return False

                # Apply the view range back to the view
                self.source_view.SetViewRange(view_range)
                self.context_changed()
                self.view_model.warning_message = "View range updated successfully"
                return True

        except Exception as e:
            self.view_model.warning_message = "Error updating view range: {}".format(
                str(e)
            )
            return False

    def _validate_view_range_order(self, new_values, new_levels=None):
        try:
            elevations = {}
            offset_values = {}

            for plane, offset_str in new_values.items():
                # Skip validation for N/A values (Unlimited levels)
                if offset_str and offset_str.upper() == "N/A":
                    continue

                if offset_str and offset_str.strip() and offset_str != "-":
                    try:
                        offset_value = float(offset_str)
                        offset_values[plane] = offset_value

                        # Use new level if provided, otherwise use current level
                        level = None
                        if new_levels and plane in new_levels:
                            level_id = new_levels[plane]
                            # Skip validation for Unlimited (InvalidElementId)
                            if (
                                not level_id
                                or level_id == DB.ElementId.InvalidElementId
                            ):
                                continue
                            level = self.source_view.Document.GetElement(level_id)

                        if not level:
                            level = self.level_data.get(plane)

                        if level:
                            level_elevation = DB.UnitUtils.ConvertFromInternalUnits(
                                level.ProjectElevation, self.length_unit
                            )
                            elevations[plane] = level_elevation + offset_value
                    except ValueError:
                        forms.alert(
                            "Invalid Input Format!\n\nThe value '{}' for {} is not a valid number.\n\n"
                            "Please enter a numeric value (e.g., 4.5, -2.0, 0)".format(
                                offset_str, PLANES[plane][1]
                            ),
                            title="Invalid Number Format",
                            warn_icon=True,
                        )
                        self.view_model.warning_message = (
                            "Invalid number format: {}".format(offset_str)
                        )
                        return False

            # If any plane is set to Unlimited, skip full validation
            if len(elevations) < 4:
                return True

            # Check order: Top >= Cut >= Bottom >= ViewDepth
            checks = [
                (
                    DB.PlanViewPlane.TopClipPlane,
                    DB.PlanViewPlane.CutPlane,
                    "Top Clip Plane",
                    "Cut Plane",
                ),
                (
                    DB.PlanViewPlane.CutPlane,
                    DB.PlanViewPlane.BottomClipPlane,
                    "Cut Plane",
                    "Bottom Clip Plane",
                ),
                (
                    DB.PlanViewPlane.BottomClipPlane,
                    DB.PlanViewPlane.ViewDepthPlane,
                    "Bottom Clip Plane",
                    "View Depth Plane",
                ),
            ]

            for higher_plane, lower_plane, higher_name, lower_name in checks:
                higher_elev = elevations.get(higher_plane)
                lower_elev = elevations.get(lower_plane)

                if (
                    higher_elev is not None
                    and lower_elev is not None
                    and higher_elev < lower_elev
                ):
                    forms.alert(
                        "View Range Order Error!\n\n{} (offset: {:.2f}') must be greater than or equal to {} "
                        "(offset: {:.2f}').\n\nNote: These are offset values from the associated level.\n\n"
                        "Correct order (top to bottom):\n1. Top Clip Plane (highest offset)\n2. Cut Plane\n"
                        "3. Bottom Clip Plane\n4. View Depth Plane (lowest offset)".format(
                            higher_name,
                            offset_values.get(higher_plane, 0),
                            lower_name,
                            offset_values.get(lower_plane, 0),
                        ),
                        title="Invalid View Range",
                        warn_icon=True,
                    )
                    self.view_model.warning_message = "{} must be >= {}".format(
                        higher_name, lower_name
                    )
                    return False

            return True

        except Exception as e:
            self.view_model.warning_message = "Error validating view range: {}".format(
                str(e)
            )
            return False

    def _populate_available_levels(self):
        """Populate the list of available levels in the project"""
        try:
            # Get all levels in the project
            level_collector = DB.FilteredElementCollector(self.source_view.Document).OfClass(DB.Level)
            levels = list(level_collector)

            # Sort levels by elevation
            levels.sort(key=lambda x: x.ProjectElevation)

            # Create a simple class for level items that WPF can bind to
            class LevelItem(object):
                def __init__(self, name, element_id, elevation=None, is_special=False):
                    self.Name = name
                    self.Id = element_id
                    self.IdValue = get_elementid_value(element_id) if element_id else INVALID_ID_VALUE
                    self.Elevation = elevation
                    self.IsSpecial = is_special

            # Create level items
            level_items = []

            # Add special "Unlimited" option (uses InvalidElementId)
            level_items.append(
                LevelItem("Unlimited", DB.ElementId.InvalidElementId, None, True)
            )

            # Add actual levels
            for level in levels:
                level_item = LevelItem(
                    level.Name, level.Id, level.ProjectElevation, False
                )
                level_items.append(level_item)

            self.view_model.available_levels = level_items
            self._levels_populated = True

        except Exception as e:
            self.view_model.warning_message = "Error loading levels: {}".format(str(e))

    def _set_current_level_selections(self, view_range):
        """Set the current level selections based on the view range"""
        try:
            # Store current selections
            stored_selections = {}

            # Set level selections for each plane
            for plane in PLANES:
                level_id = view_range.GetLevelId(plane)

                if plane == DB.PlanViewPlane.TopClipPlane:
                    if level_id and level_id != DB.ElementId.InvalidElementId:
                        stored_selections["top"] = get_elementid_value(level_id)
                    else:
                        stored_selections["top"] = INVALID_ID_VALUE

                elif plane == DB.PlanViewPlane.CutPlane:
                    # For Cut Plane, show the level name as read-only text
                    if level_id and level_id != DB.ElementId.InvalidElementId:
                        level = self.source_view.Document.GetElement(level_id)
                        self.view_model.cutplane_level_name = (
                            level.Name if level else "Unknown"
                        )
                    else:
                        self.view_model.cutplane_level_name = "Unlimited"

                elif plane == DB.PlanViewPlane.BottomClipPlane:
                    if level_id and level_id != DB.ElementId.InvalidElementId:
                        stored_selections["bottom"] = get_elementid_value(level_id)
                    else:
                        stored_selections["bottom"] = INVALID_ID_VALUE

                elif plane == DB.PlanViewPlane.ViewDepthPlane:
                    if level_id and level_id != DB.ElementId.InvalidElementId:
                        stored_selections["viewdepth"] = get_elementid_value(level_id)
                    else:
                        stored_selections["viewdepth"] = INVALID_ID_VALUE

            # Force update the view model properties (reset first to force binding refresh)
            self.view_model.topplane_level_id = None
            self.view_model.bottomplane_level_id = None
            self.view_model.viewdepth_level_id = None

            # Then set the actual values
            self.view_model.topplane_level_id = stored_selections.get("top", INVALID_ID_VALUE)
            self.view_model.bottomplane_level_id = stored_selections.get("bottom", INVALID_ID_VALUE)
            self.view_model.viewdepth_level_id = stored_selections.get("viewdepth", INVALID_ID_VALUE)

        except Exception as e:
            self.view_model.warning_message = (
                "Error setting level selections: {}".format(str(e))
            )

    def context_changed(self):
        # Clear original data dictionaries when view changes to prevent stale data in Reset
        self.original_offset_data = {}
        self.original_level_data = {}

        # Fix document reference - check validity and use source_view if available
        if self.active_view and self.active_view.IsValidObject:
            server.uidoc = UI.UIDocument(self.active_view.Document)
        elif self.source_view and self.source_view.IsValidObject:
            server.uidoc = UI.UIDocument(self.source_view.Document)

        # Reset all elevation and input values
        for _, _, prefix in PLANES.values():
            setattr(self.view_model, prefix + "_elevation", "-")
            setattr(self.view_model, prefix + "_new_value", "")

        self.view_model.warning_message = ""

        if not self.is_valid():
            server.meshes = None
            refresh_event.Raise()
            return

        try:
            edges, triangles = [], []

            if isinstance(self.source_view, DB.ViewPlan):
                if (
                    self.active_view.get_Parameter(
                        DB.BuiltInParameter.VIEWER_MODEL_CLIP_BOX_ACTIVE
                    ).AsInteger()
                    == 1
                ):
                    corners = corners_from_bb(self.active_view.GetSectionBox())
                else:
                    corners = corners_from_bb(self.source_view.CropBox)

                view_range = self.source_view.GetViewRange()

                # Only populate levels if not already populated
                if not self._levels_populated:
                    self._populate_available_levels()

                for plane in PLANES:
                    _, _, prefix = PLANES[plane]
                    level_id = view_range.GetLevelId(plane)

                    # Check if this plane is set to Unlimited
                    if not level_id or level_id == DB.ElementId.InvalidElementId:
                        self.height_data[plane] = "N/A"
                        self.offset_data[plane] = "N/A"
                        self.level_data[plane] = None
                        continue

                    plane_level = self.source_view.Document.GetElement(level_id)

                    if not plane_level:
                        self.height_data[plane] = "N/A"
                        self.offset_data[plane] = "N/A"
                        self.level_data[plane] = None
                        continue

                    self.level_data[plane] = plane_level

                    plane_elevation = (
                        plane_level.ProjectElevation + view_range.GetOffset(plane)
                    )
                    self.height_data[plane] = round(
                        DB.UnitUtils.ConvertFromInternalUnits(
                            plane_elevation, self.length_unit
                        ),
                        2,
                    )

                    offset_value = round(
                        DB.UnitUtils.ConvertFromInternalUnits(
                            view_range.GetOffset(plane), self.length_unit
                        ),
                        2,
                    )
                    self.offset_data[plane] = offset_value

                    if plane not in self.original_offset_data:
                        self.original_offset_data[plane] = offset_value

                    # Store original level data
                    if plane not in self.original_level_data:
                        self.original_level_data[plane] = level_id

                    cut_plane_vertices = [
                        DB.XYZ(c.X, c.Y, plane_elevation) for c in corners
                    ]
                    color = get_color_from_plane(plane)
                    edges.extend(create_edges(cut_plane_vertices, color))
                    triangles.extend(create_triangles(cut_plane_vertices, color))

                # Set all view model properties
                for plane in PLANES:
                    _, _, prefix = PLANES[plane]
                    setattr(
                        self.view_model,
                        prefix + "_elevation",
                        str(self.height_data[plane]),
                    )
                    setattr(
                        self.view_model,
                        prefix + "_new_value",
                        str(self.offset_data[plane]),
                    )

                # Set current level selections AFTER ensuring levels are populated
                self._set_current_level_selections(view_range)

            else:
                crop_bbox = self.source_view.CropBox
                cut_plane_vertices = corners_from_bb(crop_bbox)

                for plane_type in [
                    DB.PlanViewPlane.ViewDepthPlane,
                    DB.PlanViewPlane.CutPlane,
                ]:
                    color = get_color_from_plane(plane_type)
                    edges.extend(create_edges(cut_plane_vertices, color))
                    triangles.extend(create_triangles(cut_plane_vertices, color))

                    if plane_type == DB.PlanViewPlane.CutPlane:
                        view_dir_transform = DB.Transform.CreateTranslation(
                            self.source_view.ViewDirection.Negate()
                            * self.source_view.CropBox.Min.Z
                        )
                        cut_plane_vertices = [
                            view_dir_transform.OfPoint(pt) for pt in cut_plane_vertices
                        ]

            server.meshes = [revit.dc3dserver.Mesh(edges, triangles)]
            refresh_event.Raise()

        except Exception:
            print(traceback.format_exc())

    def is_valid(self):
        if not can_use_view_as_source(self.source_view):
            self.view_model.message = (
                "Please select a Plan or Section View in the Project Browser!"
            )
            self.view_model.can_modify_view = False
            return False
        elif not isinstance(context.active_view, DB.View3D):
            self.view_model.message = "Please activate a 3D View!"
            self.view_model.can_modify_view = False
            return False
        elif (
            not context.source_view.CropBoxActive
            and not context.active_view.get_Parameter(
                DB.BuiltInParameter.VIEWER_MODEL_CLIP_BOX_ACTIVE
            ).AsInteger()
            == 1
        ):
            self.view_model.message = (
                'Please activate the "Section Box" on the active view,\n'
                'or the "Crop View" on the selected view!'
            )
            self.view_model.can_modify_view = False
        else:
            can_modify = (
                isinstance(self.source_view, DB.ViewPlan)
                and not self.source_view.IsTemplate
            )
            self.view_model.can_modify_view = can_modify

            if self.source_view.IsTemplate:
                self.view_model.message = "Showing View Range of [{}]\n(View Template - Cannot Modify)".format(
                    self.source_view.Name
                )
            else:
                self.view_model.message = "Showing View Range of\n[{}]".format(
                    self.source_view.Name
                )
            return True


class MainViewModel(forms.Reactive):
    def __init__(self):
        self._message = None
        self._warning_message = ""
        self._can_modify_view = False

        # Initialize level-related properties - use INTEGER values for WPF binding
        self._available_levels = []
        self._topplane_level_id = INVALID_ID_VALUE
        self._bottomplane_level_id = INVALID_ID_VALUE
        self._viewdepth_level_id = INVALID_ID_VALUE
        self._cutplane_level_name = "Unknown"

        self.unit_label = ""

        # Create brushes and initialize values
        for plane, (rgb, name, prefix) in PLANES.items():
            setattr(
                self,
                prefix + "_brush",
                SolidColorBrush(Color.FromRgb(*[Convert.ToByte(i) for i in rgb])),
            )
            setattr(self, "_" + prefix + "_elevation", "-")
            setattr(self, "_" + prefix + "_new_value", "")

    @forms.reactive
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

    @forms.reactive
    def warning_message(self):
        return self._warning_message

    @warning_message.setter
    def warning_message(self, value):
        self._warning_message = value

    @forms.reactive
    def can_modify_view(self):
        return self._can_modify_view

    @can_modify_view.setter
    def can_modify_view(self, value):
        self._can_modify_view = value

    # Level properties
    @forms.reactive
    def available_levels(self):
        return self._available_levels

    @available_levels.setter
    def available_levels(self, value):
        self._available_levels = value

    @forms.reactive
    def topplane_level_id(self):
        return self._topplane_level_id

    @topplane_level_id.setter
    def topplane_level_id(self, value):
        self._topplane_level_id = value

    @forms.reactive
    def bottomplane_level_id(self):
        return self._bottomplane_level_id

    @bottomplane_level_id.setter
    def bottomplane_level_id(self, value):
        self._bottomplane_level_id = value

    @forms.reactive
    def viewdepth_level_id(self):
        return self._viewdepth_level_id

    @viewdepth_level_id.setter
    def viewdepth_level_id(self, value):
        self._viewdepth_level_id = value

    @forms.reactive
    def cutplane_level_name(self):
        return self._cutplane_level_name

    @cutplane_level_name.setter
    def cutplane_level_name(self, value):
        self._cutplane_level_name = value

    # Elevation properties
    @forms.reactive
    def topplane_elevation(self):
        return self._topplane_elevation

    @topplane_elevation.setter
    def topplane_elevation(self, value):
        self._topplane_elevation = value

    @forms.reactive
    def cutplane_elevation(self):
        return self._cutplane_elevation

    @cutplane_elevation.setter
    def cutplane_elevation(self, value):
        self._cutplane_elevation = value

    @forms.reactive
    def bottomplane_elevation(self):
        return self._bottomplane_elevation

    @bottomplane_elevation.setter
    def bottomplane_elevation(self, value):
        self._bottomplane_elevation = value

    @forms.reactive
    def viewdepth_elevation(self):
        return self._viewdepth_elevation

    @viewdepth_elevation.setter
    def viewdepth_elevation(self, value):
        self._viewdepth_elevation = value

    # New value properties
    @forms.reactive
    def topplane_new_value(self):
        return self._topplane_new_value

    @topplane_new_value.setter
    def topplane_new_value(self, value):
        self._topplane_new_value = value

    @forms.reactive
    def cutplane_new_value(self):
        return self._cutplane_new_value

    @cutplane_new_value.setter
    def cutplane_new_value(self, value):
        self._cutplane_new_value = value

    @forms.reactive
    def bottomplane_new_value(self):
        return self._bottomplane_new_value

    @bottomplane_new_value.setter
    def bottomplane_new_value(self, value):
        self._bottomplane_new_value = value

    @forms.reactive
    def viewdepth_new_value(self):
        return self._viewdepth_new_value

    @viewdepth_new_value.setter
    def viewdepth_new_value(self, value):
        self._viewdepth_new_value = value


class MainWindow(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(self, "MainWindow.xaml")
        self.Closed += self.window_closed
        script.restore_window_position(self)
        # Events are now handled via @events.handle decorators
        server.add_server()

    def window_closed(self, sender, args):
        script.save_window_position(self)
        server.remove_server()
        refresh_event.Raise()
        # Stop all registered events using the events API
        events.stop_events()

    def apply_changes_click(self, sender, e):
        try:
            new_values = {
                plane: getattr(self.DataContext, prefix + "_new_value")
                for plane, (_, _, prefix) in PLANES.items()
            }

            # Build new_levels dictionary - convert integer IDs back to ElementId
            new_levels = {}

            # Get values from ViewModel (which now stores integers)
            top_id_int = self.DataContext.topplane_level_id
            bottom_id_int = self.DataContext.bottomplane_level_id
            viewdepth_id_int = self.DataContext.viewdepth_level_id

            # Top Plane
            if top_id_int == INVALID_ID_VALUE:
                new_levels[DB.PlanViewPlane.TopClipPlane] = (
                    DB.ElementId.InvalidElementId
                )
            elif top_id_int is not None:
                new_levels[DB.PlanViewPlane.TopClipPlane] = DB.ElementId(top_id_int)

            # Bottom Plane
            if bottom_id_int == INVALID_ID_VALUE:
                new_levels[DB.PlanViewPlane.BottomClipPlane] = (
                    DB.ElementId.InvalidElementId
                )
            elif bottom_id_int is not None:
                new_levels[DB.PlanViewPlane.BottomClipPlane] = DB.ElementId(
                    bottom_id_int
                )

            # View Depth
            if viewdepth_id_int == INVALID_ID_VALUE:
                new_levels[DB.PlanViewPlane.ViewDepthPlane] = (
                    DB.ElementId.InvalidElementId
                )
            elif viewdepth_id_int is not None:
                new_levels[DB.PlanViewPlane.ViewDepthPlane] = DB.ElementId(
                    viewdepth_id_int
                )

            context.update_view_range(new_values, new_levels)
        except Exception as ex:
            self.DataContext.warning_message = "Error applying changes: {}".format(
                str(ex)
            )

    def reset_values_click(self, sender, e):
        try:
            # Reset offset values to original
            for plane, (_, _, prefix) in PLANES.items():
                original_value = context.original_offset_data.get(plane, "")
                setattr(self.DataContext, prefix + "_new_value", str(original_value))

            # Reset level selections to original levels
            if context.original_level_data:
                # Reset to original level selections
                for plane in PLANES:
                    original_level_id = context.original_level_data.get(plane)

                    if plane == DB.PlanViewPlane.TopClipPlane:
                        if (
                            original_level_id
                            and original_level_id != DB.ElementId.InvalidElementId
                        ):
                            self.DataContext.topplane_level_id = (
                                get_elementid_value(original_level_id)
                            )
                        else:
                            self.DataContext.topplane_level_id = INVALID_ID_VALUE

                    elif plane == DB.PlanViewPlane.CutPlane:
                        # For Cut Plane, show the original level name as read-only text
                        if (
                            original_level_id
                            and original_level_id != DB.ElementId.InvalidElementId
                        ):
                            try:
                                # Use source_view.Document instead of active_view.Document
                                if context.source_view and context.source_view.IsValidObject:
                                    level = context.source_view.Document.GetElement(
                                        original_level_id
                                    )
                                    self.DataContext.cutplane_level_name = (
                                        level.Name if level else "Unknown"
                                    )
                                else:
                                    self.DataContext.cutplane_level_name = "Unknown"
                            except Exception:
                                self.DataContext.cutplane_level_name = "Unknown"
                        else:
                            self.DataContext.cutplane_level_name = "Unlimited"

                    elif plane == DB.PlanViewPlane.BottomClipPlane:
                        if (
                            original_level_id
                            and original_level_id != DB.ElementId.InvalidElementId
                        ):
                            self.DataContext.bottomplane_level_id = (
                                get_elementid_value(original_level_id)
                            )
                        else:
                            self.DataContext.bottomplane_level_id = INVALID_ID_VALUE

                    elif plane == DB.PlanViewPlane.ViewDepthPlane:
                        if (
                            original_level_id
                            and original_level_id != DB.ElementId.InvalidElementId
                        ):
                            self.DataContext.viewdepth_level_id = (
                                get_elementid_value(original_level_id)
                            )
                        else:
                            self.DataContext.viewdepth_level_id = INVALID_ID_VALUE
            else:
                # Fallback: Reset level selections to current view range levels if no original data
                if hasattr(context, "source_view") and context.source_view:
                    view_range = context.source_view.GetViewRange()
                    context._set_current_level_selections(view_range)

            self.DataContext.warning_message = ""
        except Exception as ex:
            self.DataContext.warning_message = "Error resetting values: {}".format(
                str(ex)
            )


# Event handlers are now registered via @events.handle decorators below
# Old manual subscribe/unsubscribe functions removed in favor of events API


def refresh_active_view(uiapp):
    try:
        uidoc = uiapp.ActiveUIDocument
        if not compare_views(uidoc.ActiveView, context.active_view):
            uidoc.ActiveView = context.active_view
        uidoc.RefreshActiveView()
        if context.source_view:
            uidoc.Selection.SetElementIds(List[DB.ElementId]([context.source_view.Id]))
    except Exception:
        print(traceback.format_exc())


@events.handle("view-activated")
def view_activated(sender, args):
    try:
        context.active_view = args.CurrentActiveView
    except Exception:
        print(traceback.format_exc())


@events.handle("selection-changed")
def selection_changed(sender, args):
    if not args.GetDocument().ActiveView.ViewType == DB.ViewType.ProjectBrowser:
        return

    try:
        doc = args.GetDocument()
        sel_ids = list(args.GetSelectedElements())
        if len(sel_ids) == 1:
            sel = doc.GetElement(sel_ids[0])
            if can_use_view_as_source(sel):
                context.source_view = sel
                return
        context.source_view = None
    except Exception:
        print(traceback.format_exc())


@events.handle("doc-changed")
def doc_changed(sender, args):
    try:
        affected_ids = list(args.GetModifiedElementIds()) + list(
            args.GetDeletedElementIds()
        )
        if any(
            view.Id in affected_ids
            for view in [context.source_view, context.active_view]
        ):
            context.context_changed()
    except AttributeError:
        context.context_changed()
    except Exception:
        print(traceback.format_exc())


def compare_views(view1, view2):
    if not view1 and not view2:
        return True
    elif not view1 or not view2:
        return False
    return (
        view1.Document.GetHashCode() == view2.Document.GetHashCode()
        and view1.Id == view2.Id
    )


def can_use_view_as_source(view):
    return isinstance(view, (DB.ViewPlan, DB.ViewSection))


def corners_from_bb(bbox):
    transform = bbox.Transform
    corners = [
        bbox.Min,
        bbox.Min + DB.XYZ.BasisX * (bbox.Max - bbox.Min).X,
        bbox.Min
        + DB.XYZ.BasisX * (bbox.Max - bbox.Min).X
        + DB.XYZ.BasisY * (bbox.Max - bbox.Min).Y,
        bbox.Min + DB.XYZ.BasisY * (bbox.Max - bbox.Min).Y,
    ]
    return [transform.OfPoint(c) for c in corners]


def create_edges(vertices, color):
    return [
        revit.dc3dserver.Edge(vertices[i - 1], vertices[i], color)
        for i in range(len(vertices))
    ]


def create_triangles(vertices, color):
    return [
        revit.dc3dserver.Triangle(
            vertices[0],
            vertices[1],
            vertices[2],
            revit.dc3dserver.Mesh.calculate_triangle_normal(
                vertices[0], vertices[1], vertices[2]
            ),
            color,
        ),
        revit.dc3dserver.Triangle(
            vertices[2],
            vertices[3],
            vertices[0],
            revit.dc3dserver.Mesh.calculate_triangle_normal(
                vertices[2], vertices[3], vertices[0]
            ),
            color,
        ),
    ]


def get_color_from_plane(plane):
    rgb = PLANES[plane][0]
    return DB.ColorWithTransparency(rgb[0], rgb[1], rgb[2], 180)


# Initialize
server = revit.dc3dserver.Server(register=False)
refresh_event = UI.ExternalEvent.Create(SimpleEventHandler(refresh_active_view))
update_view_range_handler = UpdateViewRangeEventHandler()
update_view_range_event = UI.ExternalEvent.Create(update_view_range_handler)

vm = MainViewModel()
context = Context(vm)
context.active_view = uidoc.ActiveGraphicalView

main_window = MainWindow()
main_window.DataContext = vm
main_window.show()
