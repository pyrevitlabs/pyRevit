#pylint: disable=import-error,invalid-name,unused-argument,broad-except
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


__context__ = 'selection'
__doc__ = 'Select all elements of the same type as selected element '\
          'and reports their IDs (sorted by the owner view if they '\
          'are View Specific objects)'


output = script.get_output()

selection = revit.get_selection()

if selection:
    first_element = selection.first
    is_viewspecific = first_element.ViewSpecific
    category_id = first_element.Category.Id
    if isinstance(first_element, DB.CurveElement):
        type_id = first_element.LineStyle.Id
    else:
        type_id = first_element.GetTypeId()

    same_cat_elements = \
        DB.FilteredElementCollector(revit.doc)\
          .OfCategoryId(category_id)\
          .WhereElementIsNotElementType()\
          .ToElements()

    filered_elements = []
    model_items = []
    viewspecific_items = {}

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

    revit.get_selection().set_to(filered_elements)
else:
    forms.alert('At least one object must be selected.')
