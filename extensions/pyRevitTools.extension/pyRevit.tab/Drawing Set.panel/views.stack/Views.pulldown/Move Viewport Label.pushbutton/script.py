# encoding: utf-8
# from https://discourse.pyrevitlabs.io/t/i-developed-a-tool-need-help-to-get-it-into-the-new-release-of-pyrevit/7639/3

from pyrevit import DB, UI, script, HOST_APP, revit

doc = HOST_APP.doc
uidoc = HOST_APP.uidoc
script.get_output().close_others()


def move_viewport_label(viewport, point):
    viewminpoint = viewport.GetBoxOutline().MinimumPoint
    new_label_location = point - viewminpoint
    viewport.LabelOffset = new_label_location


def single_point_selection():
    pick_point = uidoc.Selection.PickPoint()
    return pick_point


def single_viewport_selection():
    selected_viewport = None
    filter = ViewportSelectionFilter()
    pick_ref = uidoc.Selection.PickObject(UI.Selection.ObjectType.Element, filter, "Select a viewport")
    selected_viewport = doc.GetElement(pick_ref)
    return selected_viewport


class ViewportSelectionFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, element):
        if not isinstance(element, DB.Viewport):
            return False
        else:
            return True

    def AllowReference(self, reference, position):
        return False


if __name__ == '__main__':
    selected_point = single_point_selection()
    selected_viewport = single_viewport_selection()
    with revit.Transaction("Move Label to Point", doc):
        move_viewport_label(selected_viewport, selected_point)
