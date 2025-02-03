from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.compat import get_elementid_value_func


class ViewTemplateToPurge(forms.TemplateListItem):
    @property
    def name(self):
        return self.item.Name


viewlist = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.View)\
             .WhereElementIsNotElementType()\
             .ToElements()


vtemp = set()
usedvtemp = set()
views = []

for v in viewlist:
    if v.IsTemplate and 'master' not in revit.query.get_name(v).lower():
        get_elementid_value = get_elementid_value_func()
        vtemp.add(get_elementid_value(v.Id))
    else:
        views.append(v)

for v in views:
    get_elementid_value = get_elementid_value_func()
    vtid = get_elementid_value(v.ViewTemplateId)
    if vtid > 0:
        usedvtemp.add(vtid)

unusedvtemp = vtemp - usedvtemp


if not unusedvtemp:
    forms.alert('All View Templates are in use. No purging in necessary.')
else:
    # ask user for wipe actions
    return_options = \
        forms.SelectFromList.show(
            [ViewTemplateToPurge(revit.doc.GetElement(DB.ElementId(x)))
             for x in unusedvtemp],
            title='Select View Templates to Purge',
            width=500,
            button_name='Purge View Templates',
            multiselect=True
            )

    if return_options:
        with revit.Transaction('Purge Unused View Templates'):
            for vtp in return_options:
                print('Purging View Template: {0}\t{1}'
                        .format(vtp.Id, vtp.Name))
                revit.doc.Delete(vtp.Id)
