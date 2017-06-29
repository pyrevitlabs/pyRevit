__doc__ = 'Print the full path to the central model (if model is workshared).'


from rpw import doc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ModelPathUtils
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog

if doc.IsWorkshared:
    model_path = doc.GetWorksharingCentralModelPath()
    print(ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path))
else:
    TaskDialog.Show('pyrevit', 'Model is not workshared.')
