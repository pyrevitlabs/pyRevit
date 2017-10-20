from pyrevit import HOST_APP
from pyrevit.revit.api import DB, UI


def get_all_docs():
    return HOST_APP.uiapp.Application.Documents
