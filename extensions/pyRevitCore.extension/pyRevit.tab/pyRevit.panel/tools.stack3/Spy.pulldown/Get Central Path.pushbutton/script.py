__doc__ = 'Print the full path to the central model (if model is workshared).'


from pyrevit import revit, DB, UI
from pyrevit import forms


if revit.doc.IsWorkshared:
    model_path = revit.doc.GetWorksharingCentralModelPath()
    print(DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path))
else:
    forms.alert(Model is not workshared.')
