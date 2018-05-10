import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB
from pyrevit.revit import query
from pyrevit.revit import create


logger = get_logger(__name__)


def ensure_sharedparam(sparam_name, sparam_categories, sparam_group,
                       load_param=True, doc=None):
    if query.model_has_sharedparam(sparam_name):
        return True
    elif load_param:
        create.create_shared_param(sparam_name,
                                   sparam_categories,
                                   sparam_group)
        return True


def ensure_sharedparam_file(spfilepath):
    if HOST_APP.app.SharedParametersFilename \
            and not op.normpath(
                HOST_APP.app.SharedParametersFilename
                ) == op.normpath(spfilepath):
        HOST_APP.app.SharedParametersFilename = spfilepath

    return HOST_APP.app.OpenSharedParameterFile()
