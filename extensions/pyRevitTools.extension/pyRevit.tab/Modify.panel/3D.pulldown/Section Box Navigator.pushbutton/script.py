# -*- coding: utf-8 -*-
# type: ignore
"""Section Box Navigator - Modeless window for section box navigation."""

from pyrevit import revit, script, forms
from pyrevit.framework import System
from pyrevit.revit import events
from pyrevit.compat import get_elementid_value_func
from pyrevit import DB, UI
from pyrevit import traceback

from sectionbox_navigation import (
    get_all_levels,
    get_all_grids,
    get_cardinal_direction,
    get_next_level_above,
    get_next_level_below,
    find_next_grid_in_direction,
)
from sectionbox_utils import is_2d_view, get_view_range_and_crop
from sectionbox_actions import toggle, hide, align_to_face
from sectionbox_geometry import (
    get_section_box_info,
    get_section_box_face_info,
    select_best_face_for_direction,
    make_xy_transform_only,
)

get_elementid_value = get_elementid_value_func()

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
ufu = DB.UnitFormatUtils

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
        logger.error("Error creating preview mesh: {}".format(traceback.format_exc()))
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

    # Validate dimesions
    if new_max.X <= new_min.X or new_max.Y <= new_min.Y or new_max.Z <= new_min.Z:
        return None

    new_box = DB.BoundingBoxXYZ()
    new_box.Min = new_min
    new_box.Max = new_max
    new_box.Transform = transform

    return new_box


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
        self.all_levels = get_all_levels(doc)
        self.all_grids = get_all_grids(doc)
        self.preview_server = None
        self.preview_box = None

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
        self.txtNudgeAmount.Text = str(round(default_nudge_value, 3))
        self.txtNudgeUnit.Text = length_unit_symbol_label
        self.txtExpandAmount.Text = str(round(default_nudge_value, 3))
        self.txtExpandUnit.Text = length_unit_symbol_label
        self.txtGridNudgeAmount.Text = str(round(default_nudge_value, 3))
        self.txtGridNudgeUnit.Text = length_unit_symbol_label

        self.update_info()

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
            self.current_view = doc.ActiveView

            if (
                not isinstance(self.current_view, DB.View3D)
                or not self.current_view.IsSectionBoxActive
            ):
                self.txtTopLevel.Text = "Top: No section box active"
                self.txtTopPosition.Text = ""
                self.txtBottomLevel.Text = "Bottom: No section box active"
                self.txtBottomPosition.Text = ""
                return

            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return

            transformed_max = info["transformed_max"]
            transformed_min = info["transformed_min"]

            # Get levels
            top_level, top_level_elevation = get_next_level_above(
                transformed_max.Z, self.all_levels, TOLERANCE
            )
            bottom_level, bottom_level_elevation = get_next_level_below(
                transformed_min.Z, self.all_levels, TOLERANCE
            )

            if top_level_elevation:
                top_level_elevation = ufu.Format(
                    doc.GetUnits(), DB.SpecTypeId.Length, top_level_elevation, False
                )
            if bottom_level_elevation:
                bottom_level_elevation = ufu.Format(
                    doc.GetUnits(), DB.SpecTypeId.Length, bottom_level_elevation, False
                )

            # Update top info
            if top_level:
                self.txtTopLevel.Text = "Top: Next level up: {} @ {}".format(
                    top_level.Name, top_level_elevation
                )
            else:
                self.txtTopLevel.Text = "Top: No level above"

            top = ufu.Format(
                doc.GetUnits(), DB.SpecTypeId.Length, transformed_max.Z, False
            )
            self.txtTopPosition.Text = "Position: {}".format(top)

            # Update bottom info
            if bottom_level:
                self.txtBottomLevel.Text = "Bottom: Next level down: {} @ {}".format(
                    bottom_level.Name, bottom_level_elevation
                )
            else:
                self.txtBottomLevel.Text = "Bottom: No level below"

            bottom = ufu.Format(
                doc.GetUnits(), DB.SpecTypeId.Length, transformed_min.Z, False
            )
            self.txtBottomPosition.Text = "Position: {}".format(bottom)

        except Exception:
            logger.error("Error updating info: {}".format(traceback.format_exc()))

    def execute_action(self, params):
        """Execute an action in Revit context."""
        try:
            action_type = params["action"]

            if action_type == "move_to_level":
                self.do_move_to_level(params)
            elif action_type == "nudge":
                self.do_nudge(params)
            elif action_type == "toggle":
                self.do_toggle()
            elif action_type == "hide":
                self.do_hide()
            elif action_type == "align_to_face":
                self.do_align_to_face()
            elif action_type == "expand_shrink":
                self.do_expand_shrink(params)
            elif action_type == "align_to_view":
                self.do_align_to_view(params)
            elif action_type == "grid_move":
                self.do_grid_move(params)
            elif action_type == "grid_nudge":
                self.do_grid_nudge(params)

            # Update info after action
            self.Dispatcher.Invoke(System.Action(self.update_info))

        except Exception as ex:
            logger.error("Error executing action: {}".format(ex))

    def do_move_to_level(self, params):
        """Move section box to level."""
        top_level = params.get("top_level")
        bottom_level = params.get("bottom_level")

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        adjust_top = top_level is not None
        adjust_bottom = bottom_level is not None

        # Calculate distances
        top_distance = 0
        bottom_distance = 0

        if adjust_top:
            top_distance = top_level.Elevation - info["transformed_max"].Z

        if adjust_bottom:
            bottom_distance = bottom_level.Elevation - info["transformed_min"].Z

        self.adjust_section_box(
            min_z_change=bottom_distance if adjust_bottom else 0,
            max_z_change=top_distance if adjust_top else 0,
            min_x_change=0,
            max_x_change=0,
            min_y_change=0,
            max_y_change=0,
        )

    def do_nudge(self, params):
        """Nudge section box."""
        distance_mm = params.get("distance", 0)
        adjust_top = params.get("adjust_top", False)
        adjust_bottom = params.get("adjust_bottom", False)

        self.adjust_section_box(
            min_z_change=distance_mm if adjust_bottom else 0,
            max_z_change=distance_mm if adjust_top else 0,
            min_x_change=0,
            max_x_change=0,
            min_y_change=0,
            max_y_change=0,
        )

    def do_expand_shrink(self, params):
        """Expand or shrink the section box in all directions."""
        amount = params.get("amount", 0)
        is_expand = params.get("is_expand", True)

        # Calculate the adjustment (negative for shrink)
        adjustment = amount if is_expand else -amount

        self.adjust_section_box(
            min_x_change=-adjustment,
            max_x_change=adjustment,
            min_y_change=-adjustment,
            max_y_change=adjustment,
            min_z_change=-adjustment,
            max_z_change=adjustment,
        )

    def do_grid_move(self, params):
        """Move section box side to next grid line."""
        direction_name = params.get("direction")  # 'north-out', 'south-in', etc.
        do_not_apply = params.get("do_not_apply", False)

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        # Parse direction into cardinal direction and in/out modifier
        parts = direction_name.split("-")
        cardinal_dir = parts[0]  # 'north', 'south', 'east', 'west'
        modifier = parts[1] if len(parts) > 1 else "out"  # 'in' or 'out'

        # Get cardinal direction vector - this represents which FACE we want to move
        face_direction = get_cardinal_direction(cardinal_dir)

        # Get faces and select the face we want to move (always based on cardinal_dir)
        faces = get_section_box_face_info(info)
        _, face_info = select_best_face_for_direction(faces, face_direction)

        if not face_info:
            forms.alert("Could not determine face to move.", title="Error")
            return

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
                forms.alert(
                    "No grid found in {} direction.".format(direction_name.upper()),
                    title="No Grid Found",
                )
            return

        # Calculate how far to move
        move_vector = intersection - face_info["center"]
        move_distance = move_vector.DotProduct(search_direction)

        if abs(move_distance) < TOLERANCE:
            forms.alert("Already at grid line.", title="Info")
            return

        # Convert to local coordinates
        transform = info["transform"]
        inverse_transform = transform.Inverse

        local_move_vector = inverse_transform.OfVector(move_vector)
        local_face_direction = inverse_transform.OfVector(face_direction)

        # Determine which axis the face is on (not the movement!)
        abs_x = abs(local_face_direction.X)
        abs_y = abs(local_face_direction.Y)

        min_x_change = 0
        max_x_change = 0
        min_y_change = 0
        max_y_change = 0

        # Determine which side to move based on which face we selected
        if abs_x > abs_y:
            # Face is on X axis
            if local_face_direction.X > 0:
                # Moving max X face
                max_x_change = local_move_vector.X
            else:
                # Moving min X face
                min_x_change = local_move_vector.X
        else:
            # Face is on Y axis
            if local_face_direction.Y > 0:
                # Moving max Y face
                max_y_change = local_move_vector.Y
            else:
                # Moving min Y face
                min_y_change = local_move_vector.Y

        if do_not_apply:
            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return False

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

        self.adjust_section_box(
            min_x_change=min_x_change,
            max_x_change=max_x_change,
            min_y_change=min_y_change,
            max_y_change=max_y_change,
            min_z_change=0,
            max_z_change=0,
        )

    def do_grid_nudge(self, params):
        """Nudge section box horizontally by amount in cardinal direction."""
        direction_name = params.get("direction")  # 'north-out', 'south-in', etc.
        distance = params.get("distance", 0)
        do_not_apply = params.get("do_not_apply", False)

        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        # Parse direction into cardinal direction and in/out modifier
        parts = direction_name.split("-")
        cardinal_dir = parts[0]  # 'north', 'south', 'east', 'west'
        modifier = parts[1] if len(parts) > 1 else "out"  # 'in' or 'out'

        # Get the cardinal direction - this represents which FACE we want to move
        face_direction = get_cardinal_direction(cardinal_dir)

        # Determine the actual movement direction:
        # "-out": move away from center (same as face direction)
        # "-in": move toward center (opposite of face direction)
        movement_direction = (
            face_direction if modifier == "out" else face_direction.Negate()
        )

        # Transform to local coordinates
        transform = info["transform"]
        inverse_transform = transform.Inverse

        # Get which face we're moving in local coordinates
        local_face_direction = inverse_transform.OfVector(face_direction)
        # Get the movement direction in local coordinates
        local_movement = inverse_transform.OfVector(movement_direction).Multiply(
            distance
        )

        min_x_change = 0
        max_x_change = 0
        min_y_change = 0
        max_y_change = 0

        # Determine which axis the face is on
        abs_x = abs(local_face_direction.X)
        abs_y = abs(local_face_direction.Y)

        if abs_x > abs_y:
            # Face is on X axis
            if local_face_direction.X > 0:
                # Moving max X face
                max_x_change = local_movement.X
            else:
                # Moving min X face
                min_x_change = local_movement.X
        else:
            # Face is on Y axis
            if local_face_direction.Y > 0:
                # Moving max Y face
                max_y_change = local_movement.Y
            else:
                # Moving min Y face
                min_y_change = local_movement.Y

        if do_not_apply:
            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return False

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

        self.adjust_section_box(
            min_x_change=min_x_change,
            max_x_change=max_x_change,
            min_y_change=min_y_change,
            max_y_change=max_y_change,
            min_z_change=0,
            max_z_change=0,
        )

    def do_align_to_view(self, params):
        """Align section box to a 2D view's range and crop."""
        view_data = params.get("view_data")
        if not view_data:
            return

        top_elevation = view_data.get("top_elevation", None)
        bottom_elevation = view_data.get("bottom_elevation", None)
        crop_box = view_data.get("crop_box", None)
        is_section = view_data.get("is_section", False)

        if not is_section and (top_elevation is None or bottom_elevation is None):
            forms.alert("Could not get view range information.", title="Error")
            return

        new_box = DB.BoundingBoxXYZ()

        if is_section:
            if not crop_box:
                forms.alert("Could not get crop box from section.", title="Error")
                return
            new_box = crop_box

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
                forms.alert("No cropbox or elements found to extend scopebox to")
                return
            boxes = [el.get_BoundingBox(source_view) for el in elements]
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

    def do_toggle(self):
        """Toggle section box."""
        toggle(doc, DATAFILENAME)

    def do_hide(self):
        """Hide or Unhide section box."""
        hide(doc)

    def do_align_to_face(self):
        """Align to face"""
        align_to_face(doc, uidoc)

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
            forms.alert("Invalid section box dimensions.", title="Error")
            return False

        with revit.Transaction("Adjust Section Box"):
            self.current_view.SetSectionBox(new_box)

        return True

    def show_preview(self, preview_type="nudge", params=None):
        """Show preview of adjusted section box."""
        if not self.preview_server or not self.chkPreview.IsChecked:
            return

        try:
            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return

            preview_box = None

            if preview_type == "nudge":
                distance_top = params.get("distance_top", 0)
                distance_bottom = params.get("distance_bottom", 0)
                adjust_top = params.get("adjust_top", False)
                adjust_bottom = params.get("adjust_bottom", False)

                preview_box = create_adjusted_box(
                    info,
                    min_z=distance_bottom if adjust_bottom else 0,
                    max_z=distance_top if adjust_top else 0,
                )

            elif preview_type == "level":
                distance_top = params.get("distance_top", 0)
                distance_bottom = params.get("distance_bottom", 0)
                adjust_top = params.get("adjust_top", False)
                adjust_bottom = params.get("adjust_bottom", False)

                preview_box = create_adjusted_box(
                    info,
                    min_z=distance_bottom if adjust_bottom else 0,
                    max_z=distance_top if adjust_top else 0,
                )

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

    # Button Handlers

    def btn_top_up_click(self, sender, e):
        """Move top up to next level."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        next_level, _ = get_next_level_above(
            info["transformed_max"].Z, self.all_levels, TOLERANCE
        )
        if not next_level:
            forms.alert("No level found above", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_level,
            "bottom_level": None,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_top_down_click(self, sender, e):
        """Move top down to next level."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        next_level, _ = get_next_level_below(
            info["transformed_max"].Z, self.all_levels, TOLERANCE
        )
        if not next_level:
            forms.alert("No level found below", title="Error")
            return

        if next_level.Elevation <= info["transformed_min"].Z:
            forms.alert("Would create invalid box", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_level,
            "bottom_level": None,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_bottom_up_click(self, sender, e):
        """Move bottom up to next level."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        next_level, _ = get_next_level_above(
            info["transformed_min"].Z, self.all_levels, TOLERANCE
        )
        if not next_level:
            forms.alert("No level found above", title="Error")
            return

        if next_level.Elevation >= info["transformed_max"].Z:
            forms.alert("Would create invalid box", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": None,
            "bottom_level": next_level,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_bottom_down_click(self, sender, e):
        """Move bottom down to next level."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        next_level, _ = get_next_level_below(
            info["transformed_min"].Z, self.all_levels, TOLERANCE
        )
        if not next_level:
            forms.alert("No level found below", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": None,
            "bottom_level": next_level,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_box_up_click(self, sender, e):
        """Move entire box up to next levels."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        next_top, _ = get_next_level_above(
            info["transformed_max"].Z, self.all_levels, TOLERANCE
        )
        next_bottom, _ = get_next_level_above(
            info["transformed_min"].Z, self.all_levels, TOLERANCE
        )

        if not next_top or not next_bottom:
            forms.alert("Cannot find levels above", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_top,
            "bottom_level": next_bottom,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_box_down_click(self, sender, e):
        """Move entire box down to next levels."""
        info = get_section_box_info(self.current_view, DATAFILENAME)
        if not info:
            return

        next_top, _ = get_next_level_below(
            info["transformed_max"].Z, self.all_levels, TOLERANCE
        )
        next_bottom, _ = get_next_level_below(
            info["transformed_min"].Z, self.all_levels, TOLERANCE
        )

        if not next_top or not next_bottom:
            forms.alert("Cannot find levels below", title="Error")
            return

        if next_top.Elevation <= next_bottom.Elevation:
            forms.alert("Would create invalid box", title="Error")
            return

        self.pending_action = {
            "action": "move_to_level",
            "top_level": next_top,
            "bottom_level": next_bottom,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_nudge_top_up_click(self, sender, e):
        """Nudge top up."""
        try:
            distance_text = self.txtNudgeAmount.Text.strip()
            if not distance_text:
                forms.alert("Please enter a nudge amount", title="Input Required")
                return

            distance = float(distance_text)
            if distance <= 0:
                forms.alert(
                    "Nudge amount must be greater than 0", title="Invalid Input"
                )
                return

            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": True,
                "adjust_bottom": False,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert(
                "Please enter a valid number for nudge amount", title="Invalid Input"
            )
        except Exception as ex:
            logger.error("Error in nudge top up: {}".format(ex))
            forms.alert(
                "An error occurred while nudging: {}".format(str(e)), title="Error"
            )

    def btn_nudge_top_down_click(self, sender, e):
        """Nudge top down."""
        try:
            distance_text = self.txtNudgeAmount.Text.strip()
            if not distance_text:
                forms.alert("Please enter a nudge amount", title="Input Required")
                return

            distance = float(distance_text)
            if distance <= 0:
                forms.alert(
                    "Nudge amount must be greater than 0", title="Invalid Input"
                )
                return

            distance = -DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": True,
                "adjust_bottom": False,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert(
                "Please enter a valid number for nudge amount", title="Invalid Input"
            )
        except Exception as ex:
            logger.error("Error in nudge top down: {}".format(ex))
            forms.alert(
                "An error occurred while nudging: {}".format(str(e)), title="Error"
            )

    def btn_nudge_bottom_up_click(self, sender, e):
        """Nudge bottom up."""
        try:
            distance_text = self.txtNudgeAmount.Text.strip()
            if not distance_text:
                forms.alert("Please enter a nudge amount", title="Input Required")
                return

            distance = float(distance_text)
            if distance <= 0:
                forms.alert(
                    "Nudge amount must be greater than 0", title="Invalid Input"
                )
                return

            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": False,
                "adjust_bottom": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert(
                "Please enter a valid number for nudge amount", title="Invalid Input"
            )
        except Exception as ex:
            logger.error("Error in nudge bottom up: {}".format(ex))
            forms.alert(
                "An error occurred while nudging: {}".format(str(e)), title="Error"
            )

    def btn_nudge_bottom_down_click(self, sender, e):
        """Nudge bottom down."""
        try:
            distance_text = self.txtNudgeAmount.Text.strip()
            if not distance_text:
                forms.alert("Please enter a nudge amount", title="Input Required")
                return

            distance = float(distance_text)
            if distance <= 0:
                forms.alert(
                    "Nudge amount must be greater than 0", title="Invalid Input"
                )
                return

            distance = -DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)
            self.pending_action = {
                "action": "nudge",
                "distance": distance,
                "adjust_top": False,
                "adjust_bottom": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert(
                "Please enter a valid number for nudge amount", title="Invalid Input"
            )
        except Exception as ex:
            logger.error("Error in nudge bottom down: {}".format(ex))
            forms.alert(
                "An error occurred while nudging: {}".format(str(e)), title="Error"
            )

    def btn_expansion_top_up_click(self, sender, e):
        """Expand the section box."""
        try:
            amount_text = self.txtExpandAmount.Text.strip()
            if not amount_text:
                forms.alert("Please enter an expansion amount", title="Input Required")
                return

            amount = float(amount_text)
            if amount <= 0:
                forms.alert(
                    "Expansion amount must be greater than 0", title="Invalid Input"
                )
                return

            amount = DB.UnitUtils.ConvertToInternalUnits(amount, length_unit)
            self.pending_action = {
                "action": "expand_shrink",
                "amount": amount,
                "is_expand": True,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        except ValueError:
            forms.alert(
                "Please enter a valid number for expansion amount",
                title="Invalid Input",
            )
        except Exception as ex:
            logger.error("Error in expansion: {}".format(ex))
            forms.alert(
                "An error occurred while expanding: {}".format(str(e)), title="Error"
            )

    def btn_expansion_top_down_click(self, sender, e):
        """Shrink the section box."""
        try:
            amount_text = self.txtExpandAmount.Text.strip()
            if not amount_text:
                forms.alert("Please enter a shrink amount", title="Input Required")
                return

            amount = float(amount_text)
            if amount <= 0:
                forms.alert(
                    "Shrink amount must be greater than 0", title="Invalid Input"
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
            forms.alert(
                "Please enter a valid number for shrink amount", title="Invalid Input"
            )
        except Exception as ex:
            logger.error("Error in shrink: {}".format(ex))
            forms.alert(
                "An error occurred while shrinking: {}".format(str(e)), title="Error"
            )

    def btn_align_box_to_view_click(self, sender, e):
        """Align section box to a selected 2D view."""
        # Select a 2D view
        selected_view = forms.select_views(
            multiple=False,
            filterfunc=is_2d_view,
            title="Select 2D View for Section Box",
        )

        if not selected_view:
            return

        # Get view range and crop information
        view_data = get_view_range_and_crop(selected_view, doc)

        if not view_data:
            forms.alert("Could not extract view information.", title="Error")
            return

        # Queue the action to be executed in Revit context
        self.pending_action = {
            "action": "align_to_view",
            "view_data": view_data,
        }
        self.event_handler.parameters = self.pending_action
        self.ext_event.Raise()

    def btn_preview_nudge_enter(self, sender, e):
        """Show preview when hovering over nudge buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            distance = float(self.txtNudgeAmount.Text)
            distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)

            button_content = sender.Content
            adjust_top = "Top" in button_content
            adjust_bottom = "Bottom" in button_content

            if "-" in button_content:
                distance = -distance

            params = {
                "distance_top": distance,
                "distance_bottom": distance,
                "adjust_top": adjust_top,
                "adjust_bottom": adjust_bottom,
            }
            self.show_preview("nudge", params)
        except Exception as ex:
            logger.warning("Error in nudge preview: {}".format(ex))

    def btn_preview_level_box_enter(self, sender, e):
        """Show preview when hovering over level buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            info = get_section_box_info(self.current_view, DATAFILENAME)
            if not info:
                return

            button_content = sender.Content

            # Determine which button was hovered
            is_top = "Top" in button_content
            is_bottom = "Bottom" in button_content
            is_box = "Box" in button_content
            is_up = "↑" in button_content

            distance_top = 0
            distance_bottom = 0
            adjust_top = False
            adjust_bottom = False

            if is_box:
                # Box up or down - move both
                if is_up:
                    next_top, _ = get_next_level_above(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )
                    next_bottom, _ = get_next_level_above(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )
                    if next_top and next_bottom:
                        distance_top = next_top.Elevation - info["transformed_max"].Z
                        distance_bottom = (
                            next_bottom.Elevation - info["transformed_min"].Z
                        )
                        adjust_top = True
                        adjust_bottom = True
                else:
                    next_top, _ = get_next_level_below(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )
                    next_bottom, _ = get_next_level_below(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )
                    if next_top and next_bottom:
                        distance_top = next_top.Elevation - info["transformed_max"].Z
                        distance_bottom = (
                            next_bottom.Elevation - info["transformed_min"].Z
                        )
                        adjust_top = True
                        adjust_bottom = True
            elif is_top:
                # Top up or down
                if is_up:
                    next_level, _ = get_next_level_above(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )
                else:
                    next_level, _ = get_next_level_below(
                        info["transformed_max"].Z, self.all_levels, TOLERANCE
                    )

                if next_level:
                    distance_top = next_level.Elevation - info["transformed_max"].Z
                    adjust_top = True
            elif is_bottom:
                # Bottom up or down
                if is_up:
                    next_level, _ = get_next_level_above(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )
                else:
                    next_level, _ = get_next_level_below(
                        info["transformed_min"].Z, self.all_levels, TOLERANCE
                    )

                if next_level:
                    distance_bottom = next_level.Elevation - info["transformed_min"].Z
                    adjust_bottom = True

            if adjust_top or adjust_bottom:
                params = {
                    "distance_top": distance_top,
                    "distance_bottom": distance_bottom,
                    "adjust_top": adjust_top,
                    "adjust_bottom": adjust_bottom,
                }
                self.show_preview("level", params)

        except Exception as ex:
            logger.warning("Error in level preview: {}".format(ex))

    def btn_preview_expansion_enter(self, sender, e):
        """Show preview when hovering over expansion buttons."""
        if not self.chkPreview.IsChecked:
            return

        try:
            amount = float(self.txtExpandAmount.Text)
            amount = DB.UnitUtils.ConvertToInternalUnits(amount, length_unit)

            button_content = sender.Content
            is_expand = "Expand" in button_content

            # Calculate adjustment (negative for shrink)
            adjustment = amount if is_expand else -amount

            params = {
                "adjustment": adjustment,
            }
            self.show_preview("expand_shrink", params)

        except Exception as ex:
            logger.warning("Error in expansion preview: {}".format(ex))

    def btn_preview_grid_enter(self, sender, e):
        """Show preview when hovering over buttons."""
        if not self.chkPreview.IsChecked:
            return
        try:
            is_grid_mode = self.rbGrid.IsChecked

            if is_grid_mode:
                # Grid mode - move to next grid
                params = {
                    "direction": sender.Tag,
                    "do_not_apply": True,
                }
                box = self.do_grid_move(params)
            else:
                # Nudge mode - move by amount
                try:
                    distance_text = self.txtGridNudgeAmount.Text.strip()
                    if not distance_text:
                        forms.alert(
                            "Please enter a nudge amount", title="Input Required"
                        )
                        return

                    distance = float(distance_text)
                    if distance <= 0:
                        forms.alert(
                            "Nudge amount must be greater than 0", title="Invalid Input"
                        )
                        return

                    distance = DB.UnitUtils.ConvertToInternalUnits(
                        distance, length_unit
                    )

                    params = {
                        "direction": sender.Tag,
                        "distance": distance,
                        "do_not_apply": True,
                    }
                    box = self.do_grid_nudge(params)

                except ValueError:
                    forms.alert("Please enter a valid number", title="Invalid Input")
                    return
            if box:
                params = {
                    "box": box,
                }
                self.show_preview("box", params)
        except Exception as ex:
            logger.warning("Error in general preview grid: {}".format(ex))

    def btn_preview_enter(self, sender, e):
        """Show preview when hovering over buttons."""
        if not self.chkPreview.IsChecked:
            return
        try:
            params = {
                "distance_top": 0,
                "distance_bottom": 0,
                "adjust_top": 0,
                "adjust_bottom": 0,
            }
            self.show_preview("nudge", params)
        except Exception as ex:
            logger.warning("Error in general preview: {}".format(ex))

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

    def btn_refresh_click(self, sender, e):
        """Manually refresh the information."""
        self.all_levels = get_all_levels(doc)
        self.all_grids = get_all_grids(doc)
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

    def _handle_grid_move(self, direction):
        """Helper to handle grid movement."""
        is_grid_mode = self.rbGrid.IsChecked

        if is_grid_mode:
            # Grid mode - move to next grid
            self.pending_action = {
                "action": "grid_move",
                "direction": direction,
            }
            self.event_handler.parameters = self.pending_action
            self.ext_event.Raise()
        else:
            # Nudge mode - move by amount
            try:
                distance_text = self.txtGridNudgeAmount.Text.strip()
                if not distance_text:
                    forms.alert("Please enter a nudge amount", title="Input Required")
                    return

                distance = float(distance_text)
                if distance <= 0:
                    forms.alert(
                        "Nudge amount must be greater than 0", title="Invalid Input"
                    )
                    return

                distance = DB.UnitUtils.ConvertToInternalUnits(distance, length_unit)

                self.pending_action = {
                    "action": "grid_nudge",
                    "direction": direction,
                    "distance": distance,
                }
                self.event_handler.parameters = self.pending_action
                self.ext_event.Raise()

            except ValueError:
                forms.alert("Please enter a valid number", title="Invalid Input")
                return
            except Exception as ex:
                logger.error("Error in horizontal nudge: {}".format(ex))
                forms.alert("An error occurred: {}".format(str(ex)), title="Error")
                return

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
            logger.error("Error during cleanup: {}".format(traceback.format_exc()))


# ---------
# Run main
# ---------

if __name__ == "__main__":
    try:
        # Check if section box is active
        if not isinstance(active_view, DB.View3D) or not active_view.IsSectionBoxActive:
            try:
                view_boxes = script.load_data(DATAFILENAME)
                bbox_data = view_boxes[get_elementid_value(active_view.Id)]
                restored_bbox = revit.deserialize(bbox_data)

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
                    "The current view isn't 3D or doesn't have an active section box.",
                    title="No Section Box",
                    exitscript=True,
                )

        sb_form = SectionBoxNavigatorForm("SectionBoxNavigator.xaml")

    except Exception as ex:
        logger.exception("Error launching form: {}".format(ex))
        forms.alert("An error occurred: {}".format(str(ex)), title="Error")
