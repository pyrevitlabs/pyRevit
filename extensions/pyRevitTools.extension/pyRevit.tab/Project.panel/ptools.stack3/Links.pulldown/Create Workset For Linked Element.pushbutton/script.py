from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


__doc__ = 'This tool will create a workset for the selected linked '\
          'element base on its name. If the model is not workshared, '\
          'it will be converted to workshared model.'


logger = script.get_logger()

selection = revit.get_selection()


linkedModelName = ''

if len(selection) > 0:
    for el in selection:
        if isinstance(el, DB.RevitLinkInstance):
            linkedModelName = el.Name.split(':')[0]
        elif isinstance(el, DB.ImportInstance):
            linkedModelName = \
                el.Parameter[DB.BuiltInParameter.IMPORT_SYMBOL_NAME].AsString()
        if linkedModelName:
            if not revit.doc.IsWorkshared and revit.doc.CanEnableWorksharing:
                revit.doc.EnableWorksharing('Shared Levels and Grids',
                                            'Workset1')
            with revit.Transaction('Create Workset for linked model'):
                newWs = DB.Workset.Create(revit.doc, linkedModelName)
                worksetParam = \
                    el.Parameter[DB.BuiltInParameter.ELEM_PARTITION_PARAM]
                worksetParam.Set(newWs.Id.IntegerValue)
else:
    forms.alert('At least one linked element must be selected.')
