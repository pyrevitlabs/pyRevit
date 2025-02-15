# -*- coding: utf-8 -*-

"""Lists all openings in the project and creates 
a selection filter for them."""

# Sytem
import time

# pyRevit
from pyrevit import revit, script, DB
from pyrevit.framework import List
doc         =__revit__.ActiveUIDocument.Document
uidoc       =__revit__.ActiveUIDocument
output      = script.get_output()
selection   = uidoc.Selection
timer_start = time.time()

# GET ALL OPENINGS IN THE PROJECT

# List of categories
cats = [DB.BuiltInCategory.OST_FloorOpening,
        DB.BuiltInCategory.OST_SWallRectOpening,
        DB.BuiltInCategory.OST_ShaftOpening,
        DB.BuiltInCategory.OST_RoofOpening]
list_cats = List[DB.BuiltInCategory](cats)

# Create filter
multi_cat_filter = DB.ElementMulticategoryFilter(list_cats)

# Apply filter to filteredElementCollector
all_elements = DB.FilteredElementCollector(doc)\
                .WherePasses(multi_cat_filter)\
                .WhereElementIsNotElementType()\
                .ToElements()

# Get elements for selection filter
element_ids = DB.FilteredElementCollector(doc).OfClass(DB.Opening).ToElementIds()
element_ids = List[DB.ElementId](element_ids)

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
all_sel_filters  = DB.FilteredElementCollector(doc).OfClass(DB.SelectionFilterElement).ToElements()
dict_sel_filters = {f.Name: f for f in all_sel_filters}

# Transaction to create a new selection filter
with revit.Transaction('Create Openings Filter'):
    new_filter_name = '0_ShaftOpenings'
    if new_filter_name not in dict_sel_filters:
        new_fil = DB.SelectionFilterElement.Create(doc, new_filter_name)
        new_fil.AddSet(element_ids)
        print ('Created a filter called : {}'.format(new_filter_name))
    else:
        existing_fil = dict_sel_filters[new_filter_name]
        existing_fil.AddSet(element_ids)
        print ('Updated a filter called : {}'.format(new_filter_name))

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