from pyrevit import forms
from pyrevit import revit, DB

__doc__ = 'Deletes all unused view templates '\
          '(Any view template that has not been assigned to a view).'


class ViewTemplateToPurge:
    def __init__(self, template_elid):
        self.state = False
        self.template_el = revit.doc.GetElement(DB.ElementId(template_elid))
        self.name = self.template_el.Name


viewlist = DB.FilteredElementCollector(revit.doc)\
             .OfCategory(DB.BuiltInCategory.OST_Views)\
             .WhereElementIsNotElementType()\
             .ToElements()


vtemp = set()
usedvtemp = set()
views = []

for v in viewlist:
    if v.IsTemplate and 'master' not in v.ViewName.lower():
        vtemp.add(v.Id.IntegerValue)
    else:
        views.append(v)

for v in views:
    vtid = v.ViewTemplateId.IntegerValue
    if vtid > 0:
        usedvtemp.add(vtid)

unusedvtemp = vtemp - usedvtemp


if unusedvtemp:
    # ask user for wipe actions
    return_options = \
        forms.SelectFromList.show(
            [ViewTemplateToPurge(x) for x in unusedvtemp],
            title='Select View Templates to Purge',
            width=500,
            button_name='Purge View Templates',
            multiselect=True
            )

    if return_options:
        with revit.Transaction('Purge Unused View Templates'):
            for vtp in return_options:
                if vtp.state:
                    print('Purging View Template: {0}\t{1}'
                          .format(vtp.template_el.Id, vtp.name))
                    revit.doc.Delete(vtp.template_el.Id)
