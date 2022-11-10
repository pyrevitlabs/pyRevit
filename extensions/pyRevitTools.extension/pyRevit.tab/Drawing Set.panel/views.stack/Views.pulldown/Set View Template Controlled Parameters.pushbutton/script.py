from pyrevit import script, revit, DB, forms

output = script.get_output()
output.close_others()

doc = revit.doc

templates = [v for v in DB.FilteredElementCollector(
    doc).OfClass(DB.View).ToElements() if v.IsTemplate]

view_templates, view_templates_names = [], []
for template in templates:
    if str(template.ViewType) != 'ThreeD':
        view_templates.append(template)

params_names, params = [], []
for template in view_templates:
    for p in template.Parameters:
        if p.Definition.Name not in params_names:
            params.append(p)
            params_names.append(p.Definition.Name)

selected_view_templates = forms.SelectFromList.show(
    view_templates, button_name='Select Template', multiselect=True, name_attr='Name')

parameters_processed = forms.SelectFromList.show(
    params_names, button_name='Select Parameters', multiselect=True)
for param in params:
    if param.Definition.Name not in parameters_processed:
        params.remove(param)
params_ids = [p.Id for p in params]

inclusion = forms.CommandSwitchWindow.show(
    ['Include', 'Exclude'], message='Include or Exclude parameters from selected templates?')
if inclusion == 'Include':
    include = False
else:
    include = True

with revit.Transaction('set params in view templates'):
    results = []
    for template in selected_view_templates:
        all_params = template.GetTemplateParameterIds()
        switch_off_param_ids = params_ids

        non_controlled_param_ids = template.GetNonControlledTemplateParameterIds()
        for switch_off_param_id in switch_off_param_ids:
            if include:
                non_controlled_param_ids.Add(switch_off_param_id)
            else:
                non_controlled_param_ids.Remove(switch_off_param_id)

        template.SetNonControlledTemplateParameterIds(non_controlled_param_ids)
        results.append(template)