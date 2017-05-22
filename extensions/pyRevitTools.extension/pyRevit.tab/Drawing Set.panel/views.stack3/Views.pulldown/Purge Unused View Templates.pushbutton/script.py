"""Deletes all unused view templates (Any view template that has not been assigned to a view)."""

from scriptutils.userinput import SelectFromCheckBoxes
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory, ElementId
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
viewlist = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

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
    class ViewTemplateToPurge:
        def __init__(self, template_elid):
            self.state = False
            self.template_el = doc.GetElement(ElementId(template_elid))
            self.name = self.template_el.Name

    return_options = SelectFromCheckBoxes.show([ViewTemplateToPurge(x) for x in unusedvtemp],
                                               title='Select View Templates to Purge', width=500, button_name='Purge View Templates')


    if return_options:
        t = Transaction(doc, 'Purge Unused View Templates')
        t.Start()

        for vtp in return_options:
            if vtp.state:
                print('Purging View Template: {0}\t{1}'.format(vtp.template_el.Id, vtp.name))
                doc.Delete(vtp.template_el.Id)

        # res = TaskDialog.Show('pyrevit',
        #                       'Are you sure you want to remove these view templates?',
        #                       TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.Cancel)

        # if res == TaskDialogResult.Yes:
        #     for v in unusedvtemp:
        #         doc.Delete(ElementId(v))
        # else:
        #     print('----------- Purge Cancelled --------------')

        t.Commit()
