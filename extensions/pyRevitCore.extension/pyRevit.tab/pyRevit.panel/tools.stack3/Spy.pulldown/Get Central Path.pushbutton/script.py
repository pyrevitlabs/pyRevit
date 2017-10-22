__doc__ = 'Print the full path to the central model (if model is workshared).'


from pyrevit import revit, DB, UI


if revit.doc.IsWorkshared:
    model_path = revit.doc.GetWorksharingCentralModelPath()
    print(DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path))
else:
    UI.TaskDialog.Show('pyRevit', 'Model is not workshared.')
