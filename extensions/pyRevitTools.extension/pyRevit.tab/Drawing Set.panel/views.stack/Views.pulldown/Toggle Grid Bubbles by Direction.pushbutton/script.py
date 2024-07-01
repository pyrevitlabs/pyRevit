# -*- coding: UTF-8 -*-
import sys
import clr
clr.AddReference('System.Windows.Forms')
clr.AddReference('IronPython.Wpf')
clr.AddReference('System')

from System import Windows
from pyrevit import DB, script, forms, HOST_APP
from rpw import db
import wpf

doc = HOST_APP.doc
active_view = doc.ActiveView
xamlfile = script.get_bundle_file("ui.xaml")

VIEW_TYPES = [DB.ViewType.FloorPlan,
			  DB.ViewType.Elevation,
			  DB.ViewType.Section,
			  DB.ViewType.CeilingPlan]


class CustomGrids:
	def __init__(self, document, view):
		"""Initialize with the document and view, and collect all grids visible in the view."""
		self.__view = view
		if view.ViewType not in VIEW_TYPES:
			forms.alert('The view must be a floor plan, ceiling plan, elevation or section.')
			sys.exit()
			# raise ValueError('The view must be a floor plan, elevation, section, or ceiling plan.')
		self.__view_type = view.ViewType
		self.__grids = [grid for grid in DB.FilteredElementCollector(document).OfCategory(
			DB.BuiltInCategory.OST_Grids).WhereElementIsNotElementType().ToElements() if grid.CanBeVisibleInView(view)]

	def grids(self):
		"""Return the collected grids."""
		return self.__grids

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

	def are_bubbles_visible(self, direction=None):
		"""Check if the bubbles of the grids are visible."""
		assert direction in {'top', 'bottom', 'right',
							 'left'}, "Invalid direction, must be 'top', 'bottom', 'right', or 'left'."

		coordinate = self.get_coordinate_by_direction(direction)

		if direction in {'top', 'bottom'}:
			grids = self.get_vertical_grids()
		else:
			grids = self.get_horizontal_grids()

		if self.__view_type == DB.ViewType.FloorPlan:
			coor_xyz = DB.XYZ(0, coordinate, 0)
		elif self.__view_type == DB.ViewType.Section or self.__view_type == DB.ViewType.Elevation:
			coor_xyz = DB.XYZ(0, 0, coordinate)

		for grid in grids:
			xyz_0, xyz_1 = self.get_endpoints(grid)

			if (xyz_0.DistanceTo(coor_xyz) < xyz_1.DistanceTo(coor_xyz) and grid.IsBubbleVisibleInView(DB.DatumEnds.End0, self.__view)) or\
				(xyz_0.DistanceTo(coor_xyz) > xyz_1.DistanceTo(coor_xyz) and grid.IsBubbleVisibleInView(DB.DatumEnds.End1, self.__view)):
				return True

		return False

	def get_vertical_grids(self):
		"""Get all vertical grids."""
		return self.filter_grids_by_orientation(is_vertical=True)

	def get_horizontal_grids(self):
		"""Get all horizontal grids."""
		return self.filter_grids_by_orientation(is_vertical=False)

	def get_bounding_box(self, grid):
		"""Get the bounding box of a grid in the view."""
		return grid.get_BoundingBox(self.__view)

	def get_coordinate_by_direction(self, direction=None):
		"""Get the maximum or minimum value among the bounding boxes of the grids."""

		if direction in {'top', 'bottom', 'right', 'left'}:
			if direction in {'top', 'bottom'}:
				grids = self.get_vertical_grids()
				axis = 'Y' if self.__view_type == DB.ViewType.FloorPlan else 'Z'
			else:  # direction in {'right', 'left'}
				grids = self.get_horizontal_grids()
				axis = 'X' if self.__view_type == DB.ViewType.FloorPlan else 'Y'
				# todo: check if the axis is correct for section and elevation views

			bounding_boxes = [self.get_bounding_box(grid) for grid in grids]

			if direction == 'top' or direction == 'right':
				return max(getattr(bb.Max, axis) for bb in set(bounding_boxes) if bb)
			else:  # direction == 'bottom' or direction == 'left'
				return min(getattr(bb.Min, axis) for bb in set(bounding_boxes) if bb)

	@db.Transaction.ensure('Hide all bubbles')
	def hide_all_bubbles(self):
		"""Hide the bubbles of all grids in the view."""
		for grid in self.grids():
			if grid.CanBeVisibleInView(self.__view):
				grid.HideBubbleInView(DB.DatumEnds.End0, self.__view)
				grid.HideBubbleInView(DB.DatumEnds.End1, self.__view)

	@db.Transaction.ensure('Show all bubbles')
	def show_all_bubbles(self):
		"""Show the bubbles of all grids in the view."""
		for grid in self.grids():
			if grid.CanBeVisibleInView(self.__view):
				grid.ShowBubbleInView(DB.DatumEnds.End0, self.__view)
				grid.ShowBubbleInView(DB.DatumEnds.End1, self.__view)

	@db.Transaction.ensure('Toggle bubbles')
	def toggle_bubbles(self, grid, action, end=None):
		"""Toggle the bubbles of all grids in the view."""
		map_end = {0: DB.DatumEnds.End0, 1: DB.DatumEnds.End1}
		if end == 0 or end == 1:
			if action == 'hide':
				grid.HideBubbleInView(map_end[end], self.__view)
			else:
				grid.ShowBubbleInView(map_end[end], self.__view)
		else:
			if action == 'hide':
				grid.HideBubbleInView(DB.DatumEnds.End0, self.__view)
				grid.HideBubbleInView(DB.DatumEnds.End1, self.__view)
			else:
				grid.ShowBubbleInView(DB.DatumEnds.End0, self.__view)
				grid.ShowBubbleInView(DB.DatumEnds.End1, self.__view)

	def toggle_bubbles_by_direction(self, action, direction):
		"""
		Toggle bubbles based on the specified direction.
		"""

		coordinate = self.get_coordinate_by_direction(direction)
		if direction in {'top', 'bottom'}:
			grids = self.get_vertical_grids()
			if self.__view_type == DB.ViewType.FloorPlan or self.__view_type == DB.ViewType.CeilingPlan:
				coor_xyz = DB.XYZ(0, coordinate, 0)
			elif self.__view_type == DB.ViewType.Section or self.__view_type == DB.ViewType.Elevation:
				coor_xyz = DB.XYZ(0, 0, coordinate)
		else:
			grids = self.get_horizontal_grids()
			coor_xyz = DB.XYZ(coordinate, 0, 0)

		for grid in grids:
			xyz_0, xyz_1 = self.get_endpoints(grid)

			if xyz_0.DistanceTo(coor_xyz) < xyz_1.DistanceTo(coor_xyz):
				self.toggle_bubbles(grid, action, 0)
			else:
				self.toggle_bubbles(grid, action, 1)


class MyWindow(Windows.Window):
	def __init__(self):
		wpf.LoadComponent(self, xamlfile)
		self.grids = CustomGrids(doc, active_view)

		# Flag to control event triggering
		self.updating_checkboxes = False

		# Find radio buttons
		self.hide_all = self.FindName("hide_all")
		self.show_all = self.FindName("show_all")

		self.checkboxes = {
			"top": self.FindName("check_top"),
			"left": self.FindName("check_left"),
			"right": self.FindName("check_right"),
			"bottom": self.FindName("check_bottom")
		}

		# Attach event handlers
		self.hide_all.Checked += self.on_hide_all_checked
		self.show_all.Checked += self.on_show_all_checked

		self.check_top.Checked += self.toggle_top_bubbles
		self.check_top.Unchecked += self.toggle_top_bubbles

		self.check_left.Checked += self.toggle_left_bubbles
		self.check_left.Unchecked += self.toggle_left_bubbles

		self.check_right.Checked += self.toggle_right_bubbles
		self.check_right.Unchecked += self.toggle_right_bubbles

		self.check_bottom.Checked += self.toggle_bottom_bubbles
		self.check_bottom.Unchecked += self.toggle_bottom_bubbles

		# Initialize the checkboxes based on Revit grid states
		self.update_checkboxes()

	def on_hide_all_checked(self, sender, e):
		self.update_checkboxes(False)
		self.trigger_checkbox_events()

	def on_show_all_checked(self, sender, e):
		self.update_checkboxes(True)
		self.trigger_checkbox_events()

	def update_checkboxes(self, state=None):
		self.updating_checkboxes = True
		if state is not None:
			for checkbox in self.checkboxes.values():
				checkbox.IsChecked = state
		else:
			self.checkboxes["top"].IsChecked = self.grids.are_bubbles_visible('top')
			self.checkboxes["bottom"].IsChecked = self.grids.are_bubbles_visible('bottom')
			self.checkboxes["left"].IsChecked = self.grids.are_bubbles_visible('left')
			self.checkboxes["right"].IsChecked = self.grids.are_bubbles_visible('right')
		self.updating_checkboxes = False

	def trigger_checkbox_events(self):
		# Trigger the click events for each checkbox
		self.toggle_top_bubbles(self.check_top, None)
		self.toggle_left_bubbles(self.check_left, None)
		self.toggle_right_bubbles(self.check_right, None)
		self.toggle_bottom_bubbles(self.check_bottom, None)

	def toggle_top_bubbles(self, sender, e):
		if self.updating_checkboxes:
			return
		if self.checkboxes["top"].IsChecked:
			self.grids.toggle_bubbles_by_direction('show', 'top')
		else:
			self.grids.toggle_bubbles_by_direction('hide', 'top')

	def toggle_bottom_bubbles(self, sender, e):
		if self.updating_checkboxes:
			return
		if self.checkboxes["bottom"].IsChecked:
			self.grids.toggle_bubbles_by_direction('show', 'bottom')
		else:
			self.grids.toggle_bubbles_by_direction('hide', 'bottom')


	def toggle_right_bubbles(self, sender, e):
		if self.updating_checkboxes:
			return
		if self.checkboxes["right"].IsChecked:
			self.grids.toggle_bubbles_by_direction('show', 'right')
		else:
			self.grids.toggle_bubbles_by_direction('hide', 'right')


	def toggle_left_bubbles(self, sender, e):
		if self.updating_checkboxes:
			return
		if self.checkboxes["left"].IsChecked:
			self.grids.toggle_bubbles_by_direction('show', 'left')
		else:
			self.grids.toggle_bubbles_by_direction('hide', 'left')

	def close_screen(self, sender, args):
		self.Close()

	def move_window(self, sender, args):
		self.DragMove()

	def fermer(self, sender, args):
		self.Close()


with db.TransactionGroup('Toggle Grids'):
	MyWindow().ShowDialog()
