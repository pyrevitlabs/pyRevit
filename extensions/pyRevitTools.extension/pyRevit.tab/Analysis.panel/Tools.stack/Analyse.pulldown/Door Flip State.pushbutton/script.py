# -*- coding: utf-8 -*-

__title__ = "DoorFlipState"
__author__ = "Jakob Steiner"
__doc__ = """Version = 0.3
Date    = 13.04.2025
_____________________________________________________________________
Description:

Writes the flip state (aka Left/Right) of doors back to an instance
parameter 'Flügel Aufgehrichtung' in doors. This needs to be an instance
parameter of type text with the option different values for group instances.
Prints a summary of 
accomplished job. All families to treat need 2 shared parameters
'Türfamilienaufgehrichtung_standard'
'Türfamilienaufgehrichtung_gespiegelt'
as instances with values corresponding, as in family defined standard
to write back to parameter 'Türaufgehrichtung'. For families who have
a symtetry chechbox standard value my be changed by conditional
statement in family:
(f.ex -> if(Anschlagseite gespiegelt, "Tür Rechts", "Tür Links"))

_____________________________________________________________________
Prerequisites:
In familys as instance, standard value as "blocked" formula
[Parameter] - 'Türfamilienaufgehrichtung_standard'
[Parameter] - 'Türfamilienaufgehrichtung_gespiegelt'

In project as instance:
[Parameter] - 'Flügel Aufgehrichtung'
_____________________________________________________________________
Last update:

- V 0.1 Creation(24.05.2021)
- V 0.2 (07.06.2021)
 - Refactored 
 - Show Family/Types that did not have parameters set.
- V 0.3 (13.04.2025)
 - List changes in doors
_____________________________________________________________________

"""
#--------------------------------------------------------------------------------------------------------------------
#IMPORTS
# System
import time, sys
#pyRevit
from pyrevit import script

from Autodesk.Revit.DB import *
from collections import defaultdict

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
app = __revit__.Application
output = script.get_output()
#--------------------------------------------------------------------------------------------------------------------
#GLOBAL PARAMETERS
TUERAUFG_STANDARD_PARAMETER             = "Türfamilienaufgehrichtung_standard"
TUERAUFG_STANDARD_GESPIEGELT_PARAMETER  = "Türfamilienaufgehrichtung_gespiegelt"
TUERAUFG_WRITEBACK_PARAMETER            = "Flügel Aufgehrichtung"
TUERAUFG_ERROR_VALUE                    = "-" # Value if the family does't have shared param. above

#--------------------------------------------------------------------------------------------------------------------
#MAIN
timer_start = time.time()

# GET ALL DOORS
doors_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsNotElementType().ToElements()
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
if not parameter_exists(TUERAUFG_WRITEBACK_PARAMETER):
    print("The parameter '{}' does not exist in the current document.".format(TUERAUFG_WRITEBACK_PARAMETER))
    print("Please create the parameter as an instance parameter, option different values for groupes,")
    print("for the category doors in the project.")

    sys.exit()

# CREATE CONTAINERS
count_parameter = 0
count_not_parameter = 0
doors_without_parameter = []
data_doors_changed = []

t = Transaction(doc,__title__)
t.Start()
# CREATE A DICT FOR DOORS WITH CHANGED PARAMETERS
door_changed =[]
# LOOP THROUGH ALL DOORS
for door in doors_collector:
    # GET VALUE
    try:
        if door.Mirrored:
            value = door.LookupParameter(TUERAUFG_STANDARD_GESPIEGELT_PARAMETER).AsString()
        else:
            value = door.LookupParameter(TUERAUFG_STANDARD_PARAMETER).AsString()
        count_parameter +=1

    except:
        # IF VALUE IS UNAVAILABLE - USE DEFAULT ERROR VALUE
        value = TUERAUFG_ERROR_VALUE
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
        door_out_param = door.LookupParameter(TUERAUFG_WRITEBACK_PARAMETER)
        
        # WRITE CHANGES IN PARAMETERS
        door_out_param_old = door.LookupParameter(TUERAUFG_WRITEBACK_PARAMETER).AsString()
        door_out_param_new = value
        if door_out_param_old != door_out_param_new:
            data_doors_changed.append(door_changed)
            door_out_param_changed = "{} -> {}".format(door_out_param_old, door_out_param_new)
            door_changed.append(door.Name)
            door_changed.append(door_out_param_changed)
            door_changed_link = output.linkify(door.Id)
            door_changed.append(door_changed_link)
        # SET DOOR FLIP STATE TO THE WRITEBACK PARAMETER
        door_out_param.Set(str(value))
    except:
        print("Please make sure OUT instance parameter exists: {}".format(TUERAUFG_WRITEBACK_PARAMETER))
        sys.exit()
t.Commit()

# FINAL PRINT
output.print_md("\nNumber of doors found in the project: {} ".format(len(doors_collector)))
output.print_md("of theese with writeback parameters defined in door family: {}".format(count_parameter))
output.print_md("without writeback parameters defined in door family: {a}".format(a=count_not_parameter,))
output.print_md("The default writeback value for doors without defined values will be : "'"{b}"'" ".format(b=TUERAUFG_ERROR_VALUE))
output.print_md("****************************************************************")
print("door families without writeback parameter defined in family:")
for door_type in doors_without_parameter:
    print(door_type)

print("****************************************************************")
print("Changes to previous run of the script:")

# Create a table for changed parameter values
if data_doors_changed:
    output.print_table(table_data=data_doors_changed, title="Doors with changed parameters:", columns=["Door", "Changed Value", "ElementId"])
else:
    output.print_md("No doors with changed parameters were found.")

# End
output.print_md('---')
output.print_md('#### Script has finished in {}s'.format(time.time() - timer_start))