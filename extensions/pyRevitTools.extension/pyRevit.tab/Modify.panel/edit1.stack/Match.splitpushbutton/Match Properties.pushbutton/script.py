"""Match instance or type properties between elements and their types.

Shift+Click:
Reapply the previous matched properties.

"""
import pickle

from pyrevit import revit, DB, EXEC_PARAMS
from pyrevit import forms
from pyrevit import script

from match.match_utils import get_source_properties, match_prop


logger = script.get_logger()
output = script.get_output()


MEMFILE = script.get_document_data_file(
    file_id="MatchSelectedProperties", file_ext="pym", add_cmd_name=False
)


def recall():
    """Load last matched properties from memory."""
    data = []
    try:
        with open(MEMFILE, "rb") as mf:
            data = pickle.load(mf)
    except Exception as ex:
        logger.debug("Failed loading matched properties from memory | %s", str(ex))
    return data


def remember(src_props):
    """Save selected matched properties to memory."""
    with open(MEMFILE, "wb") as mf:
        pickle.dump(src_props, mf)


# main
source_props = []
if EXEC_PARAMS.config_mode:
    target_type, source_props = recall()
    logger.debug("Recalled data: %s", source_props)

if not source_props:
    # try use selected elements
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
        source_element = None
        # ask for type of elements to match
        # some are not selectable in graphical views
        target_type = forms.CommandSwitchWindow.show(
            ["Elements", "Views"], message="Pick type of targets:"
        )

        # determine source element
        if target_type == "Elements":
            with forms.WarningBar(title="Pick source object:"):
                source_element = revit.pick_element()
        elif target_type == "Views":
            source_element = forms.select_views(
                title="Select Source View", multiple=False
            )

    # grab properties from source element
    if source_element:
        if not source_props:
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
