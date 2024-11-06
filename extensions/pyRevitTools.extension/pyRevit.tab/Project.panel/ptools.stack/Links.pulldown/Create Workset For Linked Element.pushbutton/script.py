from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms
from pyrevit.compat import get_elementid_value_func

logger = script.get_logger()

selection = revit.get_selection()

get_elementid_value = get_elementid_value_func()

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
                try:
                    newWs = DB.Workset.Create(revit.doc, linkedModelName)
                    worksetParam = \
                        el.Parameter[DB.BuiltInParameter.ELEM_PARTITION_PARAM]
                    worksetParam.Set(get_elementid_value(newWs.Id))
                except Exception as e:
                    print('Workset: {} already exists\nError: {}'.format(linkedModelName,e))
else:
    forms.alert('At least one linked element must be selected.')
