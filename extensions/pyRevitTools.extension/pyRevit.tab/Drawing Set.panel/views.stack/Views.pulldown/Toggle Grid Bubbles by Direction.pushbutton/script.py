# -*- coding: UTF-8 -*-
import math

import clr

clr.AddReference("PresentationFramework")

import System
from System.Windows import WindowStartupLocation
from System.Collections.Generic import List
from pyrevit import HOST_APP, DB, script, forms
from pyrevit.revit.db import transaction
from pyrevit.compat import get_elementid_value_func
from coordinate_selector import show_coordinate_system_selector

doc = HOST_APP.doc
uidoc = HOST_APP.uidoc
active_view = doc.ActiveView
xamlfile = script.get_bundle_file("ui.xaml")

get_elementid_value = get_elementid_value_func()

VIEW_TYPES = [
    DB.ViewType.FloorPlan,
    DB.ViewType.EngineeringPlan,
    DB.ViewType.Elevation,
    DB.ViewType.Section,
    DB.ViewType.CeilingPlan,
]
PLAN_VIEWS = [
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.EngineeringPlan,
]
ELEVATION_VIEWS = [DB.ViewType.Elevation, DB.ViewType.Section]


def angle_to_dot_product_threshold(angle_degrees):
    """Convert angle in degrees to dot product threshold."""
    angle_radians = math.radians(angle_degrees)
    return math.cos(angle_radians)


class GridsCollector:
    """Handles all grid collection, filtering, and validation."""

    def __init__(self, document, view):
        self.document = document
        self.view = view
        self.selection = self._get_selection()

        if self.selection:
            self._analyze_selection()
        else:
            self._analyze_all_grids()

    def _get_selection(self):
        """Get current selection if any."""
        selection_ids = HOST_APP.uidoc.Selection.GetElementIds()
        if selection_ids:
            return [self.document.GetElement(el_id) for el_id in selection_ids]
        return None

    def _is_valid_grid(self, elem):
        """Check if an element is a valid grid for processing."""
        try:
            grid_category_id = int(DB.BuiltInCategory.OST_Grids)
            return (
                elem.Category
                and int(get_elementid_value(elem.Category.Id)) == grid_category_id
                and hasattr(elem, "GetCurvesInView")
                and not elem.IsCurved
                and not self._is_grid_segment(elem)
            )
        except:
            return False

    def _is_grid_segment(self, grid):
        """Check if a grid is a segment (not a full grid)."""
        try:
            return not (
                grid.HasBubbleInView(DB.DatumEnds.End0, self.view)
                and grid.HasBubbleInView(DB.DatumEnds.End1, self.view)
            )
        except:
            return True

    def _analyze_selection(self):
        """Analyze selected elements."""
        self._analyze_grids(self.selection)
        self.from_selection = True

    def _analyze_all_grids(self):
        grids = (
            DB.FilteredElementCollector(self.document)
            .OfCategory(DB.BuiltInCategory.OST_Grids)
            .WhereElementIsNotElementType()
        )
        self._analyze_grids(grids)

    def _analyze_grids(self, grids):
        """Analyze all grids in view."""

        self.valid_grids = []
        self.hidden_count = 0
        self.curved_count = 0
        self.segment_count = 0

        for grid in grids:
            if grid.IsHidden(self.view):
                self.hidden_count += 1
            elif hasattr(grid, "IsCurved") and grid.IsCurved:
                self.curved_count += 1
            elif self._is_grid_segment(grid):
                self.segment_count += 1
            else:
                self.valid_grids.append(grid)

        self.from_selection = False

    def get_grid_chain_count(self):
        """Get the count of the multi-segment grids in the active view."""
        grid_chains = (
            DB.FilteredElementCollector(self.document, self.view.Id)
            .OfCategory(DB.BuiltInCategory.OST_GridChains)
            .WhereElementIsNotElementType()
            .ToElements()
        )

        # Count only visible grid chains
        count = 0
        for chain in grid_chains:
            if not chain.IsHidden(self.view):
                count += 1

        return count

    def check_validity(self):
        """Check if any valid grids exist and show appropriate alerts."""
        alert_message = "No valid grid found {}"
        if self.from_selection:
            alert_main_message = alert_message.format("in your selection.")
        else:
            alert_main_message = alert_message.format("in the current view.")

        if not self.valid_grids:
            sub_message = ""
            if self.hidden_count > 0:
                sub_message += "Hidden grids: {}\n".format(self.hidden_count)
            if self.get_grid_chain_count() > 0:
                sub_message += "Multi-segment grids: {}\n".format(
                    self.get_grid_chain_count()
                )
            if self.curved_count > 0:
                sub_message += "Curved grids: {}".format(self.curved_count)

            forms.alert(
                msg=alert_main_message,
                sub_msg=sub_message,
            )
            return False
        return True

    def get_status_text(self):
        """Get status text for UI display."""
        total = len(self.valid_grids)
        if self.from_selection:
            return "Scope: {} selected grids".format(total)
        else:
            return "Scope: All {} grids in view".format(total)


class CustomGrids:
    def __init__(
        self,
        document,
        view,
        coordinate_system="project_north",
        angle_tolerance=1,
        grid_collector=None,
    ):
        """Initialize with the document, view, coordinate system choice, and angle tolerance and GridsCollector instance."""
        self.__view = view
        self.__document = document
        self.__coordinate_system = coordinate_system
        self.__angle_tolerance = angle_tolerance
        self.is_valid = True

        # Use provided collector or create new one
        if grid_collector:
            self.collector = grid_collector
            self.__grids = grid_collector.valid_grids
            self.selection = grid_collector.selection
        else:
            # Fallback - create collector
            self.collector = GridsCollector(document, view)
            if not self.collector.check_validity():
                self.is_valid = False
                return
            self.__grids = self.collector.valid_grids
            self.selection = self.collector.selection

        # Convert angle tolerance to dot product threshold
        self.__alignment_threshold = angle_to_dot_product_threshold(angle_tolerance)

        # Initialize coordinate system attributes first
        self._transform = DB.Transform.Identity

        self.right_left_collapsed = False
        self.top_bottom_collapsed = False

        self._original_selection = []
        self._all_active_grids_selected = False

        selection_ids = HOST_APP.uidoc.Selection.GetElementIds()
        self.selection = (
            [document.GetElement(el_id) for el_id in selection_ids]
            if selection_ids
            else []
        )

        # Setyp transformation only if not in elevation or all grids mode
        if coordinate_system in ["project_north", "true_north", "view"]:
            self._setup_coordinate_transform()

        if not self.__grids:
            forms.alert("No valid grids found.")
            self.is_valid = False
            return

    def _setup_coordinate_transform(self):
        """Set up the coordinate transformation based on user choice."""
        try:
            if self.__coordinate_system == "project_north":
                # Use identity transform (no transformation)
                self._transform = DB.Transform.Identity

            elif self.__coordinate_system == "true_north":
                # Get project base point transformation
                pbp_collector = DB.FilteredElementCollector(self.__document).OfCategory(
                    DB.BuiltInCategory.OST_ProjectBasePoint
                )
                pbp = pbp_collector.FirstElement()

                if pbp:
                    # Get the angle parameter
                    angle_param = pbp.get_Parameter(
                        DB.BuiltInParameter.BASEPOINT_ANGLETON_PARAM
                    )
                    if angle_param:
                        angle = angle_param.AsDouble()
                        # Create rotation transform
                        self._transform = DB.Transform.CreateRotation(
                            DB.XYZ.BasisZ, -angle
                        )
                    else:
                        self._transform = DB.Transform.Identity
                else:
                    self._transform = DB.Transform.Identity

            elif self.__coordinate_system == "view":
                # Calculate angle from view's RightDirection and treat it like base point rotation
                view_right = self.__view.RightDirection

                # Calculate angle between view's right direction and world X axis
                angle = math.atan2(view_right.Y, view_right.X)

                # Create rotation transform (negate angle for proper transformation)
                self._transform = DB.Transform.CreateRotation(DB.XYZ.BasisZ, -angle)

            else:
                self._transform = DB.Transform.Identity

        except:
            self._transform = DB.Transform.Identity

    def _transform_point(self, point):
        """Transform a point using the selected coordinate system."""
        try:
            if self.__coordinate_system == "project_north":
                return point
            else:
                return self._transform.OfPoint(point)
        except:
            return point

    def set_ui_state(self, right_left_collapsed, top_bottom_collapsed):
        """Set the UI state so the grids class knows which controls are active."""
        self.right_left_collapsed = right_left_collapsed
        self.top_bottom_collapsed = top_bottom_collapsed

    def highlight_all_active_grids_once(self):
        """Highlight all active grids once at startup and keep them selected."""
        try:
            if not self._all_active_grids_selected:
                self._original_selection = [
                    self.__document.GetElement(el_id)
                    for el_id in HOST_APP.uidoc.Selection.GetElementIds()
                ]

                active_grids = self.get_active_grids()
                if active_grids:
                    grid_ids = [grid.Id for grid in active_grids if grid and grid.Id]
                    if grid_ids:
                        id_list = List[DB.ElementId](grid_ids)
                        HOST_APP.uidoc.Selection.SetElementIds(id_list)
                        self._all_active_grids_selected = True
        except:
            pass

    def unhighlight_grids(self):
        """Clear selection."""
        try:
            if self._all_active_grids_selected:
                HOST_APP.uidoc.Selection.SetElementIds(List[DB.ElementId]())
                self._all_active_grids_selected = False
        except:
            pass

    def get_active_grids(self):
        """Get only the grids that are actively managed by the current UI state."""
        active_grids = []

        if self.__coordinate_system == "elevation_mode":
            active_grids.extend(self.get_vertical_grids())
            return active_grids

        if self.__coordinate_system == "all_grids":
            active_grids.extend(self.__grids)

        if not self.top_bottom_collapsed:
            active_grids.extend(self.get_vertical_grids())

        if not self.right_left_collapsed:
            active_grids.extend(self.get_horizontal_grids())

        return active_grids

    def grids(self):
        """Return the collected grids."""
        return self.__grids

    def get_grid_curve(self, grid):
        """Get the curves of a grid that are specific to the view."""
        try:
            if not hasattr(grid, "GetCurvesInView"):
                return []
            return grid.GetCurvesInView(DB.DatumExtentType.ViewSpecific, self.__view)
        except:
            return []

    def is_linear(self, grid):
        """Check if a grid is linear."""
        return len(self.get_grid_curve(grid)) == 1

    def get_endpoints(self, grid):
        """Get the first and second endpoints of a grid if it is linear."""
        if self.is_linear(grid):
            curve = self.get_grid_curve(grid)[0]
            pt0 = curve.GetEndPoint(0)
            pt1 = curve.GetEndPoint(1)
            return DB.XYZ(pt0.X, pt0.Y, pt0.Z), DB.XYZ(pt1.X, pt1.Y, pt1.Z)
        return None, None

    def get_transformed_endpoints(self, grid):
        """Get grid endpoints transformed to the selected coordinate system."""
        pt0, pt1 = self.get_endpoints(grid)
        if pt0 and pt1:
            # Transform points to selected coordinate system
            transformed_pt0 = self._transform_point(pt0)
            transformed_pt1 = self._transform_point(pt1)
            return transformed_pt0, transformed_pt1
        return None, None

    def filter_grids_by_orientation(self, is_vertical=True):
        """Filter grids based on their orientation in the selected coordinate system."""
        filtered_grids = []

        for g in self.grids():
            if not hasattr(g, "GetCurvesInView"):
                continue

            pt1, pt2 = self.get_endpoints(g)
            if pt1 and pt2:

                if self.__coordinate_system in ["view", "elevation_mode"]:
                    # For view orientation, use direction vector approach with user-defined tolerance
                    grid_vector = pt2 - pt1
                    grid_vector = grid_vector.Normalize()

                    # Get view directions
                    view_right = self.__view.RightDirection.Normalize()
                    view_up = self.__view.UpDirection.Normalize()

                    # Calculate alignment with view directions
                    right_alignment = abs(grid_vector.DotProduct(view_right))
                    up_alignment = abs(grid_vector.DotProduct(view_up))

                    if is_vertical:
                        # Vertical grids should be closely aligned with view's up direction
                        if (
                            up_alignment > self.__alignment_threshold
                            and up_alignment > right_alignment
                        ):
                            filtered_grids.append(g)
                    else:
                        # Horizontal grids should be closely aligned with view's right direction
                        if (
                            right_alignment > self.__alignment_threshold
                            and right_alignment > up_alignment
                        ):
                            filtered_grids.append(g)
                else:
                    # For project_north and project coordinate systems, use transformation approach
                    transformed_pt1 = self._transform_point(pt1)
                    transformed_pt2 = self._transform_point(pt2)

                    # Calculate grid direction vector in transformed space
                    dx = transformed_pt2.X - transformed_pt1.X
                    dy = transformed_pt2.Y - transformed_pt1.Y
                    grid_length = math.sqrt(dx * dx + dy * dy)

                    if grid_length > 0:
                        # Normalize the direction vector
                        dx_norm = dx / grid_length
                        dy_norm = dy / grid_length

                        # Calculate angle from horizontal (in radians)
                        grid_angle = math.atan2(abs(dy_norm), abs(dx_norm))
                        grid_angle_degrees = math.degrees(grid_angle)

                        if is_vertical:
                            # Vertical grids should be close to 90° (±tolerance from 90°)
                            angle_from_vertical = abs(90.0 - grid_angle_degrees)
                            if angle_from_vertical < self.__angle_tolerance:
                                filtered_grids.append(g)
                        else:
                            # Horizontal grids should be close to 0° (±tolerance from 0°)
                            if grid_angle_degrees < self.__angle_tolerance:
                                filtered_grids.append(g)

        return filtered_grids

    def are_bubbles_visible(self, direction=None, reverse=False):
        """Check if the bubbles of the grids are visible."""

        if not direction:
            # Check bubbles for only active grids
            active_grids = self.get_active_grids()

            if not active_grids:
                return False

            if not reverse:
                bubbles = [
                    is_visible
                    for grid in active_grids
                    for is_visible in [
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End0, self.__view),
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End1, self.__view),
                    ]
                ]
            else:
                bubbles = [
                    not is_visible
                    for grid in active_grids
                    for is_visible in [
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End0, self.__view),
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End1, self.__view),
                    ]
                ]
            return all(bubbles) if bubbles else False

        else:
            if direction in {"top", "bottom"}:
                grids = self.get_vertical_grids()
            else:
                grids = self.get_horizontal_grids()

            for grid in grids:
                # Use transformed coordinate system
                xyz_0, xyz_1 = self.get_transformed_endpoints(grid)
                if xyz_0 and xyz_1:
                    if direction in {"top", "right"}:
                        ref_point = self.get_bounding_box_corner(grid, "max")
                    else:
                        ref_point = self.get_bounding_box_corner(grid, "min")

                    if ref_point:
                        # Transform reference point to selected coordinate system
                        transformed_ref_point = self._transform_point(ref_point)

                        if (
                            xyz_0.DistanceTo(transformed_ref_point)
                            < xyz_1.DistanceTo(transformed_ref_point)
                            and grid.IsBubbleVisibleInView(
                                DB.DatumEnds.End0, self.__view
                            )
                        ) or (
                            xyz_0.DistanceTo(transformed_ref_point)
                            > xyz_1.DistanceTo(transformed_ref_point)
                            and grid.IsBubbleVisibleInView(
                                DB.DatumEnds.End1, self.__view
                            )
                        ):
                            return True

        return False

    def get_vertical_grids(self):
        """Get all vertical grids in the selected coordinate system."""
        return self.filter_grids_by_orientation(is_vertical=True)

    def get_horizontal_grids(self):
        """Get all horizontal grids in the selected coordinate system."""
        return self.filter_grids_by_orientation(is_vertical=False)

    def get_bounding_box_corner(self, grid, corner):
        bbox = grid.get_BoundingBox(self.__view)
        if bbox and bbox.Enabled:
            return bbox.Min if corner == "min" else bbox.Max
        return None

    @transaction.carryout("Toggle bubbles")
    def toggle_bubbles(self, grid, action, end=None):
        """Toggle the bubbles of a grid in the view."""

        map_end = {0: DB.DatumEnds.End0, 1: DB.DatumEnds.End1}
        if end == 0 or end == 1:
            if action == "hide":
                grid.HideBubbleInView(map_end[end], self.__view)
            else:
                grid.ShowBubbleInView(map_end[end], self.__view)
        # If no end specified, toggle both ends
        else:
            if action == "hide":
                grid.HideBubbleInView(DB.DatumEnds.End0, self.__view)
                grid.HideBubbleInView(DB.DatumEnds.End1, self.__view)
            else:
                grid.ShowBubbleInView(DB.DatumEnds.End0, self.__view)
                grid.ShowBubbleInView(DB.DatumEnds.End1, self.__view)

    def toggle_bubbles_by_direction(self, action, direction):
        """Toggle bubbles based on the specified direction in selected coordinate system."""
        if direction in {"top", "bottom"}:
            grids = self.get_vertical_grids()
        else:
            grids = self.get_horizontal_grids()

        for grid in grids:
            # Use transformed coordinate system
            xyz_0, xyz_1 = self.get_transformed_endpoints(grid)
            if xyz_0 and xyz_1:
                if direction in {"top", "right"}:
                    ref_point = self.get_bounding_box_corner(grid, "max")
                else:
                    ref_point = self.get_bounding_box_corner(grid, "min")

                if ref_point:
                    # Transform reference point to selected coordinate system
                    transformed_ref_point = self._transform_point(ref_point)

                    if xyz_0.DistanceTo(transformed_ref_point) < xyz_1.DistanceTo(
                        transformed_ref_point
                    ):
                        self.toggle_bubbles(grid, action, 0)
                    else:
                        self.toggle_bubbles(grid, action, 1)

    @transaction.carryout("Hide all bubbles")
    def hide_all_bubbles(self):
        """Hide the bubbles of only the actively managed grids."""
        active_grids = self.get_active_grids()

        for grid in active_grids:
            if grid.CanBeVisibleInView(self.__view):
                grid.HideBubbleInView(DB.DatumEnds.End0, self.__view)
                grid.HideBubbleInView(DB.DatumEnds.End1, self.__view)

    @transaction.carryout("Show all bubbles")
    def show_all_bubbles(self):
        """Show the bubbles of only the actively managed grids."""
        active_grids = self.get_active_grids()

        for grid in active_grids:
            if grid.CanBeVisibleInView(self.__view):
                grid.ShowBubbleInView(DB.DatumEnds.End0, self.__view)
                grid.ShowBubbleInView(DB.DatumEnds.End1, self.__view)


class ToggleGridWindow(forms.WPFWindow):
    def __init__(
        self,
        xaml_source,
        view,
        coordinate_system,
        angle_tolerance,
        grid_collector,
        transaction_group=None,
        window_left=None,
        window_top=None,
    ):
        super(ToggleGridWindow, self).__init__(xaml_source)

        self.result = None
        self.PreviewKeyDown += self.handle_key_press

        if window_left is not None and window_top is not None:
            self.WindowStartupLocation = WindowStartupLocation.Manual
            self.Left = window_left
            self.Top = window_top

        self.view = view
        self.coordinate_system = coordinate_system
        self.angle_tolerance = angle_tolerance
        self.transaction_group = transaction_group
        self.grids = CustomGrids(
            doc, self.view, coordinate_system, angle_tolerance, grid_collector
        )

        if not self.grids.is_valid:
            self.is_valid = False
            return
        self.is_valid = True

        # Hide back button if in elevation mode
        self.back_button = self.FindName("back_button")
        if self.coordinate_system == "elevation_mode" and self.back_button:
            self.back_button.Visibility = System.Windows.Visibility.Collapsed

        # Flags to control the visibility of the checkboxes
        self.right_left_collapsed = False
        self.top_bottom_collapsed = False

        # Flag to control event triggering
        self.updating_checkboxes = False

        # Find radio buttons
        self.hide_all = self.FindName("hide_all")
        self.show_all = self.FindName("show_all")

        self.status_grids = self.FindName("status_grids")
        self.status_grids_active = self.FindName("status_grids_active")
        self.status_coordinate_system = self.FindName("status_coordinate_system")
        self.status_active_controls = self.FindName("status_active_controls")

        self.checkboxes = {
            "top": self.FindName("check_top"),
            "left": self.FindName("check_left"),
            "right": self.FindName("check_right"),
            "bottom": self.FindName("check_bottom"),
        }

        if self.coordinate_system == "all_grids":
            self.checkboxes["top"].Visibility = System.Windows.Visibility.Collapsed
            self.checkboxes["bottom"].Visibility = System.Windows.Visibility.Collapsed
            self.checkboxes["left"].Visibility = System.Windows.Visibility.Collapsed
            self.checkboxes["right"].Visibility = System.Windows.Visibility.Collapsed
            self.right_left_collapsed = True
            self.top_bottom_collapsed = True

        # Display the checkboxes based on the orientation of the grids and the view type
        if self.is_view_elevation() or not self.grids.get_horizontal_grids():
            self.checkboxes["right"].Visibility = System.Windows.Visibility.Collapsed
            self.checkboxes["left"].Visibility = System.Windows.Visibility.Collapsed
            self.right_left_collapsed = True

        if not self.grids.get_vertical_grids():
            self.checkboxes["top"].Visibility = System.Windows.Visibility.Collapsed
            self.checkboxes["bottom"].Visibility = System.Windows.Visibility.Collapsed
            self.top_bottom_collapsed = True

        self.grids.set_ui_state(self.right_left_collapsed, self.top_bottom_collapsed)

        self.grids.highlight_all_active_grids_once()

        self.update_status_display()

        self.hide_all.Checked += self.on_hide_all_checked
        self.show_all.Checked += self.on_show_all_checked

        for checkbox in self.checkboxes.values():
            checkbox.Checked += self.toggle_bubbles
            checkbox.Unchecked += self.toggle_bubbles

        self.update_checkboxes()

    def update_status_display(self):
        """Update the status display to show current operation scope."""

        total_grids = len(self.grids.grids())
        active_grids = len(self.grids.get_active_grids())

        if self.grids.selection:
            grid_status = "Scope: {} selected grid{}".format(
                total_grids, "s" if total_grids > 1 else ""
            )
        else:
            if self.coordinate_system == "elevation_mode":
                grid_status = "Scope: All visible grids"
            else:
                grid_status = "Scope: All {} grids in view".format(total_grids)

        if active_grids != total_grids:
            # Split the text to show the active part in red
            self.status_grids.Text = grid_status
            self.status_grids_active.Text = " ({} active - selected in view)".format(
                active_grids
            )
            self.status_grids_active.Visibility = System.Windows.Visibility.Visible
        else:
            self.status_grids.Text = grid_status
            self.status_grids_active.Text = ""
            self.status_grids_active.Visibility = System.Windows.Visibility.Collapsed

        coord_system_map = {
            "all_grids": "No coordinates",
            "elevation_mode": "Elevation View",
            "true_north": "True North",
            "project_north": "Project North",
            "view": "View/Scope Box Orientation",
        }

        if self.coordinate_system == "all_grids":
            coord_status = "Coordinates: -"
        elif self.coordinate_system == "elevation_mode":
            coord_status = "View Type: Elevation/Section"
        else:
            coord_status = "Coordinates: {} ({}° tolerance)".format(
                coord_system_map.get(self.coordinate_system, self.coordinate_system),
                self.angle_tolerance,
            )
        self.status_coordinate_system.Text = coord_status

        active_controls = []
        if self.coordinate_system == "all_grids":
            active_controls.append("All Grids - {} active".format(total_grids))

        if not self.top_bottom_collapsed:
            vertical_count = len(self.grids.get_vertical_grids())
            active_controls.append("Vertical ({})".format(vertical_count))
        if not self.right_left_collapsed:
            horizontal_count = len(self.grids.get_horizontal_grids())
            active_controls.append("Horizontal ({})".format(horizontal_count))

        if active_controls:
            controls_status = "Active: {}".format(", ".join(active_controls))
        else:
            controls_status = "Active: None"

        self.status_active_controls.Text = controls_status

    @classmethod
    def create(
        cls,
        xaml_source,
        view,
        coordinate_system,
        angle_tolerance,
        grid_collector=None,
        transaction_group=None,
        window_left=None,
        window_top=None,
    ):
        """Factory method to handle a clean exit"""
        window = cls(
            xaml_source,
            view,
            coordinate_system,
            angle_tolerance,
            grid_collector,
            transaction_group,
            window_left,
            window_top,
        )
        if not window.is_valid:
            return None
        return window

    def is_view_elevation(self):
        return self.view.ViewType in ELEVATION_VIEWS

    def on_hide_all_checked(self, sender, e):
        if self.updating_checkboxes:
            return
        self.update_checkboxes(False)
        self.grids.hide_all_bubbles()

    def on_show_all_checked(self, sender, e):
        if self.updating_checkboxes:
            return
        self.update_checkboxes(True)
        self.grids.show_all_bubbles()

    def update_checkboxes(self, state=None):
        """Update checkboxes visibility based on the state of the grids."""

        self.updating_checkboxes = True
        if state is not None:
            for checkbox in self.checkboxes.values():
                checkbox.IsChecked = state
        else:
            self.checkboxes["top"].IsChecked = self.grids.are_bubbles_visible("top")
            self.checkboxes["bottom"].IsChecked = self.grids.are_bubbles_visible(
                "bottom"
            )
            self.checkboxes["left"].IsChecked = self.grids.are_bubbles_visible("left")
            self.checkboxes["right"].IsChecked = self.grids.are_bubbles_visible("right")

            self.hide_all.IsChecked = self.grids.are_bubbles_visible(reverse=True)
            self.show_all.IsChecked = self.grids.are_bubbles_visible()
        self.updating_checkboxes = False

    def toggle_bubbles(self, sender, e):
        """Toggle the bubbles of the grids based on the checkbox state."""

        if self.updating_checkboxes:
            return
        action = "show" if sender.IsChecked else "hide"
        for direction, checkbox in self.checkboxes.items():
            if checkbox == sender:
                self.grids.toggle_bubbles_by_direction(action, direction)
        # Reset the radio buttons when a checkbox is toggled
        if self.show_all.IsChecked or self.hide_all.IsChecked:
            self.show_all.IsChecked = False
            self.hide_all.IsChecked = False
        self.reset_radio_buttons()

    def reset_radio_buttons(self):
        """Set radio buttons visibility according to the state of the checkboxes."""
        # Temporarily disable event handling to prevent unwanted grid toggles
        self.updating_checkboxes = True

        all_checked = all(checkbox.IsChecked for checkbox in self.checkboxes.values())
        all_unchecked = all(
            not checkbox.IsChecked for checkbox in self.checkboxes.values()
        )
        top_bottom_checked = (
            self.checkboxes["top"].IsChecked and self.checkboxes["bottom"].IsChecked
        )
        right_left_checked = (
            self.checkboxes["right"].IsChecked and self.checkboxes["left"].IsChecked
        )
        top_bottom_unchecked = (
            not self.checkboxes["top"].IsChecked
            and not self.checkboxes["bottom"].IsChecked
        )
        right_left_unchecked = (
            not self.checkboxes["right"].IsChecked
            and not self.checkboxes["left"].IsChecked
        )

        # Reset both radio buttons first
        self.show_all.IsChecked = False
        self.hide_all.IsChecked = False

        if (
            all_checked
            or (right_left_checked and self.top_bottom_collapsed)
            or (top_bottom_checked and self.right_left_collapsed)
        ):
            self.show_all.IsChecked = True
        elif (
            all_unchecked
            or (right_left_unchecked and self.top_bottom_collapsed)
            or (top_bottom_unchecked and self.right_left_collapsed)
        ):
            self.hide_all.IsChecked = True

        # Re-enable event handling
        self.updating_checkboxes = False

    def move_window(self, sender, args):
        self.DragMove()

    def go_back(self, sender, args):
        """Go back to coordinate system selector."""
        self.grids.unhighlight_grids()
        # Return action + current window coordinates
        self.result = {
            "action": "back",
            "window_left": self.Left,
            "window_top": self.Top,
        }
        self.Close()

    def cancel(self, sender, args):
        self.grids.unhighlight_grids()
        if self.transaction_group:
            self.transaction_group.RollBack()
        self.result = "cancel"
        self.Close()

    def handle_key_press(self, sender, args):
        """Handle keyboard input, especially ESC key."""
        if args.Key == System.Windows.Input.Key.Escape:
            self.cancel(None, None)

    def confirm(self, sender, args):
        self.grids.unhighlight_grids()
        self.result = "ok"
        self.Close()


def validate_active_view():
    if active_view.ViewType == DB.ViewType.ProjectBrowser:
        forms.alert(
            "You've selected a view in the project browser. \
					Click inside the active view and try again."
        )
        return False
    elif active_view.ViewType not in VIEW_TYPES:
        forms.alert(
            "The view must be a floor plan, ceiling plan, elevation or section.\n\
		Your active view is : {}".format(
                active_view.ViewType
            )
        )
        return False
    return True


def main():
    if not validate_active_view():
        return

    grid_collector = GridsCollector(doc, active_view)

    if not grid_collector.check_validity():
        return

    tg = DB.TransactionGroup(doc, "Toggle Grids")
    tg.Start()

    # Check if view is elevation/section, if true skip coordinate system selection
    if active_view.ViewType in ELEVATION_VIEWS:
        coordinate_system = "elevation_mode"
        angle_tolerance = 1

        window = ToggleGridWindow.create(
            xamlfile,
            active_view,
            coordinate_system,
            angle_tolerance,
            tg,
            None,
            None,
        )

        if window is not None:
            window.ShowDialog()

            if window.result == "cancel":
                if tg.GetStatus() == DB.TransactionStatus.Started:
                    tg.RollBack()
                return
            elif window.result == "ok":
                if tg.GetStatus() == DB.TransactionStatus.Started:
                    tg.Assimilate()
        else:
            if tg.GetStatus() == DB.TransactionStatus.Started:
                tg.RollBack()
        return

    previous_system = None
    previous_tolerance = None
    window_left = None
    window_top = None

    # Loop to handle back button
    while True:
        selection_result = show_coordinate_system_selector(
            previous_system, previous_tolerance, window_left, window_top
        )
        if selection_result is None:
            if tg.GetStatus() == DB.TransactionStatus.Started:
                tg.RollBack()
            return

        coordinate_system = selection_result["coordinate_system"]
        angle_tolerance = selection_result["angle_tolerance"]
        previous_system = coordinate_system
        previous_tolerance = angle_tolerance

        window_left = selection_result.get("window_left", None)
        window_top = selection_result.get("window_top", None)

        window = ToggleGridWindow.create(
            xamlfile,
            active_view,
            coordinate_system,
            angle_tolerance,
            grid_collector,
            tg,
            window_left,
            window_top,
        )

        if window is not None:
            window.ShowDialog()

            if (
                isinstance(window.result, dict)
                and window.result.get("action") == "back"
            ):
                window_left = window.result.get("window_left", window_left)
                window_top = window.result.get("window_top", window_top)
                continue
            elif window.result == "cancel":
                if tg.GetStatus() == DB.TransactionStatus.Started:
                    tg.RollBack()
                return
            elif window.result == "ok":
                break
        else:
            if tg.GetStatus() == DB.TransactionStatus.Started:
                tg.RollBack()
            return

    if tg.GetStatus() == DB.TransactionStatus.Started:
        tg.Assimilate()


if __name__ == "__main__":
    main()
