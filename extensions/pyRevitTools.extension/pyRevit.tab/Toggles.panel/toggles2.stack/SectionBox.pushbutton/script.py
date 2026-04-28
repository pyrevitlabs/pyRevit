"""Toggles visibility, active state or a temporary section box in current 3D view"""

from pyrevit import revit, script
from sbox.sbox_actions import toggle, hide, temp_switch


DATA_SLOTNAME = "SectionBox"
TEMP_DATAFILE = script.get_instance_data_file("SectionBoxTemp")
PADDING = 1.0  # feet

my_config = script.get_config()
scope = my_config.get_option("scope", "Visibility")


if scope == "Visibility":
    hide(revit.doc)

if scope == "Active State":
    toggle(revit.doc, DATA_SLOTNAME)

if scope == "Temporary Section Box":
    temp_switch(revit.doc, TEMP_DATAFILE, padding=PADDING)
