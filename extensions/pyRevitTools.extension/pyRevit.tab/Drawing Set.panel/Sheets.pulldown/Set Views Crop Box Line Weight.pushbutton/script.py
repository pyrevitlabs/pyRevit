from pyrevit import revit, DB, forms, script

output = script.get_output()
output.close_others()

doc = revit.doc

views = DB.FilteredElementCollector(doc).OfCategory(
    DB.BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
views_on_sheet = []
for v in views:
    try:
        if v.get_Parameter(DB.BuiltInParameter.VIEWER_SHEET_NUMBER).AsString() != '':
            views_on_sheet.append(v)
    except:
        pass
selected_views = forms.SelectFromList.show(
    views_on_sheet, button_name='Select Views', multiselect=True, name_attr='Name')

lineweights = range(1, 17, 1)
selected_lineweight = forms.SelectFromList.show(
    lineweights, button_name='Select Lineweight', multiselect=False, height=475)

if selected_lineweight and selected_views:
    override = DB.OverrideGraphicSettings().SetProjectionLineWeight(selected_lineweight)
    with revit.TransactionGroup('Set Viewport Lineweight'):
        for view in selected_views:
            with revit.Transaction('TEMP crop box to false'):
                view.CropBoxVisible = False
            collector = DB.FilteredElementCollector(doc, view.Id)
            shownElems = collector.ToElementIds()
            with revit.Transaction('TEMP crop box to true'):
                view.CropBoxVisible = True
            collector = DB.FilteredElementCollector(doc, view.Id)
            collector.Excluding(shownElems)
            cropBoxElement = collector.FirstElement()
            if cropBoxElement:
                with revit.Transaction('Set Viewport Lineweight'):
                    view.SetElementOverrides(cropBoxElement.Id, override)
else:
    script.exit()
