# -*- coding: utf-8 -*-
# type: ignore
"""Section Box Navigator - Modeless window for section box navigation."""

from pyrevit import revit, script, forms
from pyrevit.framework import System
from pyrevit.revit import events
from pyrevit import DB, UI

from sectionbox_navigation import (
    get_all_levels,
    get_all_grids,
    get_cardinal_direction,
    get_next_level_above,
    get_next_level_below,
    find_next_grid_in_direction,
)
from sectionbox_utils import (
    is_2d_view,
    get_view_range_and_crop,
    get_crop_element,
    compute_rotation_angle,
    apply_plan_viewrange_from_sectionbox,
    to_world_identity,
)
from sectionbox_actions import toggle, hide, align_to_face
from sectionbox_geometry import (
    get_section_box_info,
    get_section_box_face_info,
    select_best_face_for_direction,
    make_xy_transform_only,
)


# --------------------
# Initialize Variables
# --------------------

uidoc = revit.uidoc
doc = revit.doc
active_view = revit.active_view

logger = script.get_logger()
output = script.get_output()
output.close_others()

sb_form = None

length_format_options = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length)
length_unit = length_format_options.GetUnitTypeId()
length_unit_label = DB.LabelUtils.GetLabelForUnit(length_unit)
length_unit_symbol = length_format_options.GetSymbolTypeId()
length_unit_symbol_label = None
if not length_unit_symbol.Empty():
    length_unit_symbol_label = DB.LabelUtils.GetLabelForSymbol(length_unit_symbol)

DEFAULT_NUDGE_VALUE_MM = 500.0
default_nudge_value = DB.UnitUtils.Convert(
    DEFAULT_NUDGE_VALUE_MM, DB.UnitTypeId.Millimeters, length_unit
)
TOLERANCE = 1e-5
DATAFILENAME = "SectionBox"
WINDOW_POSITION = "sbnavigator_window_pos"

# --------------------
# Helper Functions
# --------------------


def create_preview_mesh(section_box, color):
    """Create a mesh for DC3D preview."""
    try:
        mesh = revit.dc3dserver.Mesh.from_boundingbox(
            section_box, color, black_edges=False
        )
        return mesh
    except Exception:
        logger.exception("Error creating preview mesh.")
        return None


def show_preview_mesh(box, preview_server):
    color = DB.ColorWithTransparency(100, 150, 255, 150)
    mesh = create_preview_mesh(box, color)
    if mesh:
        preview_server.meshes = [mesh]
        uidoc.RefreshActiveView()


def create_adjusted_box(
    info, min_x=0, max_x=0, min_y=0, max_y=0, min_z=0, max_z=0, new_transform=None
):
    """
    Create a new bounding box with adjustments applied.

    Args:
        info: Section box info dictionary from get_section_box_info()
        min_x, max_x, min_y, max_y, min_z, max_z: Adjustments to apply
        new_transform: Optional new transform (if None, uses existing)

    Returns:
        DB.BoundingBoxXYZ or None if invalid dimensions
    """
    min_point = info["min_point"]
    max_point = info["max_point"]
    transform = new_transform if new_transform else info["transform"]

    new_min = DB.XYZ(
        min_point.X + min_x,
        min_point.Y + min_y,
        min_point.Z + min_z,
    )

    new_max = DB.XYZ(
        max_point.X + max_x,
        max_point.Y + max_y,
        max_point.Z + max_z,
    )

    # Validate dimensions
    if new_max.X <= new_min.X or new_max.Y <= new_min.Y or new_max.Z <= new_min.Z:
        return None

    new_box = DB.BoundingBoxXYZ()
    new_box.Min = new_min
    new_box.Max = new_max
    new_box.Transform = transform

    return new_box


def format_length_value(value):
    return DB.UnitFormatUtils.Format(doc.GetUnits(), DB.SpecTypeId.Length, value, False)


# --------------------
# Event Handler
# --------------------


class HelperEventHandler(UI.IExternalEventHandler):
    """Event handler for executing Revit API operations."""

    def __init__(self, action):
        self.action = action
        self.parameters = None

    def Execute(self, uiapp):
        try:
            self.action(self.parameters)
        except Exception as ex:
            logger.error("Error in Execute: {}".format(ex))

    def GetName(self):
        return "SectionBoxNavigatorHandler"


# --------------------
# View Changed Monitor
# --------------------


@events.handle("doc-changed")
@events.handle("view-activated")
def on_view_or_doc_changed(sender, args):
    try:
        if not sb_form or not sb_form.chkAutoupdate.IsChecked:
            return
        sb_form.Dispatcher.Invoke(System.Action(sb_form.update_info))
        logger.info("Form updated due to view or document change.")
    except Exception as ex:
        logger.warning("Failed to update form: {}".format(ex))


# --------------------
# Main Form
# --------------------


class SectionBoxNavigatorForm(forms.WPFWindow):
    """Modeless form for section box navigation."""

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name, handle_esc=False)

        self.current_view = doc.ActiveView
        self.all_levels = get_all_levels(doc, self.chkIncludeLinks.IsChecked)
        self.all_grids = get_all_grids(doc, self.chkIncludeLinks.IsChecked)
        self.preview_server = None

        # Initialize DC3D Server
        try:
            self.preview_server = revit.dc3dserver.Server(
                uidoc=uidoc,
                name="Section Box Navigator Preview",
                description="Preview for section box adjustments",
            )
        except Exception:
            logger.warning("Could not initialize DC3D server")

        # Setup event handler
        self.event_handler = HelperEventHandler(self.execute_action)
        self.ext_event = UI.ExternalEvent.Create(self.event_handler)
        self.pending_action = None

        if not length_unit_symbol_label:
            self.project_unit_text.Visibility = System.Windows.Visibility.Visible
            self.project_unit_text.Text = (
                "Length Label (adjust in Project Units): \n" + length_unit_label
            )
        self.txtLevelNudgeAmount.Text = str(round(default_nudge_value, 3))
        self.txtLevelNudgeUnit.Text = length_unit_symbol_label or ""
        self.txtExpandAmount.Text = str(round(default_nudge_value, 3))
        self.txtExpandUnit.Text = length_unit_symbol_label or ""
        self.txtGridNudgeAmount.Text = str(round(default_nudge_value, 3))
        self.txtGridNudgeUnit.Text = length_unit_symbol_label or ""

        self.update_info()
        self.update_grid_status()
        self.update_expand_actions_status()

        # Event subscriptions
        self.Closed += self.form_closed

        try:
            pos = script.load_data(WINDOW_POSITION, this_project=False)
            all_bounds = [s.WorkingArea for s in System.Windows.Forms.Screen.AllScreens]
            x, y = pos["Left"], pos["Top"]
            visible = any(
                (b.Left <= x <= b.Right and b.Top <= y <= b.Bottom) for b in all_bounds
            )
            if not visible:
                raise Exception
            self.WindowStartupLocation = System.Windows.WindowStartupLocation.Manual
            self.Left = pos.get("Left", 200)
            self.Top = pos.get("Top", 150)
        except Exception:
            self.WindowStartupLocation = (
                System.Windows.WindowStartupLocation.CenterScreen
            )

        self.Show()

    def update_info(self):
        """Update the information display."""
        try:
            last_view = self.current_view.Id
            self.current_view = doc.ActiveView

            if is_2d_view(self.current_view):
                self.btnAlignToView.Content = "Align with 3D View"
                if last_view != self.current_view.Id:
                    self.clear_status_message()

            elif isinstance(self.current_view, DB.View3D):
                self.btnAlignToView.Content = "Align with 2D View"
                if last_view != self.current_view.Id:
                    self.clear_status_message()

            if (
                not isinstance(self.current_view, DB.View3D)
                or not self.current_view.IsSectionBoxActive
            ):
                self.txtTopLevelAbove.Text = "No section box active"
                self.txtTopPosition.Text = ""
                self.txtTopLevelBelow.Text = ""
                self.txtBottomLevelAbove.Text = ""
                self.txtBottomPosition.Text = ""
                self.txtBottomLevelBelow.Text = ""
                return

            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return

            transformed_max = info["transformed_max"]
            transformed_min = info["transformed_min"]

            # Get levels
            top_level_above, top_level_above_elevation = get_next_level_above(
                transformed_max.Z, self.all_levels, TOLERANCE
            )
            top_level_below, top_level_below_elevation = get_next_level_below(
                transformed_max.Z, self.all_levels, TOLERANCE
            )
            bottom_level_above, bottom_level_above_elevation = get_next_level_above(
                transformed_min.Z, self.all_levels, TOLERANCE
            )
            bottom_level_below, bottom_level_below_elevation = get_next_level_below(
                transformed_min.Z, self.all_levels, TOLERANCE
            )

            if top_level_above_elevation:
                top_level_above_elevation = format_length_value(
                    top_level_above_elevation
                )
            if top_level_below_elevation:
                top_level_below_elevation = format_length_value(
                    top_level_below_elevation
                )
            if bottom_level_above_elevation:
                bottom_level_above_elevation = format_length_value(
                    bottom_level_above_elevation
                )
            if bottom_level_below_elevation:
                bottom_level_below_elevation = format_length_value(
                    bottom_level_below_elevation
                )

            # Update top info
            if top_level_above:
                self.txtTopLevelAbove.Text = "Above Top: {} @ {}".format(
                    top_level_above.Name, top_level_above_elevation
                )
            else:
                self.txtTopLevelAbove.Text = "No level above top"
            if top_level_below:
                self.txtTopLevelBelow.Text = "Below Top: {} @ {}".format(
                    top_level_below.Name, top_level_below_elevation
                )
            else:
                self.txtTopLevelBelow.Text = "No level below top"

            top = format_length_value(transformed_max.Z)
            self.txtTopPosition.Text = "Top of Box: {}".format(top)

            # Update bottom info
            if bottom_level_above:
                self.txtBottomLevelAbove.Text = "Above Bottom: {} @ {}".format(
                    bottom_level_above.Name, bottom_level_above_elevation
                )
            else:
                self.txtBottomLevelAbove.Text = "No level above bottom"
            if bottom_level_below:
                self.txtBottomLevelBelow.Text = "Below Bottom: {} @ {}".format(
                    bottom_level_below.Name, bottom_level_below_elevation
                )
            else:
                self.txtBottomLevelBelow.Text = "No level below bottom"

            bottom = format_length_value(transformed_min.Z)
            self.txtBottomPosition.Text = "Bottom of Box: {}".format(bottom)

        except Exception:
            logger.exception("Error updating info.")

    def show_status_message(self, column, message, message_type="info"):
        """
        Display a status message in the appropriate column's status section.

        Args:
            column: 1 (Vertical), 2 (Grid), 3 (Expand/Actions)
            message: Text to display
            message_type: "info", "error", "warning", "success" (for color coding)
        """
        try:
            # Define color mapping
            colors = {
                "error": System.Windows.Media.Brushes.Red,
                "warning": System.Windows.Media.Brushes.Orange,
                "info": System.Windows.Media.Brushes.Blue,
                "success": System.Windows.Media.Brushes.Green,
            }

            color = colors.get(message_type.lower(), System.Windows.Media.Brushes.Black)

            def update_ui():
                if column == 1:
                    self.txtVerticalStatus.Text = message
                    self.txtVerticalStatus.Foreground = color
                elif column == 2:
                    self.txtGridStatus.Text = message
                    self.txtGridStatus.Foreground = color
                elif column == 3:
                    self.txtExpandActionsStatus.Text = message
                    self.txtExpandActionsStatus.Foreground = color

            self.Dispatcher.Invoke(System.Action(update_ui))
        except Exception as ex:
            logger.error("Error showing status message: {}".format(ex))

    def clear_status_message(self, column=None):
        """Clear the status message for the specified column."""
        try:

            def update_ui():
                if column == 1:
                    self.txtVerticalStatus.Text = ""
                elif column == 2:
                    self.txtGridStatus.Text = ""
                elif column == 3:
                    self.txtExpandActionsStatus.Text = ""
                elif column is None:
                    self.txtVerticalStatus.Text = ""
                    self.txtGridStatus.Text = ""
                    self.txtExpandActionsStatus.Text = ""

            self.Dispatcher.Invoke(System.Action(update_ui))
        except Exception as ex:
            logger.error("Error clearing status message: {}".format(ex))

    def update_grid_status(self):
        """Update the grid navigation status display."""
        try:

            def update_ui():
                info = get_section_box_info(self.current_view, DATAFILENAME)
                if not info:
                    self.txtGridStatus.Text = "No section box active"
                    self.txtGridStatus.Foreground = System.Windows.Media.Brushes.Gray
                    return

                # Get current grid position info if needed
                self.txtGridStatus.Text = "..."
                self.txtGridStatus.Foreground = System.Windows.Media.Brushes.Black

            self.Dispatcher.Invoke(System.Action(update_ui))
        except Exception as ex:
            logger.error("Error updating grid status: {}".format(ex))

    def update_expand_actions_status(self):
        """Update the expand/shrink and actions status display."""
        try:

            def update_ui():
                info = get_section_box_info(self.current_view, DATAFILENAME)
                if not info:
                    self.txtExpandActionsStatus.Text = "No section box active"
                    self.txtExpandActionsStatus.Foreground = (
                        System.Windows.Media.Brushes.Gray
                    )
                    return

                self.txtExpandActionsStatus.Text = "..."
                self.txtExpandActionsStatus.Foreground = (
                    System.Windows.Media.Brushes.Black
                )

            self.Dispatcher.Invoke(System.Action(update_ui))
        except Exception as ex:
            logger.error("Error updating expand/actions status: {}".format(ex))

    def execute_action(self, params):
        """Execute an action in Revit context."""
        try:
            action_type = params["action"]

            if action_type == "level_move":
                self.do_level_move(params)
            elif action_type == "toggle":
                self.do_toggle()
            elif action_type == "hide":
                self.do_hide()
            elif action_type == "align_to_face":
                self.do_align_to_face()
            elif action_type == "expand_shrink":
                self.do_expand_shrink(params)
            elif action_type == "align_to_2d_view":
                self.do_align_to_2d_view(params)
            elif action_type == "align_to_3d_view":
                self.do_align_to_3d_view(params)
            elif action_type == "grid_move":
                self.do_grid_move(params)

            # Update info after action
            self.Dispatcher.Invoke(System.Action(self.update_info))

        except Exception as ex:
            logger.exception("Error executing action: {}".format(ex))

    def do_level_move(self, params):
        """Move section box to level or by nudge amount."""
        direction = params.get("direction")  # 'top-up', 'bottom-down', 'box-up', etc.
        is_level_mode = params.get("is_level_mode", True)
        nudge_amount = params.get("nudge_amount", 0)
        do_not_apply = params.get("do_not_apply", False)

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return None if do_not_apply else False

        # Parse direction
        parts = direction.split("-")
        target = parts[0]  # 'top', 'bottom', or 'box'
        movement = parts[1]  # 'up' or 'down'

        adjust_top = False
        adjust_bottom = False
        top_distance = 0
        bottom_distance = 0

        # Store level information for status messages
        next_top_level = None
        next_bottom_level = None
        next_level = None

        if is_level_mode:
            # Level mode - snap to next level
            if target == "box":
                # Move entire box
                adjust_top = True
                adjust_bottom = True

                if movement == "up":
                    next_top_level, _ = get_next_level_above(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )
                    next_bottom_level, _ = get_next_level_above(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )
                else:
                    next_top_level, _ = get_next_level_below(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )
                    next_bottom_level, _ = get_next_level_below(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )

                if not next_top_level or not next_bottom_level:
                    if not do_not_apply:
                        self.show_status_message(
                            1, "Cannot find levels in that direction", "error"
                        )
                    return None

                top_distance = next_top_level.Elevation - info["transformed_max"].Z
                bottom_distance = (
                    next_bottom_level.Elevation - info["transformed_min"].Z
                )

                # Validate box dimensions
                if next_top_level.Elevation <= next_bottom_level.Elevation:
                    if not do_not_apply:
                        self.show_status_message(1, "Would create invalid box", "error")
                    return None

            elif target == "top":
                adjust_top = True

                if movement == "up":
                    next_level, _ = get_next_level_above(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )
                else:
                    next_level, _ = get_next_level_below(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )

                if not next_level:
                    if not do_not_apply:
                        self.show_status_message(
                            1, "No level found in that direction", "error"
                        )
                    return None

                top_distance = next_level.Elevation - info["transformed_max"].Z

                # Validate won't go below bottom
                if next_level.Elevation <= info["transformed_min"].Z:
                    if not do_not_apply:
                        self.show_status_message(1, "Would create invalid box", "error")
                    return None

            elif target == "bottom":
                adjust_bottom = True

                if movement == "up":
                    next_level, _ = get_next_level_above(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )
                else:
                    next_level, _ = get_next_level_below(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )

                if not next_level:
                    if not do_not_apply:
                        self.show_status_message(
                            1, "No level found in that direction", "error"
                        )
                    return None

                bottom_distance = next_level.Elevation - info["transformed_min"].Z

                # Validate won't go above top
                if next_level.Elevation >= info["transformed_max"].Z:
                    if not do_not_apply:
                        self.show_status_message(1, "Would create invalid box", "error")
                    return None

        else:
            # Nudge mode - move by specified amount
            distance = nudge_amount if movement == "up" else -nudge_amount

            if target == "box":
                # Move entire box
                adjust_top = True
                adjust_bottom = True
                top_distance = distance
                bottom_distance = distance
            elif target == "top":
                adjust_top = True
                top_distance = distance
            elif target == "bottom":
                adjust_bottom = True
                bottom_distance = distance

        # Create adjusted box
        if do_not_apply:
            new_box = create_adjusted_box(
                info,
                min_z=bottom_distance if adjust_bottom else 0,
                max_z=top_distance if adjust_top else 0,
            )
            return new_box

        # Apply the adjustment
        if self.adjust_section_box(
            min_z_change=bottom_distance if adjust_bottom else 0,
            max_z_change=top_distance if adjust_top else 0,
            min_x_change=0,
            max_x_change=0,
            min_y_change=0,
            max_y_change=0,
        ):
            # Success - show informative message
            if is_level_mode:
                # Level mode - show which level we moved to
                if target == "box":
                    if next_top_level and next_bottom_level:
                        self.show_status_message(
                            1,
                            "Box moved {}: Top to '{}', Bottom to '{}'".format(
                                movement, next_top_level.Name, next_bottom_level.Name
                            ),
                            "success",
                        )
                elif target == "top":
                    if next_level:
                        self.show_status_message(
                            1,
                            "Top moved {} to level '{}'".format(
                                movement, next_level.Name
                            ),
                            "success",
                        )
                elif target == "bottom":
                    if next_level:
                        self.show_status_message(
                            1,
                            "Bottom moved {} to level '{}'".format(
                                movement, next_level.Name
                            ),
                            "success",
                        )
            else:
                # Nudge mode - show nudge amount
                nudge_display = format_length_value(abs(nudge_amount))

                self.show_status_message(
                    1,
                    "Nudged {} by {} {}".format(target, nudge_display, movement),
                    "success",
                )

    def do_expand_shrink(self, params):
        """Expand or shrink the section box in all directions."""
        amount = params.get("amount", 0)
        is_expand = params.get("is_expand", True)

        # Calculate the adjustment (negative for shrink)
        adjustment = amount if is_expand else -amount

        if self.adjust_section_box(
            min_x_change=-adjustment,
            max_x_change=adjustment,
            min_y_change=-adjustment,
            max_y_change=adjustment,
            min_z_change=-adjustment,
            max_z_change=adjustment,
        ):
            # Success - show informative message
            amount_display = format_length_value(amount)
            operation = "Expanded" if is_expand else "Shrunk"
            self.show_status_message(
                3,
                "{} by {} in all directions".format(operation, amount_display),
                "success",
            )

    def do_grid_move(self, params):
        """Move section box side to next grid line or by nudge amount."""
        direction_name = params.get("direction")  # 'north-out', 'south-in', etc.
        is_grid_mode = params.get("is_grid_mode", True)
        nudge_amount = params.get("nudge_amount", 0)
        do_not_apply = params.get("do_not_apply", False)

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return None if do_not_apply else False

        # Parse direction into cardinal direction and in/out modifier
        parts = direction_name.split("-")
        cardinal_dir = parts[0]  # 'north', 'south', 'east', 'west'
        modifier = parts[1] if len(parts) > 1 else "out"  # 'in' or 'out'

        # Get cardinal direction vector - this represents which FACE we want to move
        face_direction = get_cardinal_direction(cardinal_dir, self.current_view)

        # Transform to local coordinates
        transform = info["transform"]
        inverse_transform = transform.Inverse
        local_face_direction = inverse_transform.OfVector(face_direction)

        # Determine which axis the face is on
        abs_x = abs(local_face_direction.X)
        abs_y = abs(local_face_direction.Y)

        min_x_change = 0
        max_x_change = 0
        min_y_change = 0
        max_y_change = 0

        if is_grid_mode:
            # Grid mode - snap to next grid line
            # Get faces and select the face we want to move
            faces = get_section_box_face_info(info)
            _, face_info = select_best_face_for_direction(faces, face_direction)

            if not face_info:
                if not do_not_apply:
                    self.show_status_message(
                        2, "Could not determine face to move.", "error"
                    )
                return None

            # Determine the search direction:
            # "-out": search away from center (same as face direction)
            # "-in": search toward center (opposite of face direction)
            search_direction = (
                face_direction if modifier == "out" else face_direction.Negate()
            )

            # Find next grid in the search direction
            grid, intersection = find_next_grid_in_direction(
                face_info["center"], search_direction, self.all_grids, TOLERANCE
            )

            if not grid:
                if not do_not_apply:
                    self.show_status_message(
                        2,
                        "No grid found in {} direction.".format(direction_name.upper()),
                        "error",
                    )
                return None

            # Calculate how far to move
            move_vector = intersection - face_info["center"]
            move_distance = move_vector.DotProduct(search_direction)

            if abs(move_distance) < TOLERANCE:
                if not do_not_apply:
                    self.show_status_message(2, "Already at grid line.", "info")
                return None

            # Convert movement to local coordinates
            local_move_vector = inverse_transform.OfVector(move_vector)

            # Apply movement based on which face we're moving
            if abs_x > abs_y:
                # Face is on X axis
                if local_face_direction.X > 0:
                    max_x_change = local_move_vector.X
                else:
                    min_x_change = local_move_vector.X
            else:
                # Face is on Y axis
                if local_face_direction.Y > 0:
                    max_y_change = local_move_vector.Y
                else:
                    min_y_change = local_move_vector.Y

        else:
            # Nudge mode - move by specified amount
            # Determine the actual movement direction:
            # "-out": move away from center (same as face direction)
            # "-in": move toward center (opposite of face direction)
            movement_direction = (
                face_direction if modifier == "out" else face_direction.Negate()
            )

            # Get the movement in local coordinates
            local_movement = inverse_transform.OfVector(movement_direction).Multiply(
                nudge_amount
            )

            # Apply movement based on which face we're moving
            if abs_x > abs_y:
                # Face is on X axis
                if local_face_direction.X > 0:
                    max_x_change = local_movement.X
                else:
                    min_x_change = local_movement.X
            else:
                # Face is on Y axis
                if local_face_direction.Y > 0:
                    max_y_change = local_movement.Y
                else:
                    min_y_change = local_movement.Y

        # Create adjusted box if in preview mode
        if do_not_apply:
            new_box = create_adjusted_box(
                info,
                min_x_change,
                max_x_change,
                min_y_change,
                max_y_change,
                0,
                0,
            )
            return new_box

        # Apply the adjustment
        if self.adjust_section_box(
            min_x_change=min_x_change,
            max_x_change=max_x_change,
            min_y_change=min_y_change,
            max_y_change=max_y_change,
            min_z_change=0,
            max_z_change=0,
        ):
            # Success - show informative message
            if is_grid_mode:
                # Get grid name
                grid_name = "Unknown"
                if grid:
                    if hasattr(grid, "Element"):
                        grid_name = grid.Element.Name
                    elif hasattr(grid, "Name"):
                        grid_name = grid.Name
                direction_display = cardinal_dir.upper()
                self.show_status_message(
                    2,
                    "Moved to grid '{}' in {} direction".format(
                        grid_name, direction_display
                    ),
                    "success",
                )
            else:
                # Nudge mode
                nudge_display = format_length_value(nudge_amount)

                direction_display = cardinal_dir.upper()
                self.show_status_message(
                    2,
                    "Nudged {} in {} direction".format(
                        nudge_display, direction_display
                    ),
                    "success",
                )

    def do_align_to_2d_view(self, params):
        """Align section box to a 2D view's range and crop."""
        view_data = params.get("view_data")
        if not view_data:
            return

        top_elevation = view_data.get("top_elevation", None)
        bottom_elevation = view_data.get("bottom_elevation", None)
        crop_box = view_data.get("crop_box", None)
        is_section = view_data.get("is_section", False)

        if not is_section and (top_elevation is None or bottom_elevation is None):
            self.show_status_message(
                1, "Could not get view range information.", "error"
            )
            return

        new_box = DB.BoundingBoxXYZ()

        if is_section:
            if not crop_box:
                self.show_status_message(
                    3, "Could not get crop box from section.", "error"
                )
                return
            new_box = to_world_identity(crop_box)

        elif crop_box:
            # For floor plans, use the existing logic
            xy_transform = make_xy_transform_only(crop_box.Transform)
            new_box.Min = DB.XYZ(crop_box.Min.X, crop_box.Min.Y, bottom_elevation)
            new_box.Max = DB.XYZ(crop_box.Max.X, crop_box.Max.Y, top_elevation)
            new_box.Transform = xy_transform
        else:
            # Fallback box
            source_view = view_data.get("view", None)
            elements = revit.query.get_all_elements_in_view(source_view)
            if not elements:
                self.show_status_message(
                    3, "No cropbox or elements found to extend scopebox to", "error"
                )
                return
            boxes = [
                b for b in [el.get_BoundingBox(source_view) for el in elements] if b
            ]
            min_x = min(b.Min.X for b in boxes if b)
            min_y = min(b.Min.Y for b in boxes if b)
            max_x = max(b.Max.X for b in boxes if b)
            max_y = max(b.Max.Y for b in boxes if b)
            new_box.Min = DB.XYZ(min_x, min_y, bottom_elevation)
            new_box.Max = DB.XYZ(max_x, max_y, top_elevation)

        # Show preview and ask for confirmation
        show_preview_mesh(new_box, self.preview_server)
        result = forms.alert(
            "Apply section box from view '{}'?".format(view_data["view"].Name),
            title="Confirm Section Box",
            ok=True,
            cancel=True,
        )

        # Hide preview
        if self.preview_server:
            self.preview_server.meshes = []
            uidoc.RefreshActiveView()

        # Apply if confirmed
        if result:
            with revit.Transaction("Align to View"):
                self.current_view.SetSectionBox(new_box)
            self.show_status_message(
                3,
                "Section box aligned to view '{}'".format(view_data["view"].Name),
                "success",
            )

    def do_align_to_3d_view(self, params):
        view_data = params.get("view_data")
        if not view_data:
            return

        vt = view_data.get("view_type", None)
        section_box = view_data.get("section_box", None)

        # Has to be a seperate Transaction for rotate_crop_element to find the bbox
        with revit.Transaction("Activate CropBox"):
            if not self.current_view.CropBoxActive:
                self.current_view.CropBoxActive = True

            if not self.current_view.CropBoxVisible:
                self.current_view.CropBoxVisible = True

        with revit.Transaction("Align 2D View to 3D Section Box"):
            if vt == DB.ViewType.FloorPlan or vt == DB.ViewType.CeilingPlan:
                self.current_view.CropBox = section_box
                crop_el = get_crop_element(doc, self.current_view)
                if crop_el:
                    # --- 1. Compute 3D section box centroid in world coordinates ---
                    tf = section_box.Transform
                    sb_min = tf.OfPoint(section_box.Min)
                    sb_max = tf.OfPoint(section_box.Max)
                    sb_centroid = DB.XYZ(
                        (sb_min.X + sb_max.X) / 2.0,
                        (sb_min.Y + sb_max.Y) / 2.0,
                        0,  # Z is ignored for plan rotation
                    )

                    # --- 2. Compute current crop element centroid in view coordinates ---
                    crop_box = crop_el.get_BoundingBox(self.current_view)
                    crop_centroid = DB.XYZ(
                        (crop_box.Min.X + crop_box.Max.X) / 2.0,
                        (crop_box.Min.Y + crop_box.Max.Y) / 2.0,
                        0,
                    )

                    # --- 3. Translate crop element so centroids align (XY only) ---
                    translation = sb_centroid - crop_centroid
                    DB.ElementTransformUtils.MoveElement(doc, crop_el.Id, translation)

                    # --- 4. Rotate crop element around vertical axis through its centroid ---
                    angle = compute_rotation_angle(section_box, self.current_view)
                    axis = DB.Line.CreateBound(
                        DB.XYZ(sb_centroid.X, sb_centroid.Y, 0),
                        DB.XYZ(sb_centroid.X, sb_centroid.Y, 1),
                    )
                    DB.ElementTransformUtils.RotateElement(doc, crop_el.Id, axis, angle)
                apply_plan_viewrange_from_sectionbox(
                    doc, self.current_view, section_box
                )
                self.show_status_message(
                    3,
                    "Crop box aligned to view '{}'".format(view_data["view"].Name),
                    "success",
                )

            else:
                self.show_status_message(3, "Unsupported view type.", "warning")
                return

    def do_toggle(self):
        """Toggle section or crop box."""
        if isinstance(self.current_view, DB.View3D):
            was_active = self.current_view.IsSectionBoxActive
            toggle(doc, DATAFILENAME)
            is_now_active = self.current_view.IsSectionBoxActive
        elif is_2d_view(self.current_view):
            was_active = self.current_view.CropBoxActive
            with revit.Transaction("Toggle CropBox Active State"):
                self.current_view.CropBoxActive = not was_active
            is_now_active = self.current_view.CropBoxActive
        else:
            return
        if was_active != is_now_active:
            state = "activated" if is_now_active else "deactivated"
            self.show_status_message(3, "Box {}".format(state), "success")
        else:
            self.show_status_message(3, "Box toggle failed", "error")

    def do_hide(self):
        """Hide or Unhide section or crop box."""
        try:
            if isinstance(self.current_view, DB.View3D):
                was_hidden = hide(doc)
            elif is_2d_view(self.current_view):
                was_hidden = self.current_view.CropBoxVisible
                with revit.Transaction("Toggle CropBox Visibility"):
                    self.current_view.CropBoxVisible = not was_hidden
            else:
                return
            state = "hidden" if not was_hidden else "unhidden"
            self.show_status_message(3, "Box {}".format(state), "success")
        except Exception:
            self.show_status_message(3, "Error in Box visibility", "error")

    def do_align_to_face(self):
        """Align to face"""
        if not isinstance(self.current_view, DB.View3D):
            return
        try:
            align_to_face(doc, uidoc)
            self.show_status_message(3, "Section box aligned to face", "success")
        except Exception as ex:
            # User might have cancelled, don't show error for cancellation
            if "cancelled" not in str(ex).lower() and "cancel" not in str(ex).lower():
                self.show_status_message(
                    3, "Failed to align to face: {}".format(str(ex)), "error"
                )

    def adjust_section_box(
        self,
        min_x_change=0,
        max_x_change=0,
        min_y_change=0,
        max_y_change=0,
        min_z_change=0,
        max_z_change=0,
    ):
        """Unified method to adjust the section box in any direction."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return False

        new_box = create_adjusted_box(
            info,
            min_x_change,
            max_x_change,
            min_y_change,
            max_y_change,
            min_z_change,
            max_z_change,
        )

        if not new_box:
            # Determine which column to show error in based on what changed
            # If only Z changed, it's column 1 (vertical)
            # If X or Y changed, it's column 2 (grid)
            # If all changed, it's column 3 (expand/shrink)
            if min_z_change != 0 or max_z_change != 0:
                if (
                    min_x_change == 0
                    and max_x_change == 0
                    and min_y_change == 0
                    and max_y_change == 0
                ):
                    self.show_status_message(
                        1, "Invalid section box dimensions.", "error"
                    )
                else:
                    self.show_status_message(
                        3, "Invalid section box dimensions.", "error"
                    )
            elif (
                min_x_change != 0
                or max_x_change != 0
                or min_y_change != 0
                or max_y_change != 0
            ):
                self.show_status_message(2, "Invalid section box dimensions.", "error")
            else:
                self.show_status_message(3, "Invalid section box dimensions.", "error")
            return False

        with revit.Transaction("Adjust Section Box"):
            self.current_view.SetSectionBox(new_box)

        return True

    def show_preview(self, preview_type="level_nudge", params=None):
        """Show preview of adjusted section box."""
        if not self.preview_server or not self.chkPreview.IsChecked:
            return

        try:
            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return

            preview_box = None

            if preview_type == "toggle":
                preview_box = create_adjusted_box(info)

            elif preview_type == "expand_shrink":
                adjustment = params.get("adjustment", 0)

                preview_box = create_adjusted_box(
                    info,
                    min_x=-adjustment,
                    max_x=adjustment,
                    min_y=-adjustment,
                    max_y=adjustment,
                    min_z=-adjustment,
                    max_z=adjustment,
                )

            elif preview_type == "box":
                preview_box = params.get("box")

            if not preview_box:
                return

            show_preview_mesh(preview_box, self.preview_server)

        except Exception as ex:
            logger.error("Error showing preview: {}".format(ex))

    def hide_preview(self):
        """Hide the preview."""
        if self.preview_server:
            try:
                self.preview_server.meshes = []
                uidoc.RefreshActiveView()
            except Exception as ex:
                logger.warning("Error hiding preview: {}".format(ex))

    # Helper Functions

    def _handle_level_move(self, direction):
        """Helper to handle level movement based on mode."""
        is_level_mode = self.rbLevel.IsChecked

        if is_level_mode:
            # Level mode - move to next level
            self.pending_action = {
                "action": "level_move",
                "direction": direction,
                "is_level_mode": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        else:
            # Nudge mode - move by amount
            try:
                distance = self._get_validated_nudge_amount(self.txtLevelNudgeAmount, 1)
                self.pending_action = {
                    "action": "level_move",
                    "direction": direction,
                    "is_level_mode": False,
                    "nudge_amount": distance,
                }
                self.event_handler.parameters = self.pending_action
                self.ext_event.Raise()

            except ValueError:
                self.show_status_message(1, "Please enter a valid number", "warning")
                return
            except Exception as ex:
                logger.error("Error in level nudge: {}".format(ex))
                self.show_status_message(
                    1, "An error occurred: {}".format(str(ex)), "error"
                )
                return

    def _handle_grid_move(self, direction):
        """Helper to handle grid movement."""
        is_grid_mode = self.rbGrid.IsChecked

        if is_grid_mode:
            # Grid mode - move to next grid
            self.pending_action = {
                "action": "grid_move",
                "direction": direction,
                "is_grid_mode": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        else:
            # Nudge mode - move by amount
            try:
                distance = self._get_validated_nudge_amount(self.txtGridNudgeAmount, 2)
                self.pending_action = {
                    "action": "grid_move",
                    "direction": direction,
                    "is_grid_mode": False,
                    "nudge_amount": distance,
                }
                self.event_handler.parameters = self.pending_action
                self.ext_event.Raise()

            except ValueError:
                self.show_status_message(2, "Please enter a valid number", "warning")
                return
            except Exception as ex:
                logger.error("Error in horizontal nudge: {}".format(ex))
                self.show_status_message(
                    2, "An error occurred: {}".format(str(ex)), "error"
                )
                return

    def _get_validated_nudge_amount(self, text_control, column=None, unit=length_unit):
        """Extract and validate nudge amount from text control.

        Returns:
            float: Converted distance in internal units, or None if invalid
        """
        try:
            distance_text = text_control.Text.strip()
            if column and not distance_text:
                self.show_status_message(
                    column, "Please enter a nudge amount", "warning"
                )
                return None

            distance = float(distance_text)
            if column and distance <= 0:
                self.show_status_message(
                    column, "Amount must be greater than 0", "warning"
                )
                return None

            return DB.UnitUtils.ConvertToInternalUnits(distance, unit)

        except ValueError:
            self.show_status_message(column, "Please enter a valid number", "warning")
            return None

    # Button Handlers

    def btn_top_up_click(self, sender, e):
        """Move top up."""
        self._handle_level_move(sender.Tag)

    def btn_top_down_click(self, sender, e):
        """Move top down."""
        self._handle_level_move(sender.Tag)

    def btn_bottom_up_click(self, sender, e):
        """Move bottom up."""
        self._handle_level_move(sender.Tag)

    def btn_bottom_down_click(self, sender, e):
        """Move bottom down."""
        self._handle_level_move(sender.Tag)

    def btn_box_up_click(self, sender, e):
        """Move entire box up."""
        self._handle_level_move(sender.Tag)

    def btn_box_down_click(self, sender, e):
        """Move entire box down."""
        self._handle_level_move(sender.Tag)

    def btn_expansion_top_up_click(self, sender, e):
        """Expand the section box."""
        try:
            amount = self._get_validated_nudge_amount(self.txtExpandAmount, 3)
            self.pending_action = {
                "action": "expand_shrink",
                "amount": amount,
                "is_expand": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            self.show_status_message(
                3, "Please enter a valid number for expansion amount", "warning"
            )
        except Exception as ex:
            logger.error("Error in expansion: {}".format(ex))
            self.show_status_message(
                3, "An error occurred while expanding: {}".format(str(ex)), "error"
            )

    def btn_expansion_top_down_click(self, sender, e):
        """Shrink the section box."""
        try:
            amount_text = self.txtExpandAmount.Text.strip()
            if not amount_text:
                self.show_status_message(3, "Please enter a shrink amount", "warning")
                return

            amount = float(amount_text)
            if amount <= 0:
                self.show_status_message(
                    3, "Shrink amount must be greater than 0", "warning"
                )
                return

            amount = DB.UnitUtils.ConvertToInternalUnits(amount, length_unit)
            self.pending_action = {
                "action": "expand_shrink",
                "amount": amount,
                "is_expand": False,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            self.show_status_message(
                3, "Please enter a valid number for shrink amount", "warning"
            )
        except Exception as ex:
            logger.error("Error in shrink: {}".format(ex))
            self.show_status_message(
                3, "An error occurred while shrinking: {}".format(str(ex)), "error"
            )

    def btn_align_box_to_view_click(self, sender, e):
        """Align section box to a selected view."""
        self.current_view = doc.ActiveView
        # Select the view to align
        if isinstance(self.current_view, DB.View3D):
            selected_view = forms.select_views(
                multiple=False,
                filterfunc=is_2d_view,
                title="Select 2D View for Section Box",
            )

            if not selected_view:
                return

            # Get view range and crop information
            view_data = get_view_range_and_crop(selected_view, doc)
            self.pending_action = {
                "action": "align_to_2d_view",
                "view_data": view_data,
            }

        elif is_2d_view(self.current_view, only_plan=True):

            selected_view = forms.select_views(
                multiple=False,
                filterfunc=lambda v: isinstance(v, DB.View3D),
                title="Select 3D View to Copy From",
            )
            if not selected_view:
                return

            info = get_section_box_info(selected_view, DATAFILENAME)
            section_box = info.get("box")
            if not section_box:
                self.show_status_message(3, "3D view has no section box.", "error")
                return

            view_data = {
                "view_type": self.current_view.ViewType,
                "section_box": section_box,
                "view": self.current_view,
            }
            self.pending_action = {
                "action": "align_to_3d_view",
                "view_data": view_data,
            }

        else:
            return

        if not view_data:
            self.show_status_message(3, "Could not extract view information.", "error")
            return

        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_preview_enter(self, sender, e):
        """Show preview when hovering over level, grid, or expansion buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            tag = sender.Tag

            # Determine button type from tag
            is_level_button = any(word in tag for word in ["top", "bottom", "box"])
            is_grid_button = any(
                word in tag for word in ["north", "east", "south", "west"]
            )
            is_expansion_button = any(word in tag for word in ["expand", "shrink"])
            is_toggle_button = "toggle" in tag

            box = None

            if is_level_button:
                is_level_mode = self.rbLevel.IsChecked
                distance = self._get_validated_nudge_amount(self.txtLevelNudgeAmount)
                if not is_level_mode and distance is None:
                    return

                params = {
                    "direction": tag,
                    "is_level_mode": is_level_mode,
                    "nudge_amount": distance,
                    "do_not_apply": True,
                }
                box = self.do_level_move(params)

            elif is_grid_button:
                is_grid_mode = self.rbGrid.IsChecked
                distance = self._get_validated_nudge_amount(self.txtGridNudgeAmount)
                if not is_grid_mode and distance is None:
                    return

                params = {
                    "direction": tag,
                    "is_grid_mode": is_grid_mode,
                    "nudge_amount": distance,
                    "do_not_apply": True,
                }
                box = self.do_grid_move(params)

            elif is_expansion_button:
                amount = self._get_validated_nudge_amount(self.txtExpandAmount)
                if amount is None:
                    return

                is_expand = "expand" in sender.Tag
                adjustment = amount if is_expand else -amount

                info = get_section_box_info(self.current_view, DATAFILENAME)
                if info:
                    box = create_adjusted_box(
                        info,
                        min_x=-adjustment,
                        max_x=adjustment,
                        min_y=-adjustment,
                        max_y=adjustment,
                        min_z=-adjustment,
                        max_z=adjustment,
                    )

            # Show preview if we got a valid box
            if box:
                params = {"box": box}
                self.show_preview("box", params)
            elif is_toggle_button:
                self.show_preview("toggle")

        except Exception as ex:
            logger.warning("Error in preview: {}".format(ex))

    def btn_preview_leave(self, sender, e):
        """Hide preview when leaving buttons."""
        self.hide_preview()

    def btn_toggle_box_click(self, sender, e):
        """Toggle section box."""
        self.pending_action = {
            "action": "toggle",
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_hide_box_click(self, sender, e):
        """Hide/unhide section box."""
        self.pending_action = {
            "action": "hide",
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_align_box_to_face_click(self, sender, e):
        """Align section box to face."""
        self.pending_action = {
            "action": "align_to_face",
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def chkIncludeLinks_checked(self, sender, e):
        """Refresh levels and grids when checkbox is toggled."""
        self.all_levels = get_all_levels(doc, self.chkIncludeLinks.IsChecked)
        self.all_grids = get_all_grids(doc, self.chkIncludeLinks.IsChecked)
        self.update_info()

    # Grid Navigation Button Handlers

    def btn_grid_west_out_click(self, sender, e):
        """Move west side outward (west direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_west_in_click(self, sender, e):
        """Move west side inward (east direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_north_out_click(self, sender, e):
        """Move north side outward (north direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_north_in_click(self, sender, e):
        """Move north side inward (south direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_south_out_click(self, sender, e):
        """Move south side outward (south direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_south_in_click(self, sender, e):
        """Move south side inward (north direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_east_out_click(self, sender, e):
        """Move east side outward (east direction)."""
        self._handle_grid_move(sender.Tag)

    def btn_grid_east_in_click(self, sender, e):
        """Move east side inward (west direction)."""
        self._handle_grid_move(sender.Tag)

    def form_closed(self, sender, args):
        """Cleanup when form is closed."""
        try:
            # Save window position
            new_pos = {"Left": self.Left, "Top": self.Top}
            script.store_data(WINDOW_POSITION, new_pos, this_project=False)

            # Unregister event handlers
            events.stop_events()

            # Cleanup form - shouldn't be necessary?
            global sb_form
            sb_form = None

            # Remove DC3D server
            if self.preview_server:
                try:
                    self.preview_server.remove_server()
                except Exception as ex:
                    logger.warning("Error removing DC3D server: {}".format(ex))

            # Refresh view
            try:
                uidoc.RefreshActiveView()
            except Exception as ex:
                logger.warning("Error refreshing view: {}".format(ex))

        except Exception:
            logger.exception("Error during cleanup.")


# ---------
# Run main
# ---------

if __name__ == "__main__":
    try:
        # Check if section box is active
        if not active_view.IsSectionBoxActive:
            try:
                info = get_section_box_info(active_view, DATAFILENAME)
                restored_bbox = info.get("box")
                if not restored_bbox:
                    raise Exception

                # Ask user if they want to restore
                if forms.alert(
                    "Stored SectionBox for this view found! Restore?",
                    cancel=True,
                    title="Restore Section Box",
                ):
                    with revit.Transaction("Restore SectionBox"):
                        active_view.SetSectionBox(restored_bbox)
            except Exception:
                forms.alert(
                    "The current view doesn't have an active or stored section box.",
                    title="No Section Box",
                    exitscript=True,
                )

        sb_form = SectionBoxNavigatorForm("SectionBoxNavigator.xaml")

    except Exception as ex:
        logger.exception("Error launching form: {}".format(ex))
        forms.alert("An error occurred: {}".format(str(ex)), title="Error")
