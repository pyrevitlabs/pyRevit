__doc__ = 'Print the full path to the central model (if model is workshared).'


from pyrevit.revit import DB, UI


doc = __activedoc__


if doc.IsWorkshared:
    model_path = doc.GetWorksharingCentralModelPath()
    print(DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path))
else:
    UI.TaskDialog.Show('pyRevit', 'Model is not workshared.')
