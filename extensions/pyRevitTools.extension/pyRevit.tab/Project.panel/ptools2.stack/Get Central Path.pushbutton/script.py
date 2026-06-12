"""Print the full path to the central model (workshared) or the local model path.

Shift+Click:
    Open model file in Explorer, or open ACC Docs project page for cloud models.
"""
#pylint: disable=E0401,invalid-name
from pyrevit import revit, DB, HOST_APP, EXEC_PARAMS
from pyrevit import forms
from pyrevit import script


def _is_cloud_path(model_path):
    return bool(getattr(model_path, "CloudPath", None))


def _get_acc_url(model_path):
    if HOST_APP.is_newer_than(2026):
        regions = list(DB.ModelPathUtils.GetAllCloudRegions())
        emea = next((r for r in regions if "EMEA" in str(r)), None)
        is_emea = emea is not None and model_path.Region == emea
    else:
        is_emea = model_path.Region == DB.ModelPathUtils.CloudRegionEMEA
    domain = "eu" if is_emea else "com"
    project_id = str(model_path.GetProjectGUID()).lower()
    return "https://acc.autodesk.{}/docs/files/projects/{}".format(domain, project_id)


doc = revit.doc

if doc.IsWorkshared:
    model_path = doc.GetWorksharingCentralModelPath()
    path_str = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path)
else:
    model_path = None
    path_str = doc.PathName

if not path_str:
    forms.alert("Project has not been saved.", warn_icon=True)
    script.exit()

if EXEC_PARAMS.config_mode:
    if model_path and _is_cloud_path(model_path):
        script.open_url(_get_acc_url(model_path))
    else:
        script.show_file_in_explorer(path_str)
else:
    print(path_str)
