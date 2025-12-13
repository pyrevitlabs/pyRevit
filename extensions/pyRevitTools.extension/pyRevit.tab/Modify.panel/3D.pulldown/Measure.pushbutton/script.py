# -*- coding: utf-8 -*-
from collections import deque
from math import pi, atan, sqrt
from pyrevit import HOST_APP, revit, forms, script
from pyrevit import UI, DB
from Autodesk.Revit.Exceptions import InvalidOperationException

logger = script.get_logger()

doc = HOST_APP.doc
uidoc = revit.uidoc
# Length
length_format_options = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length)
length_unit = length_format_options.GetUnitTypeId()
length_unit_label = DB.LabelUtils.GetLabelForUnit(length_unit)
length_unit_symbol = length_format_options.GetSymbolTypeId()
length_unit_symbol_label = None
if not length_unit_symbol.Empty():
    length_unit_symbol_label = DB.LabelUtils.GetLabelForSymbol(length_unit_symbol)
# Slope
slope_format_options = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Slope)
slope_unit = slope_format_options.GetUnitTypeId()
slope_unit_label = DB.LabelUtils.GetLabelForUnit(slope_unit)
slope_unit_symbol = slope_format_options.GetSymbolTypeId()
slope_unit_symbol_label = None
if not slope_unit_symbol.Empty():
    slope_unit_symbol_label = DB.LabelUtils.GetLabelForSymbol(slope_unit_symbol)

# Global variables
measure_window = None
measure_handler_event = None
dc3d_server = None
MAX_HISTORY = 5
measurement_history = deque(maxlen=MAX_HISTORY)

# Visual aid configuration
CUBE_SIZE = 0.3  # in feet (cube side length)
LINE_COLOR_X = DB.ColorWithTransparency(255, 0, 0, 0)  # Red
LINE_COLOR_Y = DB.ColorWithTransparency(0, 255, 0, 0)  # Green
LINE_COLOR_Z = DB.ColorWithTransparency(0, 0, 255, 0)  # Blue
LINE_COLOR_DIAG = DB.ColorWithTransparency(200, 200, 0, 0)  # Dark Yellow
CUBE_COLOR = DB.ColorWithTransparency(255, 165, 0, 50)  # Orange


def calculate_distances(point1, point2):
    """Calculate dx, dy, dz, diagonal distance, and slope angle between two points.

    Args:
        point1 (DB.XYZ): First point
        point2 (DB.XYZ): Second point

    Returns:
        tuple: (dx, dy, dz, diagonal, slope) all in internal units (feet, rad)
    """
    dx = abs(point2.X - point1.X)
    dy = abs(point2.Y - point1.Y)
    dz = abs(point2.Z - point1.Z)
    diagonal = point1.DistanceTo(point2)

    horizontal = sqrt(dx ** 2 + dy ** 2)

    if horizontal == 0:
        slope = pi / 2.0  # 90 degrees (vertical)
    else:
        slope = atan(dz / horizontal)

    return dx, dy, dz, diagonal, slope


def format_distance(value_internal):
    return DB.UnitFormatUtils.Format(
        doc.GetUnits(),
        DB.SpecTypeId.Length,
        value_internal,
        False,
    )


def format_slope(value_internal):
    return DB.UnitFormatUtils.Format(
        doc.GetUnits(),
        DB.SpecTypeId.Slope,
        value_internal,
        False,
    )


def format_point(point):
    x = DB.UnitUtils.ConvertFromInternalUnits(point.X, length_unit)
    y = DB.UnitUtils.ConvertFromInternalUnits(point.Y, length_unit)
    z = DB.UnitUtils.ConvertFromInternalUnits(point.Z, length_unit)
    return "({:.2f}, {:.2f}, {:.2f})".format(x, y, z)


def create_cube_mesh(center, size, color):
    """Create a cube mesh centered at the given point."""
    half_size = size / 2.0

    bb = DB.BoundingBoxXYZ()
    bb.Min = DB.XYZ(-half_size, -half_size, -half_size)
    bb.Max = DB.XYZ(half_size, half_size, half_size)
    bb.Transform = DB.Transform.CreateTranslation(center)

    mesh = revit.dc3dserver.Mesh.from_boundingbox(bb, color, black_edges=True)

    return mesh


def create_line_mesh(start, end, color):
    """Create a line mesh between two points."""
    edge = revit.dc3dserver.Edge(start, end, color)
    mesh = revit.dc3dserver.Mesh([edge], [])

    return mesh


def create_and_show_point_mesh(point1):
    """Immediately show the first selected point"""
    global dc3d_server
    try:
        new_meshes = []
        new_meshes.append(create_cube_mesh(point1, CUBE_SIZE, CUBE_COLOR))
        if dc3d_server:
            existing_meshes = dc3d_server.meshes if dc3d_server.meshes else []
            dc3d_server.meshes = existing_meshes + new_meshes
            uidoc.RefreshActiveView()
    except Exception as ex:
        logger.error("Error creating point mesh: {}".format(ex))


def create_measurement_meshes(point1, point2):
    """Create all visual aid meshes for a measurement."""
    meshes = []

    # Create cubes at measurement points
    # Mesh for point1 already immediately created and shown on selection
    meshes.append(create_cube_mesh(point2, CUBE_SIZE, CUBE_COLOR))

    # Determine the work plane (use the lowest Z for X and Y lines)
    lower_z = min(point1.Z, point2.Z)

    # X direction line (red)
    x_start = DB.XYZ(point1.X, point1.Y, lower_z)
    x_end = DB.XYZ(point2.X, point1.Y, lower_z)
    if x_start.DistanceTo(x_end) > 0.001:
        meshes.append(create_line_mesh(x_start, x_end, LINE_COLOR_X))

    # Y direction line (green)
    y_start = DB.XYZ(point2.X, point1.Y, lower_z)
    y_end = DB.XYZ(point2.X, point2.Y, lower_z)
    if y_start.DistanceTo(y_end) > 0.001:
        meshes.append(create_line_mesh(y_start, y_end, LINE_COLOR_Y))

    # Z direction line (blue)
    higher_point = point1 if point1.Z > point2.Z else point2
    z_start = DB.XYZ(higher_point.X, higher_point.Y, lower_z)
    z_end = DB.XYZ(higher_point.X, higher_point.Y, max(point1.Z, point2.Z))
    if z_start.DistanceTo(z_end) > 0.001:
        meshes.append(create_line_mesh(z_start, z_end, LINE_COLOR_Z))

    # Diagonal line (yellow)
    if point1.DistanceTo(point2) > 0.001:
        meshes.append(create_line_mesh(point1, point2, LINE_COLOR_DIAG))

    return meshes


def validate_3d_view():
    """Validate that the active view is a 3D view."""
    active_view = uidoc.ActiveView
    if not isinstance(active_view, DB.View3D):
        forms.alert(
            "Please activate a 3D view before using the 3D Measure tool.",
            title="3D View Required",
            exitscript=True,
        )
        return False
    return True


def perform_measurement():
    """Perform the measurement workflow: pick points, create aids, update UI."""
    # Add 3D view validation
    if not validate_3d_view():
        return

    try:
        with forms.WarningBar(title="Pick first point"):
            point1 = revit.pick_elementpoint(world=True)
            if not point1:
                return
            create_and_show_point_mesh(point1)

        with forms.WarningBar(title="Pick second point"):
            point2 = revit.pick_elementpoint(world=True)
            if not point2:
                return

        new_meshes = create_measurement_meshes(point1, point2)

        # Add to existing meshes (don't replace)
        if dc3d_server:
            existing_meshes = dc3d_server.meshes or []
            dc3d_server.meshes = existing_meshes + new_meshes
            uidoc.RefreshActiveView()

        dx, dy, dz, diagonal, slope = calculate_distances(point1, point2)

        measure_window.point1_text.Text = "Point 1: {}".format(format_point(point1))
        measure_window.point2_text.Text = "Point 2: {}".format(format_point(point2))
        measure_window.dx_text.Text = "ΔX: {:>15}".format(format_distance(dx))
        measure_window.dy_text.Text = "ΔY: {:>15}".format(format_distance(dy))
        measure_window.dz_text.Text = "ΔZ: {:>15}".format(format_distance(dz))
        measure_window.diagonal_text.Text = "Diagonal: {}".format(
            format_distance(diagonal)
        )
        measure_window.slope_text.Text = "Slope: {}".format(format_slope(slope))

        # Add to history
        history_entry = (
            "Measurement {}:\n  P1: {}\n  P2: {}\n  "
            "ΔX: {:>15}\n  ΔY: {:>15}\n  ΔZ: {:>15}\n  "
            "Diagonal: {}\n  Slope: {}".format(
                len(measurement_history) + 1,
                format_point(point1),
                format_point(point2),
                format_distance(dx),
                format_distance(dy),
                format_distance(dz),
                format_distance(diagonal),
                format_slope(slope),
            )
        )
        measurement_history.append(history_entry)

        # Update history display
        history_text = "\n".join(measurement_history)
        measure_window.history_text.Text = history_text

        # Automatically start the next measurement
        measure_handler_event.Raise()

    except InvalidOperationException as ex:
        logger.error("InvalidOperationException during measurement: {}".format(ex))
        forms.alert(
            "Measurement cancelled due to invalid operation. Please try again.",
            title="Measurement Error",
        )
    except Exception as ex:
        logger.exception(
            "Error during measurement: {}".format(ex)
        )
        forms.alert(
            "An unexpected error occurred during measurement. Check the log for details.",
            title="Measurement Error",
        )


class SimpleEventHandler(UI.IExternalEventHandler):
    """IExternalEventHandler to execute functions in Revit API context."""

    def __init__(self, do_this):
        self.do_this = do_this

    def Execute(self, uiapp):
        try:
            self.do_this()
        except InvalidOperationException as ex:
            logger.error("InvalidOperationException caught: {}".format(ex))
        except Exception as ex:
            logger.error("Error in event handler: {}".format(ex))

    def GetName(self):
        return "pyRevit 3D Measure Event Handler"


class MeasureWindow(forms.WPFWindow):
    """Modeless WPF window for 3D measurement tool."""

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name, handle_esc=True)
        self.point1_text.Text = "Point 1: Not selected"
        self.point2_text.Text = "Point 2: Not selected"
        self.dx_text.Text = "ΔX: -"
        self.dy_text.Text = "ΔY: -"
        self.dz_text.Text = "ΔZ: -"
        self.diagonal_text.Text = "Diagonal: -"
        self.slope_text.Text = "Slope: -"
        self.history_text.Text = "No measurements yet"

        if not length_unit_symbol_label:
            self.show_element(self.project_unit_text)
            self.project_unit_text.Text = (
                "Length Units (adjust in Project Units): \n" + length_unit_label
            )
            self.Height = self.Height + 20
        if not slope_unit_symbol_label:
            self.show_element(self.project_unit_text)
            self.project_unit_text.Text = self.project_unit_text.Text + (
                "\nSlope Units (adjust in Project Units): \n" + slope_unit_label
            )
            self.Height = self.Height + 20

        # Handle window close event
        self.Closed += self.window_closed
        script.restore_window_position(self)
        self.Show()

        # Automatically start the first measurement
        measure_handler_event.Raise()

    def window_closed(self, sender, args):
        """Handle window close event - copy history to clipboard, cleanup DC3D server and visual aids."""
        global dc3d_server
        script.save_window_position(self)
        # Copy measurement history to clipboard before cleanup
        try:
            if measurement_history:
                history_text = "\n".join(measurement_history)
                script.clipboard_copy(history_text)
                forms.toast("Measurements copied to Clipboard!", title="Measure 3D")
        except Exception as ex:
            logger.error("Error copying to clipboard: {}".format(ex))

        try:
            # Delete all visual aids
            if dc3d_server:
                dc3d_server.meshes = []
                uidoc.RefreshActiveView()
                dc3d_server.remove_server()
                dc3d_server = None
        except Exception as ex:
            logger.error("Error closing window: {}".format(ex))


def main():
    """Main entry point for the tool."""
    global measure_window, measure_handler_event
    global dc3d_server

    dc3d_server = revit.dc3dserver.Server(
        uidoc=uidoc,
        name="pyRevit 3D Measure Tool",
        description="Visual aids for 3D measurements",
        vendor_id="pyRevit",
    )

    if not dc3d_server:
        logger.error("Failed to create DC3D server")
        script.exit()

    measure_handler = SimpleEventHandler(perform_measurement)
    measure_handler_event = UI.ExternalEvent.Create(measure_handler)

    measure_window = MeasureWindow("measure3d.xaml")


if __name__ == "__main__":
    main()
