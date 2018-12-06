from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


__doc__ = 'This script removes all custom parameters that has not been used '\
          'in dimensions as labels and also resets the value for the other ' \
          'parameters to zero or null.'


logger = script.get_logger()

res = \
    forms.alert('Make sure your models are saved and synced. '
                'Hit OK to continue...', cancel=True, exitscript=True)

if revit.doc.IsFamilyDocument:
    params = revit.doc.FamilyManager.GetParameters()
    dims = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.Dimension)\
             .WhereElementIsNotElementType()

    allelements = DB.FilteredElementCollector(revit.doc)\
                    .WhereElementIsNotElementType()

    labelParams = set()
    for d in dims:
        try:
            if isinstance(d.FamilyLabel, DB.FamilyParameter):
                labelParams.add(d.FamilyLabel.Id.IntegerValue)
        except Exception:
            continue

    visibParams = set()
    for el in allelements:
        try:
            visible_param = el.Parameter[DB.BuiltInParameter.IS_VISIBLE_PARAM]
            if visible_param is not None:
                famvisibparam = \
                    revit.doc.FamilyManager.GetAssociatedFamilyParameter(
                        visible_param
                        )

                if famvisibparam is not None \
                        and isinstance(famvisibparam, DB.FamilyParameter):
                    visibParams.add(famvisibparam.Id.IntegerValue)
        except Exception:
            continue

    print('STARTING CLEANUP...')

    with revit.Transaction('Remove all family parameters'):
        for param in params:
            try:
                print('\nREMOVING FAMILY PARAMETER:\nID: {0}\tNAME: {1}'
                      .format(param.Id, param.Definition.Name))
                if param.Id.IntegerValue not in labelParams \
                        and param.Id.IntegerValue not in visibParams:
                    revit.doc.FamilyManager.RemoveParameter(param)
                    print('REMOVED.')
                else:
                    print('NOT REMOVED. PARAMETER IS BEING USED AS A LABEL.')
            except Exception:
                print('-- CAN NOT DELETE --')
                try:
                    if param.CanAssignFormula:
                        revit.doc.FamilyManager.SetFormula(param, None)
                    if param.StorageType == DB.StorageType.Integer \
                            or param.StorageType == DB.StorageType.Double:
                        revit.doc.FamilyManager.Set(param, 0)
                        print('-- PARAMETER VALUE SET TO INTEGER 0')
                    elif param.StorageType == DB.StorageType.String:
                        revit.doc.FamilyManager.Set(param, '')
                        print('-- PARAMETER VALUE SET TO EMPTY STRING.')
                    else:
                        print('-- PARAMETER TYPE IS UNKNOWN. '
                              'CAN NOT RESET VALUE.')
                except Exception as e:
                    logger.error(e)
                    continue
                continue

    print('\n\nALL DONE.....................................')
else:
    forms.alert('This script works only on an active family editor.')
