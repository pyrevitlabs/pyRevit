import sys
import clr
from Autodesk.Revit.DB import Transaction, ElementId, StorageType, FilteredElementCollector, Dimension, FamilyParameter
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__doc__ = 'This script removes all custom parameters that has not been used '\
          'in dimensions as labels and also resets the value for the other ' \
          'parameters to zero or null.'

res = TaskDialog.Show('pyRevit',
                      'Make sure your models are saved and synced. '
                      'Hit OK to continue...',
                      TaskDialogCommonButtons.Ok | TaskDialogCommonButtons.Cancel)

if not res == TaskDialogResult.Ok:
    sys.exit()

if doc.IsFamilyDocument:
    params = doc.FamilyManager.GetParameters()
    dims = FilteredElementCollector(doc).OfClass(Dimension).WhereElementIsNotElementType()
    allelements = FilteredElementCollector(doc).WhereElementIsNotElementType()

    labelParams = set()
    for d in dims:
        try:
            if isinstance(d.FamilyLabel, FamilyParameter):
                labelParams.add(d.FamilyLabel.Id.IntegerValue)
        except:
            continue

    visibParams = set()
    for el in allelements:
        try:
            visibparam = el.LookupParameter('Visible')
            if visibparam is not None:
                famvisibparam = doc.FamilyManager.GetAssociatedFamilyParameter(visibparam)
                if famvisibparam is not None and isinstance(famvisibparam, FamilyParameter):
                    visibParams.add(famvisibparam.Id.IntegerValue)
        except:
            continue

    print('STARTING CLEANUP...')
    t = Transaction(doc, 'Remove all family parameters')
    t.Start()

    for param in params:
        try:
            print('\nREMOVING FAMILY PARAMETER:\nID: {0}\tNAME: {1}'.format(param.Id, param.Definition.Name))
            if param.Id.IntegerValue not in labelParams and param.Id.IntegerValue not in visibParams:
                doc.FamilyManager.RemoveParameter(param)
                print('REMOVED.')
            else:
                print('NOT REMOVED. PARAMETER IS BEING USED AS A LABEL.')
        except:
            print('-- CAN NOT DELETE --')
            try:
                if param.CanAssignFormula:
                    doc.FamilyManager.SetFormula(param, None)
                if param.StorageType == StorageType.Integer or param.StorageType == StorageType.Double:
                    doc.FamilyManager.Set(param, 0)
                    print('-- PARAMETER VALUE SET TO INTEGER 0')
                elif param.StorageType == StorageType.String:
                    doc.FamilyManager.Set(param, '')
                    print('-- PARAMETER VALUE SET TO EMPTY STRING.')
                else:
                    print('-- PARAMETER TYPE IS UNKNOWN. CAN NOT RESET VALUE.')
            except Exception as e:
                print e
                continue
            continue
    print('\n\nALL DONE.....................................')
    t.Commit()
else:
    __window__.Close()
    TaskDialog.Show('pyrevit', 'This script works only on an active family editor.')
