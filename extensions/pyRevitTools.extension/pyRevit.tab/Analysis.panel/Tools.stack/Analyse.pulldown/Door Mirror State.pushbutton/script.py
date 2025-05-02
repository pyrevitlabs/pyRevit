# -*- coding: utf-8 -*-
"""Writes the door swing direction of doors 
to a shared parameter."""
__title__ = "DoorMirrorState"

#IMPORTS
# System
import time, sys
#pyRevit
from pyrevit import script, DB
from pyrevit.framework import List
#Autodesk.Revit.DB
from Autodesk.Revit.DB import Transaction, BuiltInParameter

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application
output = script.get_output()

#GLOBAL PARAMETERS
DOORDIR_STANDARD_PARAM  = "DoorFamilyOpeningDirection_standard"
DOORDIR_MIRRORED_PARAM  = "DoorFamilyOpeningDirection_mirrored"
DOORDIR_WRITEBACK_PARAM = "Door Wing Opening Direction"
DOORDIR_ERROR_VALUE    = "-" # Value if the family does't have shared param. above

#MAIN
timer_start = time.time()

# GET ALL DOORS
doors_collector = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType().ToElements()
if not doors_collector:
    sys.exit("No doors were found in the project.")

# FUNCTION TO CHECK IF PARAMETER EXISTS
def parameter_exists(parameter_name):
    binding_map = doc.ParameterBindings
    iterator = binding_map.ForwardIterator()
    iterator.Reset()
    while iterator.MoveNext():
        if iterator.Key.Name == parameter_name:
            return True
    return False

# CHECK IF TUERAUFG_WRITEBACK_PARAMETER EXISTS
if not parameter_exists(DOORDIR_WRITEBACK_PARAM):
    print("The parameter '{}' does not exist in the current document.".format(DOORDIR_WRITEBACK_PARAM))
    print("Please create the parameter as an instance parameter, option different values for groupes,")
    print("for the category doors in the project.")

    sys.exit()

# CREATE CONTAINERS
count_parameter = 0
count_not_parameter = 0
doors_without_parameter = []
# CREATE A LIST FOR DOORS WITH CHANGED PARAMETERS
data_doors_changed = []

t = Transaction(doc,__title__)
t.Start()
#door_changed =[]
# LOOP THROUGH ALL DOORS
for door in doors_collector:
    # GET VALUE
    try:
        if door.Mirrored:
            value = door.LookupParameter(DOORDIR_MIRRORED_PARAM).AsString()
        else:
            value = door.LookupParameter(DOORDIR_STANDARD_PARAM).AsString()
        count_parameter +=1

    except:
        # IF VALUE IS UNAVAILABLE - USE DEFAULT ERROR VALUE
        value = DOORDIR_ERROR_VALUE
        count_not_parameter += 1

        # LOG DOOR TYPE WITHOUT VALUE
        door_family = door.get_Parameter(BuiltInParameter.ELEM_FAMILY_PARAM).AsValueString()
        door_type   = door.get_Parameter(BuiltInParameter.ELEM_TYPE_PARAM).AsValueString()
        door_name   = "{family}-{type}".format(family=door_family, type=door_type)
        if door_name not in doors_without_parameter:
            doors_without_parameter.append(door_name)

    # SET PARAMETER
    try:
        # CHECK IF THE WRITEBACK PARAMETER EXISTS
        door_out_param = door.LookupParameter(DOORDIR_WRITEBACK_PARAM)
        
        # WRITE CHANGES IN PARAMETERS
        door_out_param_old = door_out_param.AsString()
        door_out_param_new = value
        if door_out_param_old != door_out_param_new:
            door_out_param_changed = "{} -> {}".format(door_out_param_old, door_out_param_new)
            door_name = door.Name
            door_changed_link = output.linkify(door.Id)
            data_doors_changed.append([door_name, door_out_param_changed, door_changed_link])
        # SET DOOR FLIP STATE TO THE WRITEBACK PARAMETER
        door_out_param.Set(str(value))
    except:
        print('Please make sure OUT instance parameter exists: {}'.format(DOORDIR_WRITEBACK_PARAM))
        sys.exit()
t.Commit()

# FINAL PRINT
output.print_md('### Number of doors found in the project: {} '.format(len(doors_collector)))
output.print_md('of these with writeback parameters defined in door family: {}'.format(count_parameter))
output.print_md('without writeback parameters defined in door family: {a}'.format(a=count_not_parameter,))
output.print_md('parameters missing: '"'{b}'"', '"'{c}'"''.format(b=DOORDIR_STANDARD_PARAM, c=DOORDIR_MIRRORED_PARAM))
output.print_md('you will find in the folder of the script a shared parameter file containing this parameters.')
output.print_md('The default writeback value for doors without defined values will be : '" {d} "' '.format(d=DOORDIR_ERROR_VALUE))
output.print_md('---')
output.print_md('### Door families without writeback parameter defined in family:')
for door_type in doors_without_parameter:
    print(door_type)
output.print_md('---')
output.print_md('### Changes to previous run of the script:')

# Create a table for changed parameter values
if data_doors_changed:
    output.print_table(table_data=data_doors_changed, title="Doors with changed parameters:", columns=["Door", "Changed Value (old->new)", "ElementId"])
else:
    output.print_md('#### No doors with changed parameters were found.')

# End
output.print_md('---')
output.print_md('#### Script has finished in {}s'.format(time.time() - timer_start))