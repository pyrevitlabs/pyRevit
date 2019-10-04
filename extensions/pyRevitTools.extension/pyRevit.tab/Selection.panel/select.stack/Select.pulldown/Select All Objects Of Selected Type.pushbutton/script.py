"""Select all elements of the same type as selected element
and reports their IDs (sorted by the owner view if they
are View Specific objects)

Shift-Click:
Show Results
"""
#pylint: disable=import-error,invalid-name,unused-argument,broad-except,superfluous-parens
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


__context__ = 'selection'

output = script.get_output()
selection = revit.get_selection()


filered_elements = []
model_items = []
viewspecific_items = {}

# verify selection
if not selection:
    forms.alert('At least one object must be selected.', exitscript=True)

# collect element matching selected input
for selected_element in selection:
    is_viewspecific = selected_element.ViewSpecific

    # find type id
    if isinstance(selected_element, DB.CurveElement):
        type_id = selected_element.LineStyle.Id
    else:
        type_id = selected_element.GetTypeId()

    # determine by class or by category
    by_class = category_id = None
    if isinstance(selected_element, DB.Dimension):
        by_class = DB.Dimension
    else:
        category_id = selected_element.Category.Id

    # collect all target elements
    if by_class:
        same_cat_elements = \
            DB.FilteredElementCollector(revit.doc)\
            .OfClass(by_class)\
            .WhereElementIsNotElementType()\
            .ToElements()
    else:
        same_cat_elements = \
            DB.FilteredElementCollector(revit.doc)\
            .OfCategoryId(category_id)\
            .WhereElementIsNotElementType()\
            .ToElements()

    # find matching types
    for sim_element in same_cat_elements:
        if isinstance(sim_element, DB.CurveElement):
            r_type = sim_element.LineStyle.Id
        else:
            r_type = sim_element.GetTypeId()
        if r_type == type_id:
            filered_elements.append(sim_element.Id)
            if is_viewspecific:
                ovname = \
                    revit.query.get_name(
                        revit.doc.GetElement(sim_element.OwnerViewId)
                        )
                if ovname in viewspecific_items:
                    viewspecific_items[ovname].append(sim_element)
                else:
                    viewspecific_items[ovname] = [sim_element]
            else:
                model_items.append(sim_element)

# print results if requested
if __shiftclick__:  #pylint: disable=undefined-variable
    if is_viewspecific:
        for ovname, items in viewspecific_items.items():
            print('OWNER VIEW: {0}'.format(ovname))
            for vs_element in items:
                print('\tID: {0}\t{1}'.format(
                    output.linkify(vs_element.Id),
                    vs_element.GetType().Name.ljust(20)
                    ))
            print('\n')
    else:
        print('SELECTING MODEL ITEMS:')
        for model_element in model_items:
            print('\tID: {0}\t{1}'.format(
                output.linkify(model_element.Id),
                model_element.GetType().Name.ljust(20)
                ))

# select results
revit.get_selection().set_to(filered_elements)
