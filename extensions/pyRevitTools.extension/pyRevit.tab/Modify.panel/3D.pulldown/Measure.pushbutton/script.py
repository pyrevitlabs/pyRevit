# -*- coding: utf-8 -*-
from collections import deque
from math import pi, atan, sqrt, acos
from pyrevit import revit, forms, script
from pyrevit import DB
from Autodesk.Revit.Exceptions import InvalidOperationException

logger = script.get_logger()

doc = revit.doc
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
LINE_COLOR_X = DB.ColorWithTransparency(255, 0, 0, 0)  # Red
LINE_COLOR_Y = DB.ColorWithTransparency(0, 255, 0, 0)  # Green
LINE_COLOR_Z = DB.ColorWithTransparency(0, 0, 255, 0)  # Blue
LINE_COLOR_DIAG = DB.ColorWithTransparency(200, 200, 0, 0)  # Dark Yellow
CONE_COLOR = DB.ColorWithTransparency(255, 165, 0, 50)  # Orange
CONE_SCALE = 0.05


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


def create_cone_mesh(center, scale, color, view):
    cone_path = script.get_bundle_file("cone.STL")
    cam_forward = view.GetOrientation().ForwardDirection.Normalize()
    cone_axis = cam_forward.Negate()

    z_axis = DB.XYZ.BasisZ
    dot = max(-1.0, min(1.0, z_axis.DotProduct(cone_axis)))

    if dot >= 0.9999999:
        rotation = DB.Transform.Identity
    elif dot <= -0.9999999:
        perp = z_axis.CrossProduct(DB.XYZ.BasisX)
        if perp.GetLength() < 1e-6:
            perp = z_axis.CrossProduct(DB.XYZ.BasisY)
        rotation = DB.Transform.CreateRotationAtPoint(perp.Normalize(), pi, DB.XYZ.Zero)
    else:
        axis = z_axis.CrossProduct(cone_axis).Normalize()
        angle = acos(dot)
        rotation = DB.Transform.CreateRotationAtPoint(axis, angle, DB.XYZ.Zero)

    translation = DB.Transform.CreateTranslation(center)
    transform = translation.Multiply(rotation).ScaleBasis(scale)
    mesh = revit.dc3dserver.Mesh.from_stl(
        cone_path, color, transform=transform, black_edges=True
    )

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
        new_meshes.append(create_cone_mesh(point1, CONE_SCALE, CONE_COLOR, doc.ActiveView))
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
    meshes.append(create_cone_mesh(point2, CONE_SCALE, CONE_COLOR, doc.ActiveView))

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


def perform_measurement():
    """Perform the measurement workflow: pick points, create aids, update UI."""
    # Add 3D view validation
    if not forms.check_viewtype(doc.ActiveView, DB.ViewType.ThreeD):
        return

    try:
        with forms.WarningBar(
            title=measure_window.get_locale_string("WarningBarPickFirstPoint")
        ):
            point1 = revit.pick_elementpoint(world=True)
            if not point1:
                return
            create_and_show_point_mesh(point1)

        with forms.WarningBar(
            title=measure_window.get_locale_string("WarningBarPickSecondPoint")
        ):
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

        measure_window.point1_text.Text = measure_window.get_locale_string("Point1Format").format(format_point(point1))
        measure_window.point2_text.Text = measure_window.get_locale_string("Point2Format").format(format_point(point2))
        measure_window.dx_text.Text = measure_window.get_locale_string("DeltaXFormat").format(format_distance(dx))
        measure_window.dy_text.Text = measure_window.get_locale_string("DeltaYFormat").format(format_distance(dy))
        measure_window.dz_text.Text = measure_window.get_locale_string("DeltaZFormat").format(format_distance(dz))
        measure_window.diagonal_text.Text = measure_window.get_locale_string("DiagonalFormat").format(
            format_distance(diagonal)
        )
        measure_window.slope_text.Text = measure_window.get_locale_string("SlopeFormat").format(format_slope(slope))

        # Add to history
        history_entry = (
            measure_window.get_locale_string("MeasurementHistoryEntry")
            .format(
                len(measurement_history) + 1,
                format_point(point1),
                format_point(point2),
                format_distance(dx),
                format_distance(dy),
                format_distance(dz),
                format_distance(diagonal),
                format_slope(slope),
            )
            .lstrip()
        )
        measurement_history.append(history_entry)

        # Update history display
        history_text = "\n".join(measurement_history)
        measure_window.history_text.Text = history_text

        # Automatically start the next measurement
        revit.events.execute_in_revit_context(perform_measurement)

    except InvalidOperationException as ex:
        logger.error("InvalidOperationException during measurement: {}".format(ex))
        forms.alert(
            measure_window.get_locale_string("AlertMeasurementCancelled"),
            title=measure_window.get_locale_string("AlertMeasurementErrorTitle"),
        )
    except Exception as ex:
        logger.exception("Error during measurement: {}".format(ex))
        forms.alert(
            measure_window.get_locale_string("AlertUnexpectedError"),
            title=measure_window.get_locale_string("AlertMeasurementErrorTitle"),
        )


class MeasureWindow(forms.WPFWindow):
    """Modeless WPF window for 3D measurement tool."""

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name, handle_esc=True)
        self.point1_text.Text = self.get_locale_string("Point1NotSelected")
        self.point2_text.Text = self.get_locale_string("Point2NotSelected")
        self.dx_text.Text = self.get_locale_string("DeltaXFormat").format("-")
        self.dy_text.Text = self.get_locale_string("DeltaYFormat").format("-")
        self.dz_text.Text = self.get_locale_string("DeltaZFormat").format("-")
        self.diagonal_text.Text = self.get_locale_string("DiagonalFormat").format("-")
        self.slope_text.Text = self.get_locale_string("SlopeFormat").format("-")
        self.history_text.Text = self.get_locale_string("NoMeasurementsYet")

        if not length_unit_symbol_label:
            self.show_element(self.project_unit_text)
            self.project_unit_text.Text = (
                self.get_locale_string("ProjectUnitLengthUnits") + length_unit_label
            ).lstrip()
            self.Height = self.Height + 20
        if not slope_unit_symbol_label:
            self.show_element(self.project_unit_text)
            self.project_unit_text.Text = self.project_unit_text.Text + (
                "\n" + self.get_locale_string("ProjectUnitSlopeUnits") + slope_unit_label
            ).lstrip()
            self.Height = self.Height + 20

        # Handle window close event
        self.Closed += self.window_closed
        script.restore_window_position(self)
        self.Show()

        # Automatically start the first measurement
        revit.events.execute_in_revit_context(perform_measurement)

    def window_closed(self, sender, args):
        """Handle window close event - copy history to clipboard, cleanup DC3D server and visual aids."""
        global dc3d_server
        script.save_window_position(self)
        # Copy measurement history to clipboard before cleanup
        try:
            if measurement_history:
                history_text = "\n".join(measurement_history)
                script.clipboard_copy(history_text)
                forms.toast(
                    self.get_locale_string("ToastMeasurementsCopied"),
                    title=self.get_locale_string("ToastMeasure3DTitle"),
                )
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

    measure_window = MeasureWindow("measure3d.xaml")


if __name__ == "__main__":
    main()
