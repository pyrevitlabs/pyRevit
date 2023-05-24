from pyrevit import script, revit, DB, forms

output = script.get_output()
output.close_others()

doc = revit.doc

view_templates = [v for v in DB.FilteredElementCollector(
    doc).OfClass(DB.View).ToElements() if v.IsTemplate]

selected_view_templates = forms.SelectFromList.show(
    sorted(view_templates, key=lambda template: template.Name), button_name='Select Template', multiselect=True, name_attr='Name')

params_dict = {}
if selected_view_templates:
    for template in selected_view_templates:
        for p in template.Parameters:
            if p.Definition.Name not in params_dict.keys():
                params_dict[p.Definition.Name] = p

    parameters_processed = forms.SelectFromList.show(sorted(params_dict.keys()), button_name='Select Parameters', multiselect=True)
    if parameters_processed:
        selected_params = [params_dict[p] for p in parameters_processed]
        params_ids = [p.Id for p in selected_params]
        inclusion = forms.CommandSwitchWindow.show(
            ['Include', 'Exclude'], message='Include or Exclude parameters from selected templates?')
        if inclusion:
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
else:
    script.exit()
