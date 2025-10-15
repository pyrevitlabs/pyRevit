# -*- coding: utf-8 -*-
"""3D Measure Tool for Revit
Allows measuring distances between two points with visual aids and history tracking.
"""
from __future__ import print_function
import math
from pyrevit import revit, forms, script, traceback
from pyrevit import UI, DB
from pyrevit.framework import List
from Autodesk.Revit.Exceptions import InvalidOperationException

# Configure logger
logger = script.get_logger()

# Document variables
doc = revit.doc
uidoc = revit.uidoc
active_view = revit.active_view
length_unit = doc.GetUnits().GetFormatOptions(DB.SpecTypeId.Length).GetUnitTypeId()
unit_label = DB.LabelUtils.GetLabelForUnit(length_unit)

# Global variables
measure_window = None
measure_handler_event = None
delete_all_visual_aids_handler_event = None
visual_aids_ids = []
measurement_history = []
MAX_HISTORY = 5  # Configurable: maximum number of measurements to keep in history

# Visual aid configuration
SPHERE_RADIUS = 0.3  # in feet (approximately 4 inches)
VISUAL_AID_COMMENT = "pyRevit_Measure_Helper"


def calculate_distances(point1, point2):
    """Calculate dx, dy, dz and diagonal distance between two points.

    Args:
        point1 (DB.XYZ): First point
        point2 (DB.XYZ): Second point

    Returns:
        tuple: (dx, dy, dz, diagonal) all in internal units (feet)
    """
    dx = abs(point2.X - point1.X)
    dy = abs(point2.Y - point1.Y)
    dz = abs(point2.Z - point1.Z)
    diagonal = point1.DistanceTo(point2)

    logger.debug(
        "Calculated distances - dx: {}, dy: {}, dz: {}, diagonal: {}".format(
            dx, dy, dz, diagonal
        )
    )

    return dx, dy, dz, diagonal


def format_distance(value_in_feet):
    converted_value = DB.UnitUtils.ConvertFromInternalUnits(value_in_feet, length_unit)
    return "{:.3f} {}".format(converted_value, unit_label)


def format_point(point):
    x = DB.UnitUtils.ConvertFromInternalUnits(point.X, length_unit)
    y = DB.UnitUtils.ConvertFromInternalUnits(point.Y, length_unit)
    z = DB.UnitUtils.ConvertFromInternalUnits(point.Z, length_unit)
    return "({:.3f}, {:.3f}, {:.3f}) {}".format(x, y, z, unit_label)


def create_visual_aid_sphere(point, radius=SPHERE_RADIUS, color=DB.Color(255, 0, 0)):
    """Create a sphere at the given point as a visual aid.

    Args:
        point (DB.XYZ): Center point of sphere
        radius (float): Sphere radius in feet
        color (DB.Color): Color for the sphere (default: red)

    Returns:
        DB.ElementId: ID of created DirectShape element
    """
    start = point + DB.XYZ(0, 0, -radius)
    end = point + DB.XYZ(0, 0, radius)
    mid = point + DB.XYZ(radius, 0, 0)  # Point on arc (right side)

    arc = DB.Arc.Create(start, end, mid)

    profile = DB.CurveLoop()
    profile.Append(arc)
    profile.Append(DB.Line.CreateBound(end, start))  # Close the loop with a line

    profile_list = List[DB.CurveLoop]()
    profile_list.Add(profile)

    # Create Frame (revolve around Z axis)
    origin = point
    x_dir = DB.XYZ.BasisX
    y_dir = DB.XYZ.BasisY
    z_dir = DB.XYZ.BasisZ  # This is the axis of revolution
    frame = DB.Frame(origin, x_dir, y_dir, z_dir)

    # Revolve 360 degrees (full circle)
    angle_start = 0
    angle_end = 2 * math.pi

    # Create geometry
    sphere = DB.GeometryCreationUtilities.CreateRevolvedGeometry(frame, profile_list, angle_start, angle_end)

    with revit.Transaction("Create Sphere"):
        # Create DirectShape
        direct_shape = DB.DirectShape.CreateElement(
            doc, DB.ElementId(DB.BuiltInCategory.OST_GenericModel)
        )
        direct_shape.SetShape([sphere])

        # Set mark parameter
        mark_param = direct_shape.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if mark_param:
            mark_param.Set(VISUAL_AID_COMMENT)

        # Set color using graphics override
        view = doc.ActiveView
        override_settings = DB.OverrideGraphicSettings()
        override_settings.SetProjectionLineColor(color)
        override_settings.SetSurfaceForegroundPatternColor(color)
        view.SetElementOverrides(direct_shape.Id, override_settings)

        element_id = direct_shape.Id
        visual_aids_ids.append(element_id)
        logger.debug("Created sphere at {} with ID {}".format(point, element_id))

        return element_id


def create_visual_aid_lines(point1, point2):
    """Create model lines showing dx, dy, dz projections and diagonal.

    Args:
        point1 (DB.XYZ): First point
        point2 (DB.XYZ): Second point
    """
    with revit.Transaction("Create Measurement Lines"):
        # Determine the work plane (use the lowest Z for X and Y lines)
        lower_z = min(point1.Z, point2.Z)

        # Create sketch plane for horizontal lines
        plane_origin = DB.XYZ(0, 0, lower_z)
        plane_normal = DB.XYZ.BasisZ
        plane = DB.Plane.CreateByNormalAndOrigin(plane_normal, plane_origin)
        sketch_plane = DB.SketchPlane.Create(doc, plane)

        # X direction line (red)
        x_start = DB.XYZ(point1.X, point1.Y, lower_z)
        x_end = DB.XYZ(point2.X, point1.Y, lower_z)
        if x_start.DistanceTo(x_end) > 0.001:  # Only create if distance is significant
            x_line = DB.Line.CreateBound(x_start, x_end)
            x_model_line = doc.Create.NewModelCurve(x_line, sketch_plane)

            override_x = DB.OverrideGraphicSettings()
            override_x.SetProjectionLineColor(DB.Color(255, 0, 0))  # Red
            override_x.SetProjectionLineWeight(3)
            doc.ActiveView.SetElementOverrides(x_model_line.Id, override_x)
            visual_aids_ids.append(x_model_line.Id)

        # Y direction line (green)
        y_start = DB.XYZ(point2.X, point1.Y, lower_z)
        y_end = DB.XYZ(point2.X, point2.Y, lower_z)
        if y_start.DistanceTo(y_end) > 0.001:
            y_line = DB.Line.CreateBound(y_start, y_end)
            y_model_line = doc.Create.NewModelCurve(y_line, sketch_plane)

            override_y = DB.OverrideGraphicSettings()
            override_y.SetProjectionLineColor(DB.Color(0, 255, 0))  # Green
            override_y.SetProjectionLineWeight(3)
            doc.ActiveView.SetElementOverrides(y_model_line.Id, override_y)
            visual_aids_ids.append(y_model_line.Id)

        # Z direction line (blue) - vertical plane through the higher point
        higher_point = point1 if point1.Z > point2.Z else point2
        plane_z = DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisX, higher_point)
        sketch_plane_z = DB.SketchPlane.Create(doc, plane_z)

        z_start = DB.XYZ(higher_point.X, higher_point.Y, lower_z)
        z_end = DB.XYZ(higher_point.X, higher_point.Y, max(point1.Z, point2.Z))
        if z_start.DistanceTo(z_end) > 0.001:
            z_line = DB.Line.CreateBound(z_start, z_end)
            z_model_line = doc.Create.NewModelCurve(z_line, sketch_plane_z)

            override_z = DB.OverrideGraphicSettings()
            override_z.SetProjectionLineColor(DB.Color(0, 0, 255))  # Blue
            override_z.SetProjectionLineWeight(3)
            doc.ActiveView.SetElementOverrides(z_model_line.Id, override_z)
            visual_aids_ids.append(z_model_line.Id)

        # Diagonal line (yellow) - create plane through both points
        if point1.DistanceTo(point2) > 0.001:
            direction = (point2 - point1).Normalize()
            # Find a perpendicular vector for plane normal
            if abs(direction.Z) < 0.9:
                plane_normal_diag = direction.CrossProduct(DB.XYZ.BasisZ).Normalize()
            else:
                plane_normal_diag = direction.CrossProduct(DB.XYZ.BasisX).Normalize()

            plane_diag = DB.Plane.CreateByNormalAndOrigin(plane_normal_diag, point1)
            sketch_plane_diag = DB.SketchPlane.Create(doc, plane_diag)

            diag_line = DB.Line.CreateBound(point1, point2)
            diag_model_line = doc.Create.NewModelCurve(diag_line, sketch_plane_diag)

            override_diag = DB.OverrideGraphicSettings()
            override_diag.SetProjectionLineColor(DB.Color(200, 200, 0))  # Dark Yellow
            override_diag.SetProjectionLineWeight(4)
            doc.ActiveView.SetElementOverrides(diag_model_line.Id, override_diag)
            visual_aids_ids.append(diag_model_line.Id)

        logger.debug(
            "Created measurement lines, total visual aids: {}".format(
                len(visual_aids_ids)
            )
        )


def delete_all_visual_aids():
    """Delete all visual aids created by this tool."""
    global visual_aids_ids

    if not visual_aids_ids:
        logger.info("No visual aids to delete")
        return

    with revit.Transaction("Delete Visual Aids"):
        ids_to_delete = [aid for aid in visual_aids_ids if doc.GetElement(aid)]
        if ids_to_delete:
            doc.Delete(List[DB.ElementId](ids_to_delete))
            logger.info("Deleted {} visual aids".format(len(ids_to_delete)))
        visual_aids_ids = []


def perform_measurement():
    """Perform the measurement workflow: pick points, create aids, update UI."""
    global measurement_history

    try:
        # Pick first point
        with forms.WarningBar(title="Pick first point"):
            point1 = revit.pick_elementpoint(world=True)
            if not point1:
                logger.info("First point selection cancelled")
                return
        create_visual_aid_sphere(point1, color=DB.Color(255, 165, 0))  # Orange

        with forms.WarningBar(title="Pick second point"):
            point2 = revit.pick_elementpoint(world=True)
            if not point2:
                logger.info("Second point selection cancelled")
                delete_all_visual_aids()
                return
        create_visual_aid_sphere(point2, color=DB.Color(255, 165, 0))  # Orange

        create_visual_aid_lines(point1, point2)

        dx, dy, dz, diagonal = calculate_distances(point1, point2)

        # Update window with current measurement
        measure_window.point1_text.Text = "Point 1: {}".format(format_point(point1))
        measure_window.point2_text.Text = "Point 2: {}".format(format_point(point2))
        measure_window.dx_text.Text = "ΔX: {}".format(format_distance(dx))
        measure_window.dy_text.Text = "ΔY: {}".format(format_distance(dy))
        measure_window.dz_text.Text = "ΔZ: {}".format(format_distance(dz))
        measure_window.diagonal_text.Text = "Diagonal: {}".format(
            format_distance(diagonal)
        )

        # Add to history
        history_entry = "Measurement {}:\n  P1: {}\n  P2: {}\n  ΔX: {}\n  ΔY: {}\n  ΔZ: {}\n  Diagonal: {}\n".format(
            len(measurement_history) + 1,
            format_point(point1),
            format_point(point2),
            format_distance(dx),
            format_distance(dy),
            format_distance(dz),
            format_distance(diagonal),
        )

        measurement_history.append(history_entry)

        # Keep only last MAX_HISTORY measurements
        if len(measurement_history) > MAX_HISTORY:
            measurement_history = measurement_history[-MAX_HISTORY:]

        # Update history display
        history_text = "\n".join(measurement_history)
        measure_window.history_text.Text = history_text

        logger.info("Measurement completed successfully")

    except Exception as ex:
        logger.error("Error during measurement: {}\n {}".format(ex, traceback.format_exc()))


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
        forms.WPFWindow.__init__(self, xaml_file_name)
        self.point1_text.Text = "Point 1: Not selected"
        self.point2_text.Text = "Point 2: Not selected"
        self.dx_text.Text = "ΔX: -"
        self.dy_text.Text = "ΔY: -"
        self.dz_text.Text = "ΔZ: -"
        self.diagonal_text.Text = "Diagonal: -"
        self.history_text.Text = "No measurements yet"
        self.Show()
        logger.debug("Measure window opened")

    def delete_click(self, sender, e):
        """Handle delete button click."""
        delete_all_visual_aids_handler_event.Raise()
        logger.debug("Delete visual aids event raised")

    def measure_click(self, sender, e):
        """Handle measure again button click."""
        measure_handler_event.Raise()
        logger.debug("Measure event raised")


def main():
    """Main entry point for the tool."""
    global measure_window, measure_handler_event, delete_all_visual_aids_handler_event

    if not measure_window:
        measure_handler = SimpleEventHandler(perform_measurement)
        measure_handler_event = UI.ExternalEvent.Create(measure_handler)

        delete_handler = SimpleEventHandler(delete_all_visual_aids)
        delete_all_visual_aids_handler_event = UI.ExternalEvent.Create(delete_handler)

        measure_window = MeasureWindow("measure3d.xaml")

    perform_measurement()


if __name__ == "__main__":
    main()
