# -*- coding: utf-8 -*-

"""Lists all openings in the project and creates 
a selection filter for them."""

# Sytem
import time

# Revit
from Autodesk.Revit.DB import BuiltInCategory, ElementMulticategoryFilter, FilteredElementCollector, Opening, SelectionFilterElement, Transaction, ElementId

# pyRevit
from pyrevit import script
from pyrevit.framework import List
doc         =__revit__.ActiveUIDocument.Document
uidoc       =__revit__.ActiveUIDocument
output      = script.get_output()
selection   = uidoc.Selection
timer_start = time.time()

# GET ALL OPENINGS IN THE PROJECT

# List of categories
cats = [BuiltInCategory.OST_FloorOpening,
        BuiltInCategory.OST_SWallRectOpening,
        BuiltInCategory.OST_ShaftOpening,
        BuiltInCategory.OST_RoofOpening]
list_cats = List[BuiltInCategory](cats)

# Create filter
multi_cat_filter = ElementMulticategoryFilter(list_cats)

# Apply filter to filteredElementCollector
all_elements = FilteredElementCollector(doc)\
                .WherePasses(multi_cat_filter)\
                .WhereElementIsNotElementType()\
                .ToElements()

# Get elements for selection filter
element_ids = FilteredElementCollector(doc).OfClass(Opening).ToElementIds()
element_ids = List[ElementId](element_ids)

# Declaration of a list to contains list of wanted element properties
data = []

# Collect information about the object and put it into in the data list.
for e in all_elements:
    el = []
    el.append(e.Name)
    el.append(e.Id)
    # add IFC Classification if parameter exist
    e_link = output.linkify(e.Id)
    el.append(e_link)
    data.append(el)

# Get All Selection Filters
all_sel_filters  = FilteredElementCollector(doc).OfClass(SelectionFilterElement).ToElements()
dict_sel_filters = {f.Name: f for f in all_sel_filters}

try:
    t = Transaction(doc, 'Create Openings Filter')
    t.Start()

    # Selection Filter Name
    new_filter_name = '0_ShaftOpenings'

    # Create new if doesn't exist
    if new_filter_name not in dict_sel_filters:
        new_fil = SelectionFilterElement.Create(doc, new_filter_name)
        new_fil.AddSet(element_ids)
        print ('Created a filter called : {}'.format(new_filter_name))

    # Update if already exists
    else:
        existing_fil = dict_sel_filters[new_filter_name]
        existing_fil.AddSet(element_ids)
        print ('Updated a filter called : {}'.format(new_filter_name))

    t.Commit()
except Exception as ex:
    if t.HasStarted():
        t.RollBack()
    script.exit(str(ex))

# Report

output.print_md("#### There are {} openings (floor, wall, shaft, roof) in the project.".format(len(all_elements))) # TO DO Output link for all.
if data:
    output.print_table(table_data=data, title="Shafts:", columns=["Family" ,"ElementId", "Select/Show Element"])
    #output.print_md("#####Total {} WDB/WA elements has been updated.".format(len(data)))
else:
    output.print_md("#####There are no openings (floor, wall, shaft, roof) in the project")

# End
output.print_md('---')
output.print_md('#### Script has finished in {}s'.format(time.time() - timer_start))