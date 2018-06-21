import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit import revit, DB
from pyrevit.revit import query
from pyrevit.revit import create


logger = get_logger(__name__)


def ensure_sharedparam(sparam_name, sparam_categories, sparam_group,
                       load_param=True, doc=None):
    doc = doc or HOST_APP.doc
    if query.model_has_sharedparam(sparam_name, doc=doc):
        return True
    elif load_param:
        create.create_shared_param(sparam_name,
                                   sparam_categories,
                                   sparam_group,
                                   doc=doc)
        return True


def ensure_sharedparam_file(spfilepath):
    if spfilepath and not HOST_APP.app.SharedParametersFilename:
        HOST_APP.app.SharedParametersFilename = spfilepath
    elif HOST_APP.app.SharedParametersFilename \
            and not op.normpath(
                HOST_APP.app.SharedParametersFilename
                ) == op.normpath(spfilepath):
        HOST_APP.app.SharedParametersFilename = spfilepath

    return HOST_APP.app.OpenSharedParameterFile()


def ensure_family(family_name, family_file, doc=None):
    doc = doc or HOST_APP.doc
    famsym = query.get_family(family_name, doc=doc)
    if not famsym:
        with revit.Transaction('Load Family', doc=doc):
            logger.debug('Family \"{}\" did not exist.'.format(family_name))
            if create.load_family(family_file, doc=doc):
                return query.get_family(family_name, doc=doc)
            else:
                raise PyRevitException('Error loading family from: {}'
                                       .format(family_file))
    return famsym


def ensure_element_ids(mixed_list):
    element_id_list = []

    if not isinstance(mixed_list, list):
        mixed_list = [mixed_list]

    for item in mixed_list:
        if isinstance(item, DB.ElementId):
            element_id_list.append(item)
        elif isinstance(item, DB.Element):
            element_id_list.append(item.Id)
        elif type(item) == int:
            element_id_list.append(DB.ElementId(item))

    return element_id_list
