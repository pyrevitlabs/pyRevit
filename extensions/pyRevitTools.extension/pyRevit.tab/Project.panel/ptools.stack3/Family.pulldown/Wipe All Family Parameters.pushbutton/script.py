#pylint: disable=E0401
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


__doc__ = 'This script removes all custom parameters that has not been used '\
          'in dimensions as labels and also resets the value for the other ' \
          'parameters to zero or null.'

logger = script.get_logger()

res = \
    forms.alert('Make sure your models are saved and synced. '
                'Hit OK to continue...', cancel=True)

if revit.doc.IsFamilyDocument:
    params = revit.doc.FamilyManager.GetParameters()
    dims = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.Dimension)\
             .WhereElementIsNotElementType()

    labelParams = set()
    for d in dims:
        try:
            if isinstance(d.FamilyLabel, DB.FamilyParameter):
                labelParams.add(d.FamilyLabel.Id.IntegerValue)
        except Exception:
            continue

    print('STARTING CLEANUP...')

    with revit.Transaction('Remove all family parameters'):
        for param in params:
            try:
                print('\nREMOVING FAMILY PARAMETER:\nID: {0}\tNAME: {1}'
                      .format(param.Id, param.Definition.Name))
                revit.doc.FamilyManager.RemoveParameter(param)
                print('REMOVED.')
            except Exception:
                print('-- CAN NOT DELETE --')
                if param.Id.IntegerValue not in labelParams:
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
                else:
                    print('PARAMETER IS BEING USED AS A LABEL. '
                          'PARAMETER VALUE WON\'T BE RESET')
                continue
    print('\n\nALL DONE.....................................')
else:
    forms.alert('This script works only on an active family editor.')
