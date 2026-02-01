# -*- coding: utf-8 -*-
# type: ignore
"""Section Box Navigator - Modeless window for section box navigation."""

from pyrevit import revit, script, forms
from pyrevit.framework import System, Controls, Media
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
            self.project_unit_text.Visibility = forms.WPF_VISIBLE
            self.project_unit_text.Text = (
                self.get_locale_string("LengthLabelAdjust") + "\n" + length_unit_label
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
        self.update_dropdown_visibility()

        self.Closed += self.form_closed
        script.restore_window_position(self)
        self.Show()

    def update_dropdown_visibility(self):
        """Show/hide dropdown arrows based on Level mode."""
        visibility = forms.WPF_VISIBLE if self.rbLevel.IsChecked else forms.WPF_COLLAPSED

        self.btnTopUpDropdown.Visibility = visibility
        self.btnTopDownDropdown.Visibility = visibility
        self.btnBottomUpDropdown.Visibility = visibility
        self.btnBottomDownDropdown.Visibility = visibility
        self.btnBoxUpDropdown.Visibility = visibility
        self.btnBoxDownDropdown.Visibility = visibility

    def populate_level_menu(self, menu, direction, target):
        """Populate a level menu with all available levels in the given direction.

        Args:
            menu: StackPanel to populate with level buttons
            direction: 'up' or 'down'
            target: 'top', 'bottom', or 'both'
        """
        menu.Children.Clear()

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        # Determine reference elevation based on target
        if target == "top":
            ref_elevation = info["transformed_max"].Z
        elif target == "bottom":
            ref_elevation = info["transformed_min"].Z
        elif target == "both":
            # For box movement, use the top elevation
            ref_elevation = info["transformed_max"].Z
        else:
            return

        # Collect all levels in the direction
        levels = []
        current_elevation = ref_elevation

        while True:
            if direction == "up":
                next_level, _ = get_next_level_above(
                    current_elevation, self.all_levels, TOLERANCE
                )
            else:
                next_level, _ = get_next_level_below(
                    current_elevation, self.all_levels, TOLERANCE
                )

            if not next_level:
                break

            levels.append(next_level)
            current_elevation = next_level.Elevation

            # Limit to reasonable number of levels
            if len(levels) >= 20:
                break

        # Create buttons for each level
        for level in levels:
            btn = Controls.Button()
            btn.Style = self.FindResource("LevelMenuItemStyle")

            # Format level name and elevation
            level_name = level.Name
            level_elev = format_length_value(level.Elevation)
            btn.Content = "{0} ({1})".format(level_name, level_elev)

            # Store level info in Tag
            btn.Tag = {
                "target": target,
                "direction": direction,
                "elevation": level.Elevation
            }

            # Wire up click and hover events
            btn.Click += self.btn_menu_item_click
            btn.MouseEnter += self.btn_preview_enter
            btn.MouseLeave += self.btn_preview_leave

            menu.Children.Add(btn)

        # If no levels found, add a disabled message
        if len(levels) == 0:
            lbl = Controls.TextBlock()
            lbl.Text = self.get_locale_string("NoLevelFoundInDirection")
            lbl.Margin = System.Windows.Thickness(10, 5, 10, 5)
            lbl.Foreground = Media.Brushes.Gray
            menu.Children.Add(lbl)

    # ----------
    # STATUS MESSAGES
    # ----------

    def update_info(self):
        """Update the information display."""
        try:
            last_view = self.current_view.Id
            self.current_view = doc.ActiveView

            if is_2d_view(self.current_view):
                self.btnAlignToView.Content = self.get_locale_string("AlignWith3DView")
                if last_view != self.current_view.Id:
                    self.clear_status_message()

            elif isinstance(self.current_view, DB.View3D):
                self.btnAlignToView.Content = self.get_locale_string("AlignWith2DView")
                if last_view != self.current_view.Id:
                    self.clear_status_message()

            if (
                not isinstance(self.current_view, DB.View3D)
                or not self.current_view.IsSectionBoxActive
            ):
                self.txtTopLevelAbove.Text = self.get_locale_string("NoSectionBoxActive")
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
                self.txtTopLevelAbove.Text = self.get_locale_string("AboveTopFormat").format(
                    top_level_above.Name, top_level_above_elevation
                )
            else:
                self.txtTopLevelAbove.Text = self.get_locale_string("NoLevelAboveTop")
            if top_level_below:
                self.txtTopLevelBelow.Text = self.get_locale_string("BelowTopFormat").format(
                    top_level_below.Name, top_level_below_elevation
                )
            else:
                self.txtTopLevelBelow.Text = self.get_locale_string("NoLevelBelowTop")

            top = format_length_value(transformed_max.Z)
            self.txtTopPosition.Text = self.get_locale_string("TopOfBoxFormat").format(top)

            # Update bottom info
            if bottom_level_above:
                self.txtBottomLevelAbove.Text = self.get_locale_string("AboveBottomFormat").format(
                    bottom_level_above.Name, bottom_level_above_elevation
                )
            else:
                self.txtBottomLevelAbove.Text = self.get_locale_string("NoLevelAboveBottom")
            if bottom_level_below:
                self.txtBottomLevelBelow.Text = self.get_locale_string("BelowBottomFormat").format(
                    bottom_level_below.Name, bottom_level_below_elevation
                )
            else:
                self.txtBottomLevelBelow.Text = self.get_locale_string("NoLevelBelowBottom")

            bottom = format_length_value(transformed_min.Z)
            self.txtBottomPosition.Text = self.get_locale_string("BottomOfBoxFormat").format(bottom)

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
                "error": Media.Brushes.Red,
                "warning": Media.Brushes.Orange,
                "info": Media.Brushes.Blue,
                "success": Media.Brushes.Green,
            }

            color = colors.get(message_type.lower(), Media.Brushes.Black)

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
                    self.txtGridStatus.Text = self.get_locale_string("NoSectionBoxActive")
                    self.txtGridStatus.Foreground = Media.Brushes.Gray
                    return

                # Get current grid position info if needed
                self.txtGridStatus.Text = "..."
                self.txtGridStatus.Foreground = Media.Brushes.Black

            self.Dispatcher.Invoke(System.Action(update_ui))
        except Exception as ex:
            logger.error("Error updating grid status: {}".format(ex))

    def update_expand_actions_status(self):
        """Update the expand/shrink and actions status display."""
        try:

            def update_ui():
                info = get_section_box_info(self.current_view, DATAFILENAME)
                if not info:
                    self.txtExpandActionsStatus.Text = self.get_locale_string("NoSectionBoxActive")
                    self.txtExpandActionsStatus.Foreground = (
                        Media.Brushes.Gray
                    )
                    return

                self.txtExpandActionsStatus.Text = "..."
                self.txtExpandActionsStatus.Foreground = (
                    Media.Brushes.Black
                )

            self.Dispatcher.Invoke(System.Action(update_ui))
        except Exception as ex:
            logger.error("Error updating expand/actions status: {}".format(ex))

    # ----------
    # ACTIONS
    # ----------

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
        target = params.get("target")  # 'top, 'bottom', 'both'
        direction = params.get("direction")  # 'up', 'down'
        nudge_amount = params.get("nudge_amount", 0)
        do_not_apply = params.get("do_not_apply", False)
        elevation = params.get("elevation", None)  # picked from the level menu item preview

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return None if do_not_apply else False

        top_distance = 0
        bottom_distance = 0

        # Store level information for status messages
        next_top_level = None
        next_bottom_level = None
        next_level = None

        if self.rbLevel.IsChecked and not elevation:
            # Level mode - snap to next level
            if target == "both":
                if direction == "up":
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
                            1, self.get_locale_string("CannotFindLevelsInDirection"), "error"
                        )
                    return None

                top_distance = next_top_level.Elevation - info["transformed_max"].Z
                bottom_distance = (
                    next_bottom_level.Elevation - info["transformed_min"].Z
                )

                # Validate box dimensions
                if next_top_level.Elevation <= next_bottom_level.Elevation:
                    if not do_not_apply:
                        self.show_status_message(1, self.get_locale_string("WouldCreateInvalidBox"), "error")
                    return None

            elif target == "top":
                if direction == "up":
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
                            1, self.get_locale_string("NoLevelFoundInDirection"), "error"
                        )
                    return None

                top_distance = next_level.Elevation - info["transformed_max"].Z

                # Validate won't go below bottom
                if next_level.Elevation <= info["transformed_min"].Z:
                    if not do_not_apply:
                        self.show_status_message(1, self.get_locale_string("WouldCreateInvalidBox"), "error")
                    return None

            elif target == "bottom":
                if direction == "up":
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
                            1, self.get_locale_string("NoLevelFoundInDirection"), "error"
                        )
                    return None

                bottom_distance = next_level.Elevation - info["transformed_min"].Z

                # Validate won't go above top
                if next_level.Elevation >= info["transformed_max"].Z:
                    if not do_not_apply:
                        self.show_status_message(1, self.get_locale_string("WouldCreateInvalidBox"), "error")
                    return None

        elif elevation:
            if target == "top":
                top_distance = elevation - info["transformed_max"].Z
                # Validate won't go below bottom
                if elevation <= info["transformed_min"].Z:
                    if not do_not_apply:
                        self.show_status_message(
                            1, self.get_locale_string("WouldCreateInvalidBox"), "error"
                        )
                    return None
            elif target == "bottom":
                bottom_distance = elevation - info["transformed_min"].Z
                # Validate won't go above top
                if elevation >= info["transformed_max"].Z:
                    if not do_not_apply:
                        self.show_status_message(
                            1, self.get_locale_string("WouldCreateInvalidBox"), "error"
                        )
                    return None
            elif target == "both":
                # Move entire box - calculate distances for both top and bottom
                current_height = info["transformed_max"].Z - info["transformed_min"].Z
                top_distance = elevation - info["transformed_max"].Z
                # Keep same height
                bottom_distance = (elevation - current_height) - info["transformed_min"].Z
                # Validate new bottom position won't be invalid
                new_bottom = info["transformed_min"].Z + bottom_distance
                new_top = info["transformed_max"].Z + top_distance
                if new_top <= new_bottom:
                    if not do_not_apply:
                        self.show_status_message(
                            1, self.get_locale_string("WouldCreateInvalidBox"), "error"
                        )
                    return None
            else:
                return None

        else:
            # Nudge mode - move by specified amount
            distance = nudge_amount if direction == "up" else -nudge_amount

            if target == "both":
                top_distance = distance
                bottom_distance = distance
            elif target == "top":
                top_distance = distance
            elif target == "bottom":
                bottom_distance = distance

        # Create adjusted box
        if do_not_apply:
            new_box = create_adjusted_box(
                info,
                min_z=bottom_distance,
                max_z=top_distance,
            )
            return new_box

        # Apply the adjustment
        if self.adjust_section_box(
            min_z_change=bottom_distance,
            max_z_change=top_distance,
            min_x_change=0,
            max_x_change=0,
            min_y_change=0,
            max_y_change=0,
        ):
            # Success - show informative message
            if self.rbLevel.IsChecked and not elevation:
                # Level mode - show which level we moved to
                if target == "both":
                    if next_top_level and next_bottom_level:
                        self.show_status_message(
                            1,
                            self.get_locale_string("BoxMovedFormat").format(
                                direction, next_top_level.Name, next_bottom_level.Name
                            ),
                            "success",
                        )
                elif target == "top":
                    if next_level:
                        self.show_status_message(
                            1,
                            self.get_locale_string("TopMovedFormat").format(
                                direction, next_level.Name
                            ),
                            "success",
                        )
                elif target == "bottom":
                    if next_level:
                        self.show_status_message(
                            1,
                            self.get_locale_string("BottomMovedFormat").format(
                                direction, next_level.Name
                            ),
                            "success",
                        )
            elif elevation:
                self.show_status_message(
                    1,
                    self.get_locale_string("TopMovedFormat").format(
                        direction, "as selected"
                    ),
                    "success",
                )
                # Close all popups
                self.popupTopUp.IsOpen = False
                self.popupTopDown.IsOpen = False
                self.popupBottomUp.IsOpen = False
                self.popupBottomDown.IsOpen = False
                self.popupBoxUp.IsOpen = False
                self.popupBoxDown.IsOpen = False
            else:
                # Nudge mode - show nudge amount
                nudge_display = format_length_value(abs(nudge_amount))

                self.show_status_message(
                    1,
                    self.get_locale_string("NudgedFormat").format(target, nudge_display, direction),
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
            operation = self.get_locale_string("Expanded") if is_expand else self.get_locale_string("Shrunk")
            self.show_status_message(
                3,
                operation + " " + self.get_locale_string("ExpandedShrunkByFormat").format(amount_display),
                "success",
            )

    def do_grid_move(self, params):
        """Move section box side to next grid line or by nudge amount."""
        target = params.get("target")  # 'north', 'south', 'east', 'west'
        direction = params.get("direction")  # 'in', 'out'
        direction_name = str(target + direction)
        nudge_amount = params.get("nudge_amount", 0)
        do_not_apply = params.get("do_not_apply", False)

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return None if do_not_apply else False

        cardinal_dir = target

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

        if self.rbGrid.IsChecked:
            # Grid mode - snap to next grid line
            # Get faces and select the face we want to move
            faces = get_section_box_face_info(info)
            _, face_info = select_best_face_for_direction(faces, face_direction)

            if not face_info:
                if not do_not_apply:
                    self.show_status_message(
                        2, self.get_locale_string("CouldNotDetermineFace"), "error"
                    )
                return None

            # Determine the search direction:
            # "-out": search away from center (same as face direction)
            # "-in": search toward center (opposite of face direction)
            search_direction = (
                face_direction if direction == "out" else face_direction.Negate()
            )
            # if view is parallel to grid we won't find a solution, check flattened
            flat = DB.XYZ(search_direction.X, search_direction.Y, 0)
            if flat.GetLength() < TOLERANCE:
                return

            # Find next grid in the search direction
            grid, intersection = find_next_grid_in_direction(
                face_info["center"], search_direction, self.all_grids, TOLERANCE
            )

            if not grid:
                if not do_not_apply:
                    self.show_status_message(
                        2,
                        self.get_locale_string("NoGridFoundFormat").format(direction_name.upper()),
                        "error",
                    )
                return None

            # Calculate how far to move
            move_vector = intersection - face_info["center"]
            move_distance = move_vector.DotProduct(search_direction)

            if abs(move_distance) < TOLERANCE:
                if not do_not_apply:
                    self.show_status_message(2, self.get_locale_string("AlreadyAtGridLine"), "info")
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
                face_direction if direction == "out" else face_direction.Negate()
            )
            # if view is parallel to grid we won't find a solution, check flattened
            flat = DB.XYZ(movement_direction.X, movement_direction.Y, 0)
            if flat.GetLength() < TOLERANCE:
                return

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
            if self.rbGrid.IsChecked:
                # Get grid name
                grid_name = self.get_locale_string("Unknown")
                if grid:
                    if hasattr(grid, "Element"):
                        grid_name = grid.Element.Name
                    elif hasattr(grid, "Name"):
                        grid_name = grid.Name
                direction_display = cardinal_dir.upper()
                self.show_status_message(
                    2,
                    self.get_locale_string("MovedToGridFormat").format(
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
                    self.get_locale_string("NudgedInDirectionFormat").format(
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
                1, self.get_locale_string("CouldNotGetViewRange"), "error"
            )
            return

        new_box = DB.BoundingBoxXYZ()

        if is_section:
            if not crop_box:
                self.show_status_message(
                    3, self.get_locale_string("CouldNotGetCropBox"), "error"
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
                    3, self.get_locale_string("NoCropboxOrElements"), "error"
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
            self.get_locale_string("ApplySectionBoxFormat").format(view_data["view"].Name),
            title=self.get_locale_string("ConfirmSectionBox"),
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
                self.get_locale_string("SectionBoxAlignedFormat").format(view_data["view"].Name),
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
                    self.get_locale_string("CropBoxAlignedFormat").format(view_data["view"].Name),
                    "success",
                )

            else:
                self.show_status_message(3, self.get_locale_string("UnsupportedViewType"), "warning")
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
            state = self.get_locale_string("Activated") if is_now_active else self.get_locale_string("Deactivated")
            self.show_status_message(3, "Box " + state, "success")
        else:
            self.show_status_message(3, self.get_locale_string("BoxToggleFailed"), "error")

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
            state = self.get_locale_string("Hidden") if not was_hidden else self.get_locale_string("Unhidden")
            self.show_status_message(3, "Box " + state, "success")
        except Exception:
            self.show_status_message(3, self.get_locale_string("ErrorInBoxVisibility"), "error")

    def do_align_to_face(self):
        """Align to face"""
        if not isinstance(self.current_view, DB.View3D):
            return
        try:
            align_to_face(doc, uidoc)
            self.show_status_message(3, self.get_locale_string("SectionBoxAlignedToFace"), "success")
        except Exception as ex:
            # User might have cancelled, don't show error for cancellation
            if "cancelled" not in str(ex).lower() and "cancel" not in str(ex).lower():
                self.show_status_message(
                    3, self.get_locale_string("FailedToAlignToFaceFormat").format(str(ex)), "error"
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
                        1, self.get_locale_string("InvalidSectionBoxDimensions"), "error"
                    )
                else:
                    self.show_status_message(
                        3, self.get_locale_string("InvalidSectionBoxDimensions"), "error"
                    )
            elif (
                min_x_change != 0
                or max_x_change != 0
                or min_y_change != 0
                or max_y_change != 0
            ):
                self.show_status_message(2, self.get_locale_string("InvalidSectionBoxDimensions"), "error")
            else:
                self.show_status_message(3, self.get_locale_string("InvalidSectionBoxDimensions"), "error")
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

    # ----------
    # Helper Functions
    # ----------

    def _handle_level_move(self, tag):
        """Helper to handle level movement based on mode."""
        tag = self._normalize_tag(tag)
        target = tag["target"]
        direction = tag["direction"]
        elevation = tag["elevation"]
        try:
            distance = self._get_validated_nudge_amount(self.txtLevelNudgeAmount, 1)
            self.pending_action = {
                "action": "level_move",
                "target": target,
                "direction": direction,
                "nudge_amount": distance,
                "elevation": elevation,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()

        except ValueError:
            self.show_status_message(1, self.get_locale_string("PleaseEnterValidNumber"), "warning")
            return
        except Exception as ex:
            logger.error("Error in level nudge: {}".format(ex))
            self.show_status_message(
                1, self.get_locale_string("AnErrorOccurredFormat").format(str(ex)), "error"
            )
            return

    def _handle_grid_move(self, tag):
        """Helper to handle grid movement."""
        tag = self._normalize_tag(tag)
        target = tag["target"]
        direction = tag["direction"]
        try:
            distance = self._get_validated_nudge_amount(self.txtGridNudgeAmount, 2)
            self.pending_action = {
                "action": "grid_move",
                "target": target,
                "direction": direction,
                "nudge_amount": distance,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()

        except ValueError:
            self.show_status_message(2, self.get_locale_string("PleaseEnterValidNumber"), "warning")
            return
        except Exception as ex:
            logger.error("Error in horizontal nudge: {}".format(ex))
            self.show_status_message(
                2, self.get_locale_string("AnErrorOccurredFormat").format(str(ex)), "error"
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
                    column, self.get_locale_string("PleaseEnterNudgeAmount"), "warning"
                )
                return None

            distance = float(distance_text)
            if column and distance <= 0:
                self.show_status_message(
                    column, self.get_locale_string("AmountMustBeGreaterThanZero"), "warning"
                )
                return None

            return DB.UnitUtils.ConvertToInternalUnits(distance, unit)

        except ValueError:
            self.show_status_message(column, self.get_locale_string("PleaseEnterValidNumber"), "warning")
            return None

    def _normalize_tag(self, tag):
        # Dynamic Buttons
        if isinstance(tag, dict):
            return {
                "target": tag.get("target"),
                "direction": tag.get("direction"),
                "elevation": tag.get("elevation")
            }

        # XAML hardcoded Buttons
        if isinstance(tag, str):
            parts = tag.split("-")

            target = parts[0]
            direction = parts[1]

            return {
                "target": target,
                "direction": direction,
                "elevation": None
            }

    # ----------
    # Button Handlers
    # ----------

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

    def btn_menu_item_click(self, sender, e):
        """Menu item click handling."""
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
                3, self.get_locale_string("PleaseEnterValidNumberForExpansion"), "warning"
            )
        except Exception as ex:
            logger.error("Error in expansion: {}".format(ex))
            self.show_status_message(
                3, self.get_locale_string("AnErrorOccurredWhileExpandingFormat").format(str(ex)), "error"
            )

    def btn_expansion_top_down_click(self, sender, e):
        """Shrink the section box."""
        try:
            amount_text = self.txtExpandAmount.Text.strip()
            if not amount_text:
                self.show_status_message(3, self.get_locale_string("PleaseEnterShrinkAmount"), "warning")
                return

            amount = float(amount_text)
            if amount <= 0:
                self.show_status_message(
                    3, self.get_locale_string("ShrinkAmountMustBeGreaterThanZero"), "warning"
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
                3, self.get_locale_string("PleaseEnterValidNumberForShrink"), "warning"
            )
        except Exception as ex:
            logger.error("Error in shrink: {}".format(ex))
            self.show_status_message(
                3, self.get_locale_string("AnErrorOccurredWhileShrinkingFormat").format(str(ex)), "error"
            )

    def btn_align_box_to_view_click(self, sender, e):
        """Align section box to a selected view."""
        self.current_view = doc.ActiveView
        # Select the view to align
        if isinstance(self.current_view, DB.View3D):
            selected_view = forms.select_views(
                multiple=False,
                filterfunc=is_2d_view,
                title=self.get_locale_string("Select2DViewForSectionBox"),
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
                title=self.get_locale_string("Select3DViewToCopyFrom"),
            )
            if not selected_view:
                return

            info = get_section_box_info(selected_view, DATAFILENAME)
            section_box = info.get("box")
            if not section_box:
                self.show_status_message(3, self.get_locale_string("View3DHasNoSectionBox"), "error")
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
            self.show_status_message(3, self.get_locale_string("CouldNotExtractViewInformation"), "error")
            return

        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_preview_enter(self, sender, e):
        """Show preview when hovering over level, grid, or expansion buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            tag = self._normalize_tag(sender.Tag)

            target = tag["target"]
            direction = tag["direction"]
            elevation = tag["elevation"]

            is_level_button = target in ("top", "bottom", "both")
            is_grid_button = target in ("north", "east", "south", "west")
            is_expansion_button = target == "box"
            is_toggle_button = direction == "toggle"

            box = None

            if is_level_button:
                distance = self._get_validated_nudge_amount(self.txtLevelNudgeAmount)
                if not self.rbLevel.IsChecked and distance is None:
                    return

                params = {
                    "target": target,
                    "direction": direction,
                    "nudge_amount": distance,
                    "do_not_apply": True,
                    "elevation": elevation,
                }
                box = self.do_level_move(params)

            elif is_grid_button:
                distance = self._get_validated_nudge_amount(self.txtGridNudgeAmount)
                if not self.rbGrid.IsChecked and distance is None:
                    return

                params = {
                    "target": target,
                    "direction": direction,
                    "nudge_amount": distance,
                    "do_not_apply": True,
                    "elevation": elevation,
                }
                box = self.do_grid_move(params)

            elif is_expansion_button and not is_toggle_button:
                amount = self._get_validated_nudge_amount(self.txtExpandAmount)
                if amount is None:
                    return

                is_expand = tag["direction"] == "expand"
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
            logger.exception("Error in preview: {}".format(ex))

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

    def btn_top_up_dropdown_click(self, sender, e):
        """Show dropdown menu for top up levels."""
        if not self.rbLevel.IsChecked:
            return
        self.populate_level_menu(self.menuTopUp, "up", "top")
        self.popupTopUp.IsOpen = True

    def btn_top_down_dropdown_click(self, sender, e):
        """Show dropdown menu for top down levels."""
        if not self.rbLevel.IsChecked:
            return
        self.populate_level_menu(self.menuTopDown, "down", "top")
        self.popupTopDown.IsOpen = True

    def btn_bottom_up_dropdown_click(self, sender, e):
        """Show dropdown menu for bottom up levels."""
        if not self.rbLevel.IsChecked:
            return
        self.populate_level_menu(self.menuBottomUp, "up", "bottom")
        self.popupBottomUp.IsOpen = True

    def btn_bottom_down_dropdown_click(self, sender, e):
        """Show dropdown menu for bottom down levels."""
        if not self.rbLevel.IsChecked:
            return
        self.populate_level_menu(self.menuBottomDown, "down", "bottom")
        self.popupBottomDown.IsOpen = True

    def btn_box_up_dropdown_click(self, sender, e):
        """Show dropdown menu for box up levels."""
        if not self.rbLevel.IsChecked:
            return
        self.populate_level_menu(self.menuBoxUp, "up", "both")
        self.popupBoxUp.IsOpen = True

    def btn_box_down_dropdown_click(self, sender, e):
        """Show dropdown menu for box down levels."""
        if not self.rbLevel.IsChecked:
            return
        self.populate_level_menu(self.menuBoxDown, "down", "both")
        self.popupBoxDown.IsOpen = True

    def rb_level_mode_changed(self, sender, e):
        """Handle level/nudge mode radio button change."""
        self.update_dropdown_visibility()

    def form_closed(self, sender, args):
        """Cleanup when form is closed."""
        try:
            # Save window position
            script.save_window_position(self)

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

                # Create a temporary form instance to get locale strings for alerts
                temp_form = SectionBoxNavigatorForm.__new__(SectionBoxNavigatorForm)
                forms.WPFWindow.__init__(temp_form, "SectionBoxNavigator.xaml", handle_esc=False)

                # Ask user if they want to restore
                if forms.alert(
                    temp_form.get_locale_string("StoredSectionBoxFound"),
                    cancel=True,
                    title=temp_form.get_locale_string("RestoreSectionBox"),
                ):
                    with revit.Transaction("Restore SectionBox"):
                        active_view.SetSectionBox(restored_bbox)
            except Exception:
                # Create a temporary form instance to get locale strings
                temp_form = SectionBoxNavigatorForm.__new__(SectionBoxNavigatorForm)
                forms.WPFWindow.__init__(temp_form, "SectionBoxNavigator.xaml", handle_esc=False)
                forms.alert(
                    temp_form.get_locale_string("NoSectionBoxMessage"),
                    title=temp_form.get_locale_string("NoSectionBoxTitle"),
                    exitscript=True,
                )

        sb_form = SectionBoxNavigatorForm("SectionBoxNavigator.xaml")

    except Exception as ex:
        logger.exception("Error launching form: {}".format(ex))
        # Create a temporary form instance to get locale strings
        try:
            temp_form = SectionBoxNavigatorForm.__new__(SectionBoxNavigatorForm)
            forms.WPFWindow.__init__(temp_form, "SectionBoxNavigator.xaml", handle_esc=False)
            error_title = temp_form.get_locale_string("ErrorTitle")
            error_msg = temp_form.get_locale_string("AnErrorOccurredFormat").format(str(ex))
        except Exception:
            error_title = "Error"
            error_msg = "An error occurred: {}".format(str(ex))
        forms.alert(error_msg, title=error_title)
