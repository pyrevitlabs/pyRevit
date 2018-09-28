import os
import os.path as op

from pyrevit.labs import TargetApps
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


def get_addinfiles_state(allusers=False):
    mlogger.debug('Getting addin manifest file states')
    addinfiles_state_dict = {}
    installed_revits_dict = _get_installed_revit_addin_dirs(allusers)
    for revit_version, revit_addin_dir in installed_revits_dict.items():
        addinfiles_state_dict[revit_version] = \
            _addin_def_exists(revit_addin_dir)

    return addinfiles_state_dict


def set_addinfiles_state(states_dict, allusers=False):
    mlogger.debug('Setting addin manifest file states')
    for revit_version, addin_state in states_dict.items():
        _set_addin_state_for(revit_version, addin_state, allusers)


def get_revit_addin_dir(revit_version, allusers=False):
    revit_addin_dir = _find_revit_addin_directory(allusers)
    if revit_addin_dir:
        addin_path = op.join(revit_addin_dir, revit_version)
        if op.isdir(addin_path):
            mlogger.debug('Revit addin path: {}'.format(addin_path))
            return addin_path


def find_programdata_manifest():
    mlogger.debug('Looking for addin manifest file in %programdata%')
    pdata_addin_dir = get_revit_addin_dir(HOST_APP.version, allusers=True)
    if pdata_addin_dir:
        pyrvt_pdata_addin = op.join(pdata_addin_dir, ADDIN_DEF_FILENAME)
        if op.isfile(pyrvt_pdata_addin):
            mlogger.debug('Found: {}'.format(pyrvt_pdata_addin))
            return pyrvt_pdata_addin


def find_appdata_manifest():
    mlogger.debug('Looking for addin manifest file in %appdata%')
    appdata_addin_dir = get_revit_addin_dir(HOST_APP.version, allusers=False)
    if appdata_addin_dir:
        pyrvt_appdata_addin = op.join(appdata_addin_dir, ADDIN_DEF_FILENAME)
        if op.isfile(pyrvt_appdata_addin):
            mlogger.debug('Found: {}'.format(pyrvt_appdata_addin))
            return pyrvt_appdata_addin


def get_current_pyrevit_addin():
    return find_programdata_manifest() or find_appdata_manifest()


def is_pyrevit_for_allusers():
    allusers = find_programdata_manifest() is not None
    mlogger.debug('Is pyRevit installed for All users? {}'.format(allusers))
    return allusers


def set_dynamocompat(compat_state=False):
    loader_ver = \
        addin.DYNAMOCOMPAT_PYREVITLOADER \
        if compat_state else addin.LATEST_PYREVITLOADER

    existing_addin_file = get_current_pyrevit_addin()

    try:
        with open(existing_addin_file, 'w') as f:
            f.writelines(
                addinfile_contents.format(
                    addinname=LOADER_ADDON_NAMESPACE,
                    addinfolder=op.join(ADDIN_DIR, loader_ver),
                    addinguid=ADDIN_GUID,
                    addinvendorid=ADDIN_VENDORID,
                    addinclassname=ADDIN_CLASSNAME
                )
            )
            mlogger.debug('Dynamo Compat Mode: {}'.format(compat_state))
    except Exception as write_err:
        mlogger.debug('Error writing {} | {}'
                     .format(existing_addin_file, write_err))


def get_dynamocompat():
    existing_addin_file = get_current_pyrevit_addin()

    try:
        with open(existing_addin_file, 'r') as f:
            for line in f.readlines():
                if addin.DYNAMOCOMPAT_PYREVITLOADER in line:
                    mlogger.debug('Dynamo Compat Mode is Active.')
                    return True
        mlogger.debug('Dynamo Compat Mode is Not Active.')
    except Exception as read_err:
        mlogger.debug('Error reading {} | {}'
                     .format(existing_addin_file, read_err))

    return False
