from pyrevit import revit, DB, script, forms

output = script.get_output()
output.close_others()

elements = revit.get_selection()

forms.alert_ifnot(len(elements) > 0, 'Please select at least one legend component.', title='Legend component orientation view setter', exitscript=True)

i = -8
orientation = 'Top view'

with revit.Transaction('Set Legend Component View to {}'.format(orientation), show_error_dialog=True):
    for element in elements:
        try:
            element_param = element.get_Parameter(DB.BuiltInParameter.LEGEND_COMPONENT_VIEW)
            element_param.Set(i)
        except:
            pass