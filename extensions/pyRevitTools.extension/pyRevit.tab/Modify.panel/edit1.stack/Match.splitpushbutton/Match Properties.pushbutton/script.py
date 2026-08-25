# -*- coding: utf-8 -*-
"""Match instance or type properties between elements and their types.

Shift+Click:
Open a modeless recall window pre-filled with the last matched properties.

"""
import pickle

from pyrevit import revit, DB, EXEC_PARAMS
from pyrevit import forms
from pyrevit import script

from match.match_utils import get_source_properties, match_prop
from match.clipboard import RecallWindow


logger = script.get_logger()
output = script.get_output()


MEMFILE = script.get_instance_data_file(file_id="MatchSelectedProperties")


def recall():
    """Load last matched properties from memory."""
    try:
        with open(MEMFILE, "rb") as mf:
            return pickle.load(mf)
    except Exception as ex:
        logger.debug("Failed loading matched properties from memory | %s", str(ex))
    return None, []


def remember(src_props):
    """Save selected matched properties to memory."""
    with open(MEMFILE, "wb") as mf:
        pickle.dump(src_props, mf)


# ── Shift+Click: open modeless recall window ─────────────────────────────────
if EXEC_PARAMS.config_mode:
    target_type, recalled_props = recall()
    RecallWindow(target_type, recalled_props, MEMFILE).Show()
    script.exit()

# ── Normal click ─────────────────────────────────────────────────────────────
source_props = []
source_element = None

selected_elements = revit.get_selection().elements
if len(selected_elements) == 1 and forms.alert(
    "Use selected %s?"
    % ("view" if isinstance(selected_elements[0], DB.View) else "element"),
    yes=True,
    no=True,
):
    source_element = selected_elements[0]
    target_type = "Views" if isinstance(source_element, DB.View) else "Elements"
else:
    target_type = forms.CommandSwitchWindow.show(
        ["Elements", "Views"], message="Pick type of targets:"
    )
    if target_type == "Elements":
        with forms.WarningBar(title="Pick source object:"):
            source_element = revit.pick_element()
    elif target_type == "Views":
        source_element = forms.select_views(
            title="Select Source View", multiple=False
        )

if source_element:
    source_props = get_source_properties(source_element, simple=True)
    remember((target_type, source_props))

# apply values
if source_props:
    if target_type == "Elements":
        with forms.WarningBar(title="Pick objects to match type properties:"):
            while True:
                dest_element = revit.pick_element()
                if not dest_element:
                    break

                dest_type = revit.query.get_type(dest_element)
                with revit.Transaction("Match Type Properties"):
                    # apply type params first
                    match_prop(
                        dest_element, dest_type, [x for x in source_props if x.istype]
                    )
                    # then instance params
                    match_prop(
                        dest_element,
                        dest_type,
                        [x for x in source_props if not x.istype],
                    )

    elif target_type == "Views":
        target_views = forms.select_views(title="Select Target Views", multiple=True)
        if target_views:
            with revit.Transaction("Match Type Properties"):
                for tview in target_views:
                    tview_type = revit.query.get_type(tview)
                    # apply type params first
                    match_prop(tview, tview_type, [x for x in source_props if x.istype])
                    # then instance params
                    match_prop(
                        tview, tview_type, [x for x in source_props if not x.istype]
                    )
