# -*- coding: utf-8 -*-
"""tmpgfx example — warning icon on a picked element."""

import traceback

from pyrevit import revit, UI, script
from pyrevit.compat import get_elementid_value_func
from pyrevit.framework import Guid

from pyrevit.revit.tmpgfx import ControlManager, Handler


# Revit context


uidoc = revit.uidoc
doc = revit.doc

get_elementid_value = get_elementid_value_func()

STATE_ENVVAR = "PYREVITDEV_TMPGFX_EXAMPLE"
HANDLER_ID = Guid("6f0c2a7e-5d1b-4f0a-9c57-2b6f8a1d4e93")

# Bundle icon path — resolved once at module level


ICON_PATH = script.get_bundle_file("warning.bmp")

if not ICON_PATH:
    raise IOError(
        "warning.bmp not found in script bundle. "
        "Place a 32x32 24-bit BMP named 'warning.bmp' next to script.py."
    )


# Custom handler
class WarningHandler(Handler):
    """Shows a TaskDialog with element info when a warning icon is clicked."""

    def __init__(self):
        Handler.__init__(
            self,
            guid=HANDLER_ID,
            name="pyRevit Warning Icon Handler",
            description="Displays element info on warning icon click",
            vendor_id="pyRevit",
        )

    def on_click(self, index, payload):
        """Show element name and Id when the warning icon is clicked.

        Args:
            index (int): Control index that was clicked.
            payload: The DB.Element stored when the control was created.
        """
        try:
            if payload is None:
                UI.TaskDialog.Show(
                    "Warning Icon Clicked",
                    "Control index: {}\n(no element linked)".format(index),
                )
                return

            elem = payload
            UI.TaskDialog.Show(
                "Warning Icon Clicked",
                "Element: {}\nId: {}".format(
                    elem.Name,
                    get_elementid_value(elem.Id),
                ),
            )
        except Exception:
            print(traceback.format_exc())


def get_manager():
    """Return this document's manager, reusing the one handler of earlier runs."""
    state = script.get_envvar(STATE_ENVVAR)
    if not state:
        state = {"handler": WarningHandler(), "managers": {}}
        script.set_envvar(STATE_ENVVAR, state)
    managers = state["managers"]
    key = doc.GetHashCode()
    if key not in managers or not managers[key][0].IsValidObject:
        managers[key] = (doc, ControlManager(doc, handler=state["handler"]))
    return managers[key][1]


# Pick an element


elem = revit.pick_element()
if not elem:
    script.exit()

bbox = elem.get_BoundingBox(None)

if not bbox:
    UI.TaskDialog.Show("Error", "Selected element has no bounding box.")
    script.exit()

center = (bbox.Min + bbox.Max) * 0.5


# Get the shared handler + manager, place the control


mgr = get_manager()

active_view = uidoc.ActiveView

control_index = mgr.add_control(
    icon_path=ICON_PATH,
    position=center,
    view=active_view,
    payload=elem,
)

if control_index == -1:
    print("Failed to create in-canvas control.")
    script.exit()

print(
    "Warning icon placed (control index: {}, element: '{}', id: {}).".format(
        control_index,
        elem.Name,
        get_elementid_value(elem.Id),
    )
)
print("Click the icon in the canvas to see element info.")
print("No icon? Try a 3D view or a floor plan. Shift-click removes the icons.")
print("Controls in active view: {}".format(mgr.control_count(active_view)))
