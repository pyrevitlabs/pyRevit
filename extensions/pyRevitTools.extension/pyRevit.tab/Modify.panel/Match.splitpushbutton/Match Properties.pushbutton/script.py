"""Match instance or type properties between elements and their types.

Shift+Click:
Reapply the previous match properties.

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


def get_source_properties(src_element):
    """Return info on selected properties."""
    props = []

    src_type = revit.query.get_type(src_element)

    selected_params = forms.select_parameter(
        src_element,
        title='Select Parameters',
        multiple=True,
        include_instance=True,
        include_type=True
    ) or []

    logger.debug('Selected parameters: %s', [x.name for x in selected_params])

    for sparam in selected_params:
        logger.debug('Reading %s', sparam.name)
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
    with forms.WarningBar(title='Pick objects to match type properties:'):
        while True:
            dest_element = revit.pick_element()

            if not dest_element:
                break

            dest_type = revit.query.get_type(dest_element)
            if dest_type:
                with revit.Transaction('Match Type Properties'):
                    for pkv in src_props:
                        logger.debug('Applying %s', pkv.name)
                        target = dest_type if pkv.istype else dest_element
                        logger.debug('Target is %s', target)
                        dparam = target.LookupParameter(pkv.name)
                        if dparam and pkv.datatype == dparam.StorageType:
                            if dparam.StorageType == DB.StorageType.Integer:
                                dparam.Set(pkv.value or 0)
                            elif dparam.StorageType == DB.StorageType.Double:
                                dparam.Set(pkv.value or 0.0)
                            elif dparam.StorageType == DB.StorageType.ElementId:
                                dparam.Set(DB.ElementId(pkv.value))
                            else:
                                dparam.Set(pkv.value or "")


def recall():
    """Load last matched properties from memory."""
    data = []
    try:
        with open(MEMFILE, 'r') as mf:
            data = pickle.load(mf)
    except Exception as ex:
        logger.debug(
            'Failed loading matched properties from memory | %s', str(ex)
            )
    return data


def remember(src_props):
    """Save selected matched properties to memory."""
    with open(MEMFILE, 'w') as mf:
        pickle.dump(src_props, mf)


# main
source_props = []
if __shiftclick__:    #pylint: disable=undefined-variable
    source_props = recall()
    logger.debug('Recalled data: %s', source_props)

if not source_props:
    with forms.WarningBar(title='Pick source object:'):
        source_element = revit.pick_element()

    if source_element:
        if not source_props:
            source_props = get_source_properties(source_element)
            remember(source_props)


if source_props:
    pick_and_match_types(source_props)
