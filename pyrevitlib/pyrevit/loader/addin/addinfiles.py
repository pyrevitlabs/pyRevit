import os
import os.path as op

from pyrevit import PYREVIT_ADDON_NAME, HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader import LOADER_ADDON_NAMESPACE
from pyrevit.loader.basetypes import ADDIN_DIR


logger = get_logger(__name__)


ADDIN_DEF_FILENAME = PYREVIT_ADDON_NAME + '.addin'
ADDIN_GUID = "B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D"
ADDIN_CLASSNAME = LOADER_ADDON_NAMESPACE + 'Application'
ADDIN_VENDORID = 'eirannejad'


addinfile_contents = \
    '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'            \
    '<RevitAddIns>\n'                                                     \
    '  <AddIn Type="Application">\n'                                      \
    '    <Name>{addinname}</Name>\n'                                      \
    '    <Assembly>{addinfolder}\\{addinname}.dll</Assembly>\n'           \
    '    <AddInId>{addinguid}</AddInId>\n'                                \
    '    <FullClassName>{addinname}.{addinclassname}</FullClassName>\n'   \
    '  <VendorId>{addinvendorid}</VendorId>\n'                            \
    '  </AddIn>\n'                                                        \
    '</RevitAddIns>\n'


def _find_revit_addin_directory(program_data=False):
    base_dirname = 'programdata' if program_data else 'appdata'
    logger.debug('Finding base addins path under %{}%'.format(base_dirname))

    addins_dir = op.join(os.getenv(base_dirname),
                         "Autodesk", "Revit", "Addins")

    if op.isdir(addins_dir):
        logger.debug('Revit base addin dir: {}'.format(addins_dir))
        return addins_dir
    else:
        return None


def _get_installed_revit_addin_dirs(program_data=False):
    addins_base_dir = _find_revit_addin_directory(program_data)
    if addins_base_dir:
        addindict = {x: op.join(addins_base_dir, x)
                     for x in os.listdir(addins_base_dir)}
        logger.debug('Installed Revits: {}'.format(addindict))
        return addindict
    else:
        logger.debug('Can not find installed revits under {}'
                     .format('%programdata%' if program_data else '%appdata%'))
        return {}


def _addin_def_exists(revit_addin_dir):
    logger.debug('Looking for manifest file in: {}'.format(revit_addin_dir))
    for fname in os.listdir(revit_addin_dir):
        if fname.lower().endswith('addin'):
            fullfname = op.join(revit_addin_dir, fname)
            try:
                with open(fullfname, 'r') as f:
                    for line in f.readlines():
                        if (LOADER_ADDON_NAMESPACE + '.dll').lower() \
                                in line.lower():
                            logger.debug('Addin file exists for pyRevit: {}'
                                         .format(fullfname))
                            return fullfname
            except Exception as read_err:
                logger.debug('Error reading {} | {}'
                             .format(fullfname, read_err))

    return False


def _set_addin_state_for(revit_version, addin_state, program_data=False):
    installed_revits_dict = _get_installed_revit_addin_dirs(program_data)
    if revit_version in installed_revits_dict:
        revit_addin_dir = installed_revits_dict[revit_version]
        existing_addin_file = _addin_def_exists(revit_addin_dir)
        if existing_addin_file:
            try:
                os.remove(existing_addin_file)
                logger.debug('Disabled: {}'.format(existing_addin_file))
            except Exception as del_err:
                logger.debug('Error removing {} | {}'
                             .format(existing_addin_file, del_err))

        if addin_state:
            new_addin_file = op.join(revit_addin_dir, ADDIN_DEF_FILENAME)
            try:
                with open(new_addin_file, 'w') as f:
                    f.writelines(
                        addinfile_contents.format(
                            addinname=LOADER_ADDON_NAMESPACE,
                            addinfolder=ADDIN_DIR,
                            addinguid=ADDIN_GUID,
                            addinvendorid=ADDIN_VENDORID,
                            addinclassname=ADDIN_CLASSNAME
                        )
                    )
                    logger.debug('Enabled: {}'.format(existing_addin_file))
            except Exception as write_err:
                logger.debug('Error writing {} | {}'
                             .format(existing_addin_file, write_err))


def get_addinfiles_state(allusers=False):
    logger.debug('Getting addin manifest file states')
    addinfiles_state_dict = {}
    installed_revits_dict = _get_installed_revit_addin_dirs(allusers)
    for revit_version, revit_addin_dir in installed_revits_dict.items():
        addinfiles_state_dict[revit_version] = \
            _addin_def_exists(revit_addin_dir)

    return addinfiles_state_dict


def set_addinfiles_state(states_dict, allusers=False):
    logger.debug('Setting addin manifest file states')
    for revit_version, addin_state in states_dict.items():
        _set_addin_state_for(revit_version, addin_state, allusers)


def get_revit_addin_dir(revit_version, allusers=False):
    revit_addin_dir = _find_revit_addin_directory(allusers)
    if revit_addin_dir:
        addin_path = op.join(revit_addin_dir, revit_version)
        if op.isdir(addin_path):
            logger.debug('Revit addin path: {}'.format(addin_path))
            return addin_path


def find_programdata_manifest():
    logger.debug('Looking for addin manifest file in %programdata%')
    pdata_addin_dir = get_revit_addin_dir(HOST_APP.version, allusers=True)
    if pdata_addin_dir:
        pyrvt_pdata_addin = op.join(pdata_addin_dir, ADDIN_DEF_FILENAME)
        if op.isfile(pyrvt_pdata_addin):
            logger.debug('Found: {}'.format(pyrvt_pdata_addin))
            return pyrvt_pdata_addin


def find_appdata_manifest():
    logger.debug('Looking for addin manifest file in %appdata%')
    appdata_addin_dir = get_revit_addin_dir(HOST_APP.version, allusers=False)
    if appdata_addin_dir:
        pyrvt_appdata_addin = op.join(appdata_addin_dir, ADDIN_DEF_FILENAME)
        if op.isfile(pyrvt_appdata_addin):
            logger.debug('Found: {}'.format(pyrvt_appdata_addin))
            return pyrvt_appdata_addin


def get_current_pyrevit_addin():
    return find_programdata_manifest() or find_appdata_manifest()


def is_pyrevit_for_allusers():
    allusers = find_programdata_manifest() is not None
    logger.debug('Is pyRevit installed for All users? {}'.format(allusers))
    return allusers
