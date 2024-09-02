# encoding: utf-8
# from https://discourse.pyrevitlabs.io/t/i-developed-a-tool-need-help-to-get-it-into-the-new-release-of-pyrevit/7639/3

from pyrevit import DB
from pyrevit.revit import pick_point, pick_element_by_category, Transaction
from pyrevit.forms import alert


def move_viewport_label(viewport, point):
    viewminpoint = viewport.GetBoxOutline().MinimumPoint
    new_label_location = point - viewminpoint
    viewport.LabelOffset = new_label_location


if __name__ == '__main__':
    selected_point = pick_point("Select a point")
    selected_viewport = pick_element_by_category(DB.BuiltInCategory.OST_Viewports, "Select a viewport")
    if selected_point is not None and selected_viewport is not None:
        with Transaction("Move Label to Point"):
            move_viewport_label(selected_viewport, selected_point)
    else:
        alert("Invalid selection. Please try again.")
