"""Match instance or type properties between elements and their types.

Shift+Click:
Reapply the previous matched properties.

"""
#pylint: disable=import-error,invalid-name,broad-except
import pickle

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"

logger = script.get_logger()
output = script.get_output()


class PropKeyValue(object):
    """Storage class for matched property info and value."""
    def __init__(self, name, datatype, value, istype):
        self.name = name
        self.datatype = datatype
        self.value = value
        self.istype = istype

    def __repr__(self):
        return str(self.__dict__)


MEMFILE = script.get_document_data_file(
    file_id='MatchSelectedProperties',
    file_ext='pym',
    add_cmd_name=False
    )


def match_prop(dest_inst, dest_type, src_props):
    """Match given properties on target instance or type"""
    for pkv in src_props:
        logger.debug("Applying %s", pkv.name)

        # determine target
        target = dest_type if pkv.istype else dest_inst
        # ensure target is valid if it is type
        if pkv.istype and not target:
            logger.warning("Element type is not accessible.")
            continue
        logger.debug("Target is %s", target)

        # find parameter
        dparam = target.LookupParameter(pkv.name)
        if dparam and pkv.datatype == dparam.StorageType:
            try:
                if dparam.StorageType == DB.StorageType.Integer:
                    dparam.Set(pkv.value or 0)
                elif dparam.StorageType == DB.StorageType.Double:
                    dparam.Set(pkv.value or 0.0)
                elif dparam.StorageType == DB.StorageType.ElementId:
                    dparam.Set(DB.ElementId(pkv.value))
                else:
                    dparam.Set(pkv.value or "")
            except Exception as setex:
                logger.warning(
                    "Error applying value to: %s | %s",
                    pkv.name, setex)
                continue
        else:
            logger.debug("Parameter \"%s\"not found on target.", pkv.name)


def get_source_properties(src_element):
    """Return info on selected properties."""
    props = []

    src_type = revit.query.get_type(src_element)

    selected_params = forms.select_parameters(
        src_element,
        title="Select Parameters",
        multiple=True,
        include_instance=True,
        include_type=True
    ) or []

    logger.debug("Selected parameters: %s", [x.name for x in selected_params])

    for sparam in selected_params:
        logger.debug("Reading %s", sparam.name)
        target = src_type if sparam.istype else src_element
        tparam = target.LookupParameter(sparam.name)
        if tparam:
            if tparam.StorageType == DB.StorageType.Integer:
                value = tparam.AsInteger()
            elif tparam.StorageType == DB.StorageType.Double:
                value = tparam.AsDouble()
            elif tparam.StorageType == DB.StorageType.ElementId:
                value = tparam.AsElementId().IntegerValue
            else:
                value = tparam.AsString()

            props.append(
                PropKeyValue(
                    name=sparam.name,
                    datatype=tparam.StorageType,
                    value=value,
                    istype=sparam.istype
                    ))

    return props


def pick_and_match_types(src_props):
    """Match property values for selected types."""
    with forms.WarningBar(title="Pick objects to match type properties:"):
        while True:
            dest_element = revit.pick_element()
            if not dest_element:
                break

            dest_type = revit.query.get_type(dest_element)
            with revit.Transaction("Match Type Properties"):
                match_prop(dest_element, dest_type, src_props)


def recall():
    """Load last matched properties from memory."""
    data = []
    try:
        with open(MEMFILE, 'r') as mf:
            data = pickle.load(mf)
    except Exception as ex:
        logger.debug(
            "Failed loading matched properties from memory | %s", str(ex)
            )
    return data


def remember(src_props):
    """Save selected matched properties to memory."""
    with open(MEMFILE, 'w') as mf:
        pickle.dump(src_props, mf)


# main
source_props = []
if __shiftclick__:    #pylint: disable=undefined-variable
    target_type, source_props = recall()
    logger.debug("Recalled data: %s", source_props)

if not source_props:
    source_element = None

    # ask for type of elements to match
    # some are not selectable in graphical views
    target_type = \
        forms.CommandSwitchWindow.show(
            ["Elements", "Views"],
            message="Pick type of targets:")

    # determine source element
    if target_type == "Elements":
        with forms.WarningBar(title="Pick source object:"):
            source_element = revit.pick_element()
    elif target_type == "Views":
        source_element = \
            forms.select_views(title="Select Source View", multiple=False)

    # grab properties from source element
    if source_element:
        if not source_props:
            source_props = get_source_properties(source_element)
            remember((target_type, source_props))

# apply values
if source_props:
    if target_type == "Elements":
        pick_and_match_types(source_props)
    elif target_type == "Views":
        target_views = \
            forms.select_views(title="Select Target Views", multiple=True)
        if target_views:
            with revit.Transaction("Match Type Properties"):
                for tview in target_views:
                    tview_type = revit.query.get_type(tview)
                    match_prop(tview, tview_type, source_props)
