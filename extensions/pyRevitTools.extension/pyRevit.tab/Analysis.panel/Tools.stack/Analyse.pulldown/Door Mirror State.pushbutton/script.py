# -*- coding: utf-8 -*-

import time, sys
from pyrevit import script, DB, revit, DOCS, forms
from pyrevit.framework import List

doc = DOCS.doc
output = script.get_output()

DOORDIR_STANDARD_PARAM = "DoorFamilyOpeningDirection_standard"
DOORDIR_MIRRORED_PARAM = "DoorFamilyOpeningDirection_mirrored"
DOORDIR_WRITEBACK_PARAM = "Door Wing Opening Direction"
DOORDIR_ERROR_VALUE = "-"  # Value if the family doesn't have shared param. above

# MAIN
timer_start = time.time()

# GET ALL DOORS
doors_collector = (
    DB.FilteredElementCollector(doc)
    .OfCategory(DB.BuiltInCategory.OST_Doors)
    .WhereElementIsNotElementType()
    .ToElements()
)

if not doors_collector:
    forms.alert("No doors found in the model.", title="Warning")
    script.exit()


def parameter_exists(parameter_name):
    binding_map = doc.ParameterBindings
    iterator = binding_map.ForwardIterator()
    iterator.Reset()
    while iterator.MoveNext():
        if iterator.Key.Name == parameter_name:
            return True
    return False


if not parameter_exists(DOORDIR_WRITEBACK_PARAM):
    print(
        "The parameter '{}' does not exist in the current document.\n"
        "Please create the parameter as an instance parameter, option different values for groupes,\n"
        "for the category doors in the project.".format(DOORDIR_WRITEBACK_PARAM)
    )
    script.exit()

count_parameter = 0
count_not_parameter = 0
doors_without_parameter = []
data_doors_changed = []

with revit.Transaction(doc, "DoorMirrorState"):
    for door in doors_collector:
        try:
            if door.Mirrored:
                value = door.LookupParameter(DOORDIR_MIRRORED_PARAM).AsString()
            else:
                value = door.LookupParameter(DOORDIR_STANDARD_PARAM).AsString()
            count_parameter += 1

        except AttributeError:
            value = DOORDIR_ERROR_VALUE
            count_not_parameter += 1

            door_family = door.get_Parameter(
                DB.BuiltInParameter.ELEM_FAMILY_PARAM
            ).AsValueString()
            door_type = door.get_Parameter(
                DB.BuiltInParameter.ELEM_TYPE_PARAM
            ).AsValueString()
            door_name = "{family}-{type}".format(family=door_family, type=door_type)
            if door_name not in doors_without_parameter:
                doors_without_parameter.append(door_name)

        try:
            door_out_param = door.LookupParameter(DOORDIR_WRITEBACK_PARAM)

            door_out_param_old = door_out_param.AsString()
            door_out_param_new = value
            if door_out_param_old != door_out_param_new:
                door_out_param_changed = "{} -> {}".format(
                    door_out_param_old, door_out_param_new
                )
                door_name = door.Name
                door_changed_link = output.linkify(door.Id)
                data_doors_changed.append(
                    [door_name, door_out_param_changed, door_changed_link]
                )
            door_out_param.Set(str(value))
        except AttributeError:
            forms.alert(
                "Please make sure instance parameter exists: {}".format(
                    DOORDIR_WRITEBACK_PARAM
                )
            )
            script.exit()

output.print_md(
    "### Number of doors found in the project: {} \n"
    "- With writeback parameters defined in door family: {}\n"
    "- Without writeback parameters defined in door family: {}\n"
    "- Parameters missing: '{}', '{}'\n"
    "- You will find in the folder of the script a shared parameter file containing these parameters.\n"
    "- The default writeback value for doors without defined values will be: '{}'\n"
    "---\n".format(
        len(doors_collector),
        count_parameter,
        count_not_parameter,
        DOORDIR_STANDARD_PARAM,
        DOORDIR_MIRRORED_PARAM,
        DOORDIR_ERROR_VALUE,
    )
)

output.print_md("### Door families without writeback parameter defined in family:")
for door_type in doors_without_parameter:
    print(door_type)
output.print_md("---\n### Changes to previous run of the script:")

if data_doors_changed:
    output.print_table(
        table_data=data_doors_changed,
        title="Doors with changed parameters:",
        columns=["Door", "Changed Value (old->new)", "ElementId"],
    )
else:
    output.print_md("#### No doors with changed parameters were found.")

elapsed_time = time.time() - timer_start
output.print_md("---\n#### Script has finished in {:.2f}s".format(elapsed_time))
