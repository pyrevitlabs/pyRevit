__doc__ = 'Print the full path to the central model (if model is workshared).'


from pyrevit import DB, UI


doc = _R.doc


if doc.IsWorkshared:
    model_path = doc.GetWorksharingCentralModelPath()
    print(DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path))
else:
    UI.TaskDialog.Show('pyRevit', 'Model is not workshared.')
