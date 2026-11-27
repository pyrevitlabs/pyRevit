# -*- coding: utf-8 -*-
"""tmpgfx example — warning icon on a picked element."""

from pyrevit import script
from pyrevit import revit, UI
from pyrevit.revit import query, tmpgfx
from pyrevit.compat import get_elementid_value_func

logger = script.get_logger()
get_elementid_value = get_elementid_value_func()

TOOL_NAME = "pyRevitDev.TemporaryGraphicsExample"
DIALOG_TITLE = "Warning Icon Clicked"


class WarningHandler(tmpgfx.Handler):
    """Shows a TaskDialog with element info when a warning icon is clicked."""

    def __init__(self, guid):
        tmpgfx.Handler.__init__(
            self,
            guid=guid,
            name="pyRevit Warning Icon Handler",
            description="Displays element info on warning icon click",
        )

    def on_click(self, index, payload):
        element = self.clicked_document.GetElement(payload)
        if element is None:
            UI.TaskDialog.Show(DIALOG_TITLE, "The element no longer exists.")
            return
        UI.TaskDialog.Show(
            DIALOG_TITLE,
            "Element: {}\nId: {}".format(
                query.get_name(element), get_elementid_value(element.Id)
            ),
        )


icon_path = script.get_bundle_file("warning.bmp")
element = revit.pick_element()
if not element:
    script.exit()

bbox = element.get_BoundingBox(None)
if not bbox:
    UI.TaskDialog.Show("Error", "Selected element has no bounding box.")
    script.exit()

manager = tmpgfx.get_manager(TOOL_NAME, revit.doc, WarningHandler)
manager.add_control(
    icon_path=icon_path,
    position=(bbox.Min + bbox.Max) * 0.5,
    view=revit.active_view,
    payload=element.Id,
)

print(
    "Warning icon placed on '{}' (id {}).".format(
        query.get_name(element), get_elementid_value(element.Id)
    )
)
print("Click the icon in the canvas to see element info.")
print("No icon? Try a 3D view or a floor plan. Shift-click removes the icons.")
