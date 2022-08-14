# -*- coding: utf-8 -*-
from pyrevit import revit, script, DB, forms

doc = revit.doc

# takes care of closing previous output windows
output = script.get_output()
output.close_others()

arrowhead_types, arrowhead_types_names, deleted, not_deleted = [], [], '',''

# collect arrowhead types
element_types = DB.FilteredElementCollector(doc).OfClass(DB.ElementType).WhereElementIsElementType()

for element_type in element_types:
    # check if element type is arrowhead
    if element_type.get_Parameter(DB.BuiltInParameter.ARROW_CLOSED) and element_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString()!='':
        # collect arrowhead types and arrowhead types names separately
        arrowhead_types_names.append(element_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString())
        arrowhead_types.append(element_type)

# The selection form
selection = forms.SelectFromList.show(arrowhead_types_names, 'Select arrowhead types you wand to delete', multiselect = True, infopanel = 'Select arrowhead type you wish to delete')

# checking if there is a selection
if selection:
    with revit.Transaction('Delete Arrowheads'):
        # get arrowhead_type from arrowhead_types_names selected
        for e_name, e_type in zip(arrowhead_types_names, arrowhead_types):
            if e_name in selection:
                try: 
                    # delete arrowhead_type
                    doc.Delete(e_type.Id)
                    deleted = deleted + '- ' + e_name + '\n'
                except:
                    # not deleted - BECASUE YOU CANNOT DELETE ALL OF THEM
                    not_deleted = not_deleted + '- ' + e_name + '\n'
    # show results
    output.set_width(200)
    output.print_md('#Deleted arrowheads: \n{}\n'.format(deleted))
    output.print_md('#Not deleted arrowheads: \n{}\n'.format(not_deleted))
else:
    script.exit()