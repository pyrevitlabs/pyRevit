# -*- coding: UTF-8 -*-
import sys

from System import Windows
from pyrevit import HOST_APP, DB, script, forms
from pyrevit.revit.db import transaction

doc = HOST_APP.doc
uidoc = HOST_APP.uidoc
active_view = doc.ActiveView
xamlfile = script.get_bundle_file("ui.xaml")

VIEW_TYPES = [
    DB.ViewType.FloorPlan,
	DB.ViewType.EngineeringPlan,
    DB.ViewType.Elevation,
    DB.ViewType.Section,
    DB.ViewType.CeilingPlan,
]
PLAN_VIEWS = [DB.ViewType.FloorPlan, DB.ViewType.CeilingPlan, DB.ViewType.EngineeringPlan]
ELEVATION_VIEWS = [DB.ViewType.Elevation, DB.ViewType.Section]


class CustomGrids:
    def __init__(self, document, view):
        """Initialize with the document and view, and collect all grids visible in the view."""
        self.__view = view
        self.__grids = []
        self.is_valid = True

        self.selection = [
            document.GetElement(el_id)
            for el_id in HOST_APP.uidoc.Selection.GetElementIds()
        ]

        if self.selection:
            self.__grids = self.selection
        else:
            self.__grids = [
                grid
                for grid in DB.FilteredElementCollector(document)
                .OfCategory(DB.BuiltInCategory.OST_Grids)
                .WhereElementIsNotElementType()
                .ToElements()
                if grid.CanBeVisibleInView(view)
            ]

        if not self.__grids:
            forms.alert("No grids are visible in the view.")
            self.is_valid = False
            return

    def grids(self):
        """Return the collected grids."""
        return self.__grids

    def is_grid_hidden(self, grids):
        """Check if a grid is hidden in the view."""
        for grid in grids:
            if grid.IsHidden(self.__view):
                return True
        return False

    def get_grid_curve(self, grid):
        """Get the curves of a grid that are specific to the view."""
        return grid.GetCurvesInView(DB.DatumExtentType.ViewSpecific, self.__view)

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

    def filter_grids_by_orientation(self, is_vertical=True):
        """Filter grids based on their orientation."""
        filtered_grids = []
        for g in self.grids():
            pt1, pt2 = self.get_endpoints(g)
            if pt1 and pt2:
                if is_vertical and round(pt1.X, 3) == round(pt2.X, 3):
                    filtered_grids.append(g)
                elif not is_vertical and round(pt1.Y, 3) == round(pt2.Y, 3):
                    filtered_grids.append(g)
        return filtered_grids

    def are_bubbles_visible(self, direction=None, reverse=False):
        """Check if the bubbles of the grids are visible."""

        if not direction:
            # Check if all bubbles are visible
            if not reverse:
                bubbles = [
                    is_visible
                    for grid in self.grids()
                    for is_visible in [
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End0, self.__view),
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End1, self.__view),
                    ]
                ]
            else:
                bubbles = [
                    not is_visible
                    for grid in self.grids()
                    for is_visible in [
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End0, self.__view),
                        grid.IsBubbleVisibleInView(DB.DatumEnds.End1, self.__view),
                    ]
                ]
            return all(bubbles)

        else:
            if direction in {"top", "bottom"}:
                grids = self.get_vertical_grids()
            else:
                grids = self.get_horizontal_grids()
            for grid in grids:
                xyz_0, xyz_1 = self.get_endpoints(grid)
                if direction in {"top", "right"}:
                    ref_point = self.get_bounding_box_corner(grid, "max")
                else:
                    ref_point = self.get_bounding_box_corner(grid, "min")
                if ref_point:
                    if (
                        xyz_0.DistanceTo(ref_point) < xyz_1.DistanceTo(ref_point)
                        and grid.IsBubbleVisibleInView(DB.DatumEnds.End0, self.__view)
                    ) or (
                        xyz_0.DistanceTo(ref_point) > xyz_1.DistanceTo(ref_point)
                        and grid.IsBubbleVisibleInView(DB.DatumEnds.End1, self.__view)
                    ):
                        return True
                else:
                    continue

        return False

    def get_vertical_grids(self):
        """Get all vertical grids."""
        return self.filter_grids_by_orientation(is_vertical=True)

    def get_horizontal_grids(self):
        """Get all horizontal grids."""
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
        """Toggle bubbles based on the specified direction."""

        if direction in {"top", "bottom"}:
            grids = self.get_vertical_grids()
        else:
            grids = self.get_horizontal_grids()
        for grid in grids:
            xyz_0, xyz_1 = self.get_endpoints(grid)
            if direction in {"top", "right"}:
                ref_point = self.get_bounding_box_corner(grid, "max")
            else:
                ref_point = self.get_bounding_box_corner(grid, "min")
            if ref_point:
                if xyz_0.DistanceTo(ref_point) < xyz_1.DistanceTo(ref_point):
                    self.toggle_bubbles(grid, action, 0)
                else:
                    self.toggle_bubbles(grid, action, 1)
            else:
                continue

    @transaction.carryout("Hide all bubbles")
    def hide_all_bubbles(self):
        """Hide the bubbles of all grids in the view."""
        for grid in self.grids():
            if grid.CanBeVisibleInView(self.__view):
                grid.HideBubbleInView(DB.DatumEnds.End0, self.__view)
                grid.HideBubbleInView(DB.DatumEnds.End1, self.__view)

    @transaction.carryout("Show all bubbles")
    def show_all_bubbles(self):
        """Show the bubbles of all grids in the view."""
        for grid in self.grids():
            if grid.CanBeVisibleInView(self.__view):
                grid.ShowBubbleInView(DB.DatumEnds.End0, self.__view)
                grid.ShowBubbleInView(DB.DatumEnds.End1, self.__view)


class ToggleGridWindow(forms.WPFWindow):
    def __init__(self, xaml_source, view, transaction_group=None):
        super(ToggleGridWindow, self).__init__(xaml_source)

        self.view = view
        self.transaction_group = transaction_group
        self.grids = CustomGrids(doc, self.view)

        if not self.grids.is_valid:
            self.is_valid = False
            return
        self.is_valid = True

        # Flags to control the visibility of the checkboxes
        self.right_left_collapsed = False
        self.top_bottom_collapsed = False

        # Flag to control event triggering
        self.updating_checkboxes = False

        # Find radio buttons
        self.hide_all = self.FindName("hide_all")
        self.show_all = self.FindName("show_all")

        self.checkboxes = {
            "top": self.FindName("check_top"),
            "left": self.FindName("check_left"),
            "right": self.FindName("check_right"),
            "bottom": self.FindName("check_bottom"),
        }

        # Display the checkboxes based on the orientation of the grids and the view type
        if self.is_view_elevation() or not self.grids.get_horizontal_grids():
            self.checkboxes["right"].Visibility = Windows.Visibility.Collapsed
            self.checkboxes["left"].Visibility = Windows.Visibility.Collapsed
            self.right_left_collapsed = True

        if not self.grids.get_vertical_grids():
            self.checkboxes["top"].Visibility = Windows.Visibility.Collapsed
            self.checkboxes["bottom"].Visibility = Windows.Visibility.Collapsed
            self.top_bottom_collapsed = True

        self.hide_all.Checked += self.on_hide_all_checked
        self.show_all.Checked += self.on_show_all_checked

        for checkbox in self.checkboxes.values():
            checkbox.Checked += self.toggle_bubbles
            checkbox.Unchecked += self.toggle_bubbles

        self.update_checkboxes()

    @classmethod
    def create(cls, xaml_source, view, transaction_group=None):
        """Factory method to handle a clean exit"""
        window = cls(xaml_source, view, transaction_group)
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

    def move_window(self, sender, args):
        self.DragMove()

    def cancel(self, sender, args):
        if self.transaction_group:
            self.transaction_group.RollBack()
        self.Close()

    def confirm(self, sender, args):
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

    tg = DB.TransactionGroup(doc, "Toggle Grids")
    tg.Start()

    window = ToggleGridWindow.create(xamlfile, active_view, tg)
    if window is not None:
        window.ShowDialog()

    if tg.GetStatus() == DB.TransactionStatus.Started:
        tg.Assimilate()


if __name__ == "__main__":
    main()
