import os
import os.path as op

from pyrevit import PYREVIT_ADDON_NAME
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader import LOADER_ADDON_NAMESPACE
from pyrevit.loader.basetypes import ADDIN_DIR


logger = get_logger(__name__)


ADDIN_DEF_FILENAME = PYREVIT_ADDON_NAME + '.addin'
ADDIN_GUID = "B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D"
ADDIN_CLASSNAME = LOADER_ADDON_NAMESPACE + 'Application'
ADDIN_VENDORID = 'eirannejad'


addinfile_contents =                                                                         \
'<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'                                  \
 '<RevitAddIns>\n'                                                                          \
 '  <AddIn Type="Application">\n'                                                           \
 '    <Name>{addinname}</Name>\n'                                                           \
 '    <Assembly>{addinfolder}\\{addinname}.dll</Assembly>\n'                                \
 '    <AddInId>{addinguid}</AddInId>\n'                                                     \
 '    <FullClassName>{addinname}.{addinclassname}</FullClassName>\n'                             \
 '  <VendorId>{addinvendorid}</VendorId>\n'                                                      \
 '  </AddIn>\n'                                                                             \
 '</RevitAddIns>\n'


def _find_revit_addin_directory():
    return op.join(os.getenv('appdata'), "Autodesk", "Revit", "Addins")


def _get_installed_revit_addin_folders():
    revit_addin_dir = _find_revit_addin_directory()
    return {x:op.join(revit_addin_dir, x) for x in os.listdir(revit_addin_dir)}


def _addin_def_exists(revit_version):
    revit_addin_dir = _find_revit_addin_directory()
    for fname in os.listdir(op.join(revit_addin_dir, revit_version)):
        if fname.lower().endswith('addin'):
            fullfname = op.join(revit_addin_dir, revit_version, fname)
            with open(fullfname, 'r') as f:
                for line in f.readlines():
                    if (LOADER_ADDON_NAMESPACE + '.dll').lower() in line.lower():
                        return True
    return False


def _set_addin_state_for(revit_version, addin_state):
    for installed_revit_version, revit_addin_dir in _get_installed_revit_addin_folders().items():
        if installed_revit_version in revit_version:
            if _addin_def_exists(installed_revit_version):
                os.remove(op.join(revit_addin_dir, ADDIN_DEF_FILENAME))

            if addin_state:
                addinfile = op.join(revit_addin_dir, ADDIN_DEF_FILENAME)
                with open(addinfile, 'w') as f:
                    f.writelines(addinfile_contents.format(addinname = LOADER_ADDON_NAMESPACE,
                                                           addinfolder = ADDIN_DIR,
                                                           addinguid = ADDIN_GUID,
                                                           addinvendorid = ADDIN_VENDORID,
                                                           addinclassname = ADDIN_CLASSNAME))

def get_addinfiles_state():
    addinfiles_state_dict = {}
    for revit_version in _get_installed_revit_addin_folders().keys():
        addinfiles_state_dict[revit_version] = _addin_def_exists(revit_version)

    return addinfiles_state_dict

def set_addinfiles_state(states_dict):
    for revit_version, addin_state in states_dict.items():
        _set_addin_state_for(revit_version, addin_state)
