"""Match type properties between element types."""
#pylint: disable=import-error,invalid-name,broad-except
from collections import namedtuple

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"

logger = script.get_logger()
output = script.get_output()


PropKeyValue = namedtuple('PropKeyValue', ['name', 'datatype', 'value'])


def get_source_properties(src_type):
    """Return info on selected properties."""
    props = []
    selected_properties = \
        forms.SelectFromList.show(
            [x.Definition.Name for x in src_type.Parameters],
            title='Select Properties to Match',
            button_name='Select Properties',
            multiselect=True
            )
    for tprop in selected_properties or []:
        tp = src_type.LookupParameter(tprop)
        if tp:
            if tp.StorageType == DB.StorageType.Integer:
                props.append(
                    PropKeyValue(
                        name=tprop,
                        datatype=tp.StorageType,
                        value=tp.AsInteger()
                        ))
            elif tp.StorageType == DB.StorageType.Double:
                props.append(
                    PropKeyValue(
                        name=tprop,
                        datatype=tp.StorageType,
                        value=tp.AsDouble()
                        ))
            elif tp.StorageType == DB.StorageType.ElementId:
                props.append(
                    PropKeyValue(
                        name=tprop,
                        datatype=tp.StorageType,
                        value=tp.AsElementId()
                        ))
            else:
                props.append(
                    PropKeyValue(
                        name=tprop,
                        datatype=tp.StorageType,
                        value=tp.AsString()
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
                        dp = dest_type.LookupParameter(pkv.name)
                        if dp and pkv.datatype == dp.StorageType:
                            dp.Set(pkv.value)


# main
with forms.WarningBar(title='Pick source object:'):
    source_element = revit.pick_element()

if source_element:
    source_typeprops = \
        get_source_properties(
            revit.query.get_type(source_element)
            )
    if source_typeprops:
        pick_and_match_types(source_typeprops)
