"""Wrapping Autodesk Desktop Connector API"""
#pylint: disable=bare-except,broad-except
import os.path as op
from pyrevit import PyRevitException
from pyrevit.framework import clr, Process
from pyrevit.coreutils import logger


mlogger = logger.get_logger(__name__)


ADC_NAME = "Autodesk Desktop Connector"
ADC_SHORTNAME = "ADC"
ADC_DRIVE_SCHEMA = '{drive_name}://'

ADC_DEFAULT_INSTALL_PATH = \
    r'C:\Program Files\Autodesk\Desktop Connector'
ADC_API_DLL = 'Autodesk.DesktopConnector.API.dll'
ADC_API_DLL_PATH = op.join(ADC_DEFAULT_INSTALL_PATH, ADC_API_DLL)

API = None
if op.exists(ADC_API_DLL_PATH):
    try:
        clr.AddReferenceToFileAndPath(ADC_API_DLL_PATH)
        import Autodesk.DesktopConnector.API as API #pylint: disable=import-error
    except:
        pass

def _ensure_api():
    if not API:
        raise PyRevitException("{} is not loaded".format(ADC_NAME))
    return API


def _get_all_processids():
    return [x.Id for x in Process.GetProcesses()]


def _get_adc():
    api = _ensure_api()
    return api.DesktopConnectorService()


def _get_drives_info(adc):
    return list(adc.GetDrives())


def _get_drive_properties(adc, drive):
    return adc.GetPropertyDefinitions(drive.Id)


def _get_drive_from_path(adc, path):
    for drv_info in _get_drives_info(adc):
        drive_schema = ADC_DRIVE_SCHEMA.format(drive_name=drv_info.Name)
        if path.lower().startswith(drive_schema.lower()):
            return drv_info


def _get_drive_from_local_path(adc, local_path):
    for drv_info in _get_drives_info(adc):
        drv_localpath = op.normpath(drv_info.WorkspaceLocation)
        if op.normpath(local_path).startswith(drv_localpath):
            return drv_info


def _drive_path_to_local_path(drv_info, path):
    drive_schema = ADC_DRIVE_SCHEMA.format(drive_name=drv_info.Name)
    return op.normpath(
        op.join(
            drv_info.WorkspaceLocation,
            path.replace(drive_schema, '')
        )
    )


def _ensure_local_path(adc, path):
    drv_info = _get_drive_from_path(adc, path)
    if drv_info:
        return _drive_path_to_local_path(drv_info, path)
    elif not _get_drive_from_local_path(adc, path):
        raise PyRevitException("Path is not inside any ADC drive")
    return path


def _get_item(adc, path):
    path = _ensure_local_path(adc, path)
    if not op.isfile(path):
        raise PyRevitException("Path does not point to a file")

    res = adc.GetItemsByWorkspacePaths([path])
    if not res:
        raise PyRevitException("Can not find item in any ADC drive")
    # grab the first item (we only except one since path is to a file)
    return res[0].Item


def _get_item_drive(adc, item):
    for drv_info in _get_drives_info(adc):
        if drv_info.Id == item.DriveId:
            return drv_info


def _get_item_lockstatus(adc, item):
    res = adc.GetLockStatus([item.Id])
    if res and res.Status:
        return res.Status[0]


def _get_item_property_value(adc, drive, item, prop_name):
    for prop_def in _get_drive_properties(adc, drive):
        if prop_def.DisplayName == prop_name:
            res = adc.GetProperties([item.Id], [prop_def.Id])
            if res:
                return res.Values[0]


def _get_item_property_id_value(adc, drive, item, prop_id):
    for prop_def in _get_drive_properties(adc, drive):
        if prop_def.Id == prop_id:
            res = adc.GetProperties([item.Id], [prop_def.Id])
            if res:
                return res.Values[0]


def is_available():
    """Check if ADC service is available"""
    try:
        _get_adc().Discover()
        return True
    except Exception:
        return False


def get_drive_paths():
    """Get dict of local paths for ADC drives"""
    adc = _get_adc()
    return {x.Name: x.WorkspaceLocation for x in _get_drives_info(adc)}


def get_local_path(path):
    """Convert ADC BIM360 drive path to local path"""
    adc = _get_adc()
    drv_info = _get_drive_from_path(adc, path)
    if drv_info:
        return _drive_path_to_local_path(drv_info, path)


def lock_file(path):
    """Lock given file"""
    adc = _get_adc()
    item = _get_item(adc, path)
    adc.LockFile(item.Id)


def is_locked(path):
    """Check if file is locked"""
    adc = _get_adc()
    item = _get_item(adc, path)
    lock_status = _get_item_lockstatus(adc, item)
    return lock_status.State == API.LockState.LockedByOther, \
        lock_status.LockOwner


def unlock_file(path):
    """Unlock given file"""
    adc = _get_adc()
    item = _get_item(adc, path)
    adc.UnlockFile(item.Id)


def is_synced(path):
    """Check if file is synchronized"""
    adc = _get_adc()
    item = _get_item(adc, path)
    drive = _get_item_drive(adc, item)
    # ADC uses translated property names so
    # check status property by its type "LocalState"
    # see https://github.com/eirannejad/pyRevit/issues/1152
    # ADC version 15 changed property_id_value
    # see https://github.com/eirannejad/pyRevit/issues/1371
    prop_val = _get_item_property_id_value(adc, drive, item, 'DesktopConnector.Core.LocalState')
    if prop_val is None:
        # version older than ADC 15
        prop_val = _get_item_property_id_value(adc, drive, item, 'LocalState')
    # possible values, 'Cached', 'Stale', 'Modified'
    # .Value is not translated
    return prop_val.Value == 'Cached'or prop_val.Value == 'Synced'


def sync_file(path, force=False):
    """Force ADC to sync given file to latest version"""
    if not force and is_synced(path):
        return
    adc = _get_adc()
    item = _get_item(adc, path)
    # make sure path is local
    local_path = _ensure_local_path(adc, path)
    for proc_id in _get_all_processids():
        adc.FileClosedWithinRunningProcess(proc_id, local_path)
    adc.SyncFiles([item.Id])
