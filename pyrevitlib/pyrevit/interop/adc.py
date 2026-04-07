# coding=utf-8
"""Wrapping Autodesk Desktop Connector API.

Supports two API surfaces:
  - LEGACY (ADC v15-v17): Autodesk.DesktopConnector.API.DesktopConnectorService
    Full file-level ops (lock, unlock, sync, properties).
    Requires WCF on .NET Framework; had a dedicated .NET 8 build at
    FOS/AddInProcess/Civil3DOE (removed in v2027).

  - PUBLIC (ADC v2027+): Autodesk.DesktopConnector.API.Public.DesktopConnectorApiClient
    Subscription-level ops only (projects, drives, availability).
    No file-level lock/unlock/sync - degrades gracefully.
    Native .NET 8 support, no WCF dependency.
"""

import os.path as op
from pyrevit import PyRevitException
from pyrevit.framework import clr, Process, System

from pyrevit import HOST_APP

ADC_NAME = "Autodesk Desktop Connector"
ADC_SHORTNAME = "ADC"
ADC_DRIVE_SCHEMA = "{drive_name}://"

# =====================================================================
# API SURFACE DETECTION
# =====================================================================

ADC_ROOT = r"C:\Program Files\Autodesk\Desktop Connector"
API = None  # Legacy API module (DesktopConnectorService)
API_PUBLIC = None  # Public API module (DesktopConnectorApiClient, v2027+)
_api_mode = None  # "public", "legacy", or None

ADC_DEFAULT_INSTALL_PATH = ADC_ROOT
ADC_API_DLL = "Autodesk.DesktopConnector.API.dll"
ADC_API_DLL_PATH = op.join(ADC_ROOT, ADC_API_DLL)


def _preload_wcf_for_public_api():
    """Pre-load WCF assemblies and register an AssemblyResolve handler
    so that the Public API's transitive dependency on
    System.ServiceModel v4.0.0.0 is satisfied on .NET 8.

    The Public API DLL (API.Public.dll) transitively depends on
    System.ServiceModel through the shared API.Contracts layer.
    On .NET 8 there's no unified System.ServiceModel.dll on the
    probing path — it's split into separate NuGet packages.

    Strategy:
      1. Load split WCF DLLs from ADC's FOS/Client/SDK
      2. Load System.ServiceModel.dll facade from NuGet cache
         (ships inside the system.servicemodel.primitives package)
      3. Register AssemblyResolve handler as fallback
      4. Load API.Contracts.dll from ADC root
    """
    from System.Reflection import Assembly as SysAssembly

    loaded = 0

    # --- 1. Split WCF assemblies from FOS/Client/SDK ---
    sdk_path = op.join(ADC_ROOT, "FOS", "Client", "SDK")
    if op.isdir(sdk_path):
        for dll in [
            "System.ServiceModel.Primitives.dll",
            "System.ServiceModel.Http.dll",
            "System.ServiceModel.NetTcp.dll",
            "System.ServiceModel.Duplex.dll",
            "System.ServiceModel.Security.dll",
        ]:
            full = op.join(sdk_path, dll)
            if op.exists(full):
                try:
                    clr.AddReferenceToFileAndPath(full)
                    loaded += 1
                except Exception:
                    pass

    # --- 2. System.ServiceModel.NetNamedPipe from Revit dir ---
    revit_dir = ""
    try:
        revit_dir = op.dirname(HOST_APP.proc_path) if HOST_APP.proc_path else ""
    except Exception:
        pass
    if revit_dir:
        nnp = op.join(revit_dir, "System.ServiceModel.NetNamedPipe.dll")
        if op.exists(nnp):
            try:
                clr.AddReferenceToFileAndPath(nnp)
                loaded += 1
            except Exception:
                pass

    # --- 3. System.ServiceModel.dll facade from NuGet cache ---
    #     This is the unified assembly that satisfies the v4.0.0.0
    #     reference.  It ships inside the Primitives NuGet package.
    import os as _os
    import re as _re

    def _ver_key(s):
        """Semantic version sort key — handles 4.10.0 > 4.9.0."""
        parts = _re.split(r"[.\-]", s)
        return [int(p) if p.isdigit() else p for p in parts]

    sm_facade = None
    nuget = op.join(
        _os.environ.get("USERPROFILE", ""),
        ".nuget",
        "packages",
        "system.servicemodel.primitives",
    )
    if op.isdir(nuget):
        # Find the newest version's net6.0 or net8.0 facade
        for ver_dir in sorted(_os.listdir(nuget), key=_ver_key, reverse=True):
            for tfm in ["net8.0", "net6.0"]:
                candidate = op.join(
                    nuget, ver_dir, "lib", tfm, "System.ServiceModel.dll"
                )
                if op.exists(candidate):
                    sm_facade = candidate
                    break
            if sm_facade:
                break

    # Also try System.Private.ServiceModel from NuGet
    spm_dll = None
    spm_pkg = op.join(
        _os.environ.get("USERPROFILE", ""),
        ".nuget",
        "packages",
        "system.private.servicemodel",
    )
    if op.isdir(spm_pkg):
        for ver_dir in sorted(_os.listdir(spm_pkg), key=_ver_key, reverse=True):
            for tfm in ["net8.0", "netstandard2.0", "net6.0"]:
                candidate = op.join(
                    spm_pkg, ver_dir, "lib", tfm, "System.Private.ServiceModel.dll"
                )
                if op.exists(candidate):
                    spm_dll = candidate
                    break
            if spm_dll:
                break

    # Load the private implementation first (facade forwards to it)
    if spm_dll:
        try:
            clr.AddReferenceToFileAndPath(spm_dll)
            loaded += 1
        except Exception:
            pass

    # Load the facade
    _facade_asm = None
    if sm_facade:
        try:
            _facade_asm = SysAssembly.LoadFrom(sm_facade)
            loaded += 1
        except Exception:
            pass

    # --- 4. AssemblyResolve handler (fallback if facade not found) ---
    #     Intercepts the runtime's request for System.ServiceModel
    #     v4.0.0.0 and returns the loaded facade or Primitives assembly.
    _resolve_cache = {}
    if _facade_asm:
        _resolve_cache["system.servicemodel"] = _facade_asm

    # Cache any other loaded ServiceModel assemblies for redirection
    try:
        for asm in System.AppDomain.CurrentDomain.GetAssemblies():
            name = asm.GetName().Name.lower()
            if "servicemodel" in name or "private.servicemodel" in name:
                _resolve_cache[name] = asm
    except Exception:
        pass

    if _resolve_cache:

        def _wcf_resolve(sender, args):
            try:
                req = args.Name.split(",")[0].strip().lower()
                if req in _resolve_cache:
                    return _resolve_cache[req]
            except Exception:
                pass
            return None

        try:
            System.AppDomain.CurrentDomain.AssemblyResolve += _wcf_resolve
        except Exception:
            pass

    # --- 5. API.Contracts.dll from ADC root ---
    contracts = op.join(ADC_ROOT, "Autodesk.DesktopConnector.API.Contracts.dll")
    if op.exists(contracts):
        try:
            clr.AddReferenceToFileAndPath(contracts)
            loaded += 1
        except Exception:
            pass

    if loaded:
        pass
    return loaded > 0


def _try_load_public_api():
    """Try to load the v2027+ public API (DesktopConnectorApiClient).

    Pre-loads WCF dependencies from ADC's bundled FOS/Client/SDK
    before importing, because API.Public.dll has a transitive
    dependency on System.ServiceModel through the shared contracts."""
    global API_PUBLIC
    dll = op.join(ADC_ROOT, "Autodesk.DesktopConnector.API.Public.dll")
    if not op.exists(dll):
        return False
    try:
        # Pre-load WCF + contracts BEFORE the Public API import
        _preload_wcf_for_public_api()
        clr.AddReferenceToFileAndPath(dll)
        import Autodesk.DesktopConnector.API.Public as _pub

        if hasattr(_pub, "DesktopConnectorApiClient"):
            API_PUBLIC = _pub
            return True
    except Exception as ex:
        pass
    return False


def _try_load_legacy_api():
    """Try to load the legacy API (DesktopConnectorService)."""
    global API, ADC_DEFAULT_INSTALL_PATH, ADC_API_DLL_PATH

    candidates = []
    if HOST_APP.is_newer_than("2024"):
        candidates.append(op.join(ADC_ROOT, "FOS", "AddInProcess", "Civil3DOE"))
    candidates.append(ADC_ROOT)

    for path in candidates:
        dll = op.join(path, ADC_API_DLL)
        if not op.exists(dll):
            continue
        try:
            clr.AddReferenceToFileAndPath(dll)
            import Autodesk.DesktopConnector.API as _api

            # Verify service can instantiate (catches WCF failures early)
            _api.DesktopConnectorService()
            API = _api
            ADC_DEFAULT_INSTALL_PATH = path
            ADC_API_DLL_PATH = dll
            return True
        except Exception as ex:
            pass


# =====================================================================
# INTERNAL HELPERS - LEGACY (DesktopConnectorService)
# =====================================================================


def _get_all_processids():
    return [x.Id for x in Process.GetProcesses()]


def _get_adc():
    if not API:
        raise PyRevitException("{} legacy API is not loaded".format(ADC_NAME))
    return API.DesktopConnectorService()


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
        op.join(drv_info.WorkspaceLocation, path.replace(drive_schema, ""))
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


# =====================================================================
# INTERNAL HELPERS - PUBLIC API (DesktopConnectorApiClient, v2027+)
# =====================================================================


def _get_pub_client():
    if not API_PUBLIC:
        raise PyRevitException("{} public API is not loaded".format(ADC_NAME))
    return API_PUBLIC.DesktopConnectorApiClient()


def _get_pub_subscriptions():
    client = _get_pub_client()
    try:
        subs = client.GetSubscriptions()
        return [s for s in subs if s.State == API_PUBLIC.SubscriptionState.Subscribed]
    finally:
        client.Dispose()


def _pub_drive_from_path(path):
    for sub in _get_pub_subscriptions():
        drive_schema = ADC_DRIVE_SCHEMA.format(drive_name=sub.Name)
        if path.lower().startswith(drive_schema.lower()):
            return sub, drive_schema
    return None, None


def _pub_drive_path_to_local(sub, drive_schema, path):
    rel = path[len(drive_schema) :]  # strip prefix exactly once
    return op.normpath(op.join(sub.Path, rel))


# =====================================================================
# FILESYSTEM FALLBACK — bypasses API when WCF is broken
# =====================================================================
# ADC v2027 on .NET 8: both API surfaces (Public + Legacy) fail because
# the DLLs were compiled against .NET Framework's unified
# System.ServiceModel which doesn't exist on .NET 8.
#
# Fallback: the ADC service IS running and files ARE synced locally.
# We just can't talk to the service via API.  Instead we:
#   1. Check the ADC tray process is running (for is_available)
#   2. Parse the cloud path schema and walk known workspace dirs
#      on disk to find the local file (for get_local_path)


def _adc_process_running():
    """Check if the Desktop Connector tray process is running."""
    try:
        for p in Process.GetProcesses():
            if "DesktopConnector" in p.ProcessName:
                return True
    except Exception:
        pass
    return False


def _find_workspace_roots():
    """Find ADC workspace root directories on this machine.
    Returns a list of directories that contain org/project folders.

    Known ADC workspace layouts:
      %USERPROFILE%\\ACCDocs\\{org}\\{project}\\...
      %USERPROFILE%\\DC\\ACCDocs\\{org}\\{project}\\...
      %USERPROFILE%\\DC\\{org}\\{project}\\..."""
    import os as _os

    roots = []
    user_profile = _os.environ.get("USERPROFILE", "")
    if not user_profile:
        return roots
    # Standard ADC workspace locations (order matters — more specific first)
    for subpath in ["DC\\ACCDocs", "ACCDocs", "DC"]:
        candidate = op.join(user_profile, subpath)
        if op.isdir(candidate):
            roots.append(candidate)
    return roots


def _parse_cloud_path(cloud_path):
    """Parse an ADC cloud path into (drive_name, relative_path).

    Cloud path formats:
      '{DriveName}://{org}/{project}/rest/of/path'
      'Autodesk Forma://Boulder Associates/ProjectName/...'
      'Autodesk Docs://OrgName/ProjectName/...'
      'BIM 360://OrgName/ProjectName/...'

    Returns (drive_name, relative_path) or (None, None).
    drive_name = everything before ://
    relative_path = everything after ://  (org/project/rest...)"""
    sep = "://"
    idx = cloud_path.find(sep)
    if idx < 0:
        return None, None
    drive_name = cloud_path[:idx]
    rel_path = cloud_path[idx + len(sep) :]
    return drive_name, rel_path


def _resolve_path_from_filesystem(cloud_path):
    """Resolve a cloud path to a local file by searching ADC workspace
    directories on disk.  Bypasses the API entirely.

    Returns the local file path if found, else None."""
    import os as _os

    drive_name, rel_path = _parse_cloud_path(cloud_path)
    if not rel_path:
        return None

    # rel_path is like: "Boulder Associates/257197.00 .../path/to/file.txt"
    # Split into segments
    segments = rel_path.replace("\\", "/").split("/")
    if len(segments) < 2:
        return None

    org_name = segments[0]
    rest = "/".join(segments[1:])

    for ws_root in _find_workspace_roots():
        # Check if org directory exists
        org_dir = op.join(ws_root, org_name)
        if not op.isdir(org_dir):
            continue

        # Try direct join: ws_root/org/project/rest...
        candidate = op.normpath(op.join(ws_root, *segments))
        if op.exists(candidate):
            return candidate

        # Try case-insensitive search in org directory
        try:
            for entry in _os.listdir(org_dir):
                project_candidate = op.join(org_dir, entry)
                if not op.isdir(project_candidate):
                    continue
                # Match only if one name fully starts with the other
                seg2 = segments[1].lower()
                entry_l = entry.lower()
                if seg2.startswith(entry_l) or entry_l.startswith(seg2):
                    # Try building path from this project dir
                    file_path = op.normpath(op.join(project_candidate, *segments[2:]))
                    if op.exists(file_path):
                        return file_path
        except Exception:
            pass

    return None


# =====================================================================
# PUBLIC INTERFACE (auto-dispatches to best available backend)
# =====================================================================


def is_available():
    """Check if ADC service is available.
    Falls back to process detection if API calls fail."""
    if API_PUBLIC:
        try:
            client = _get_pub_client()
            try:
                client.GetDesktopConnectorInfo()
                return True
            finally:
                client.Dispose()
        except Exception as ex:
            pass
    if API:
        try:
            _get_adc().Discover()
            return True
        except Exception as ex:
            pass
    # Filesystem fallback: ADC process running + workspace dirs exist
    # Verify workspace roots actually contain org subdirectories
    if _adc_process_running():
        for ws_root in _find_workspace_roots():
            try:
                import os as _os

                entries = _os.listdir(ws_root)
                if any(op.isdir(op.join(ws_root, e)) for e in entries):
                    return True
            except Exception:
                pass
    return False


def get_drive_paths():
    """Get dict of local paths for ADC drives."""
    if API_PUBLIC:
        try:
            return {s.Name: s.Path for s in _get_pub_subscriptions()}
        except Exception:
            pass
    if API:
        adc = _get_adc()
        return {x.Name: x.WorkspaceLocation for x in _get_drives_info(adc)}
    # Filesystem fallback: list workspace root contents
    import os as _os

    result = {}
    for ws_root in _find_workspace_roots():
        try:
            for org in _os.listdir(ws_root):
                org_path = op.join(ws_root, org)
                if op.isdir(org_path):
                    result[org] = org_path
        except Exception:
            pass
    return result


def get_local_path(path):
    """Convert ADC cloud drive path to local path."""
    # Try Public API first (v2027+)
    if API_PUBLIC:
        try:
            sub, schema = _pub_drive_from_path(path)
            if sub:
                return _pub_drive_path_to_local(sub, schema, path)
        except Exception as ex:
            pass
    # Try Legacy API
    if API:
        try:
            adc = _get_adc()
            drv_info = _get_drive_from_path(adc, path)
            if drv_info:
                return _drive_path_to_local_path(drv_info, path)
        except Exception as ex:
            pass
    # Filesystem fallback
    resolved = _resolve_path_from_filesystem(path)
    if resolved:
        return resolved
    return None


def lock_file(path):
    """Lock given file. No-op if only Public API available."""
    if not API:
        return
    adc = _get_adc()
    item = _get_item(adc, path)
    adc.LockFile(item.Id)


def is_locked(path):
    """Check if file is locked. Returns (False, None) if unavailable."""
    if not API:
        return False, None
    adc = _get_adc()
    item = _get_item(adc, path)
    lock_status = _get_item_lockstatus(adc, item)
    return lock_status.State == API.LockState.LockedByOther, lock_status.LockOwner


def unlock_file(path):
    """Unlock given file. No-op if only Public API available."""
    if not API:
        return
    adc = _get_adc()
    item = _get_item(adc, path)
    adc.UnlockFile(item.Id)


def is_synced(path):
    """Check if file is synchronized. Assumes True if unavailable."""
    if not API:
        return True
    adc = _get_adc()
    item = _get_item(adc, path)
    drive = _get_item_drive(adc, item)
    prop_val = _get_item_property_id_value(
        adc, drive, item, "DesktopConnector.Core.LocalState"
    )
    if prop_val is None:
        prop_val = _get_item_property_id_value(adc, drive, item, "LocalState")
    return prop_val.Value == "Cached" or prop_val.Value == "Synced"


def sync_file(path, force=False):
    """Force ADC to sync given file. No-op if only Public API available."""
    if not API:
        return
    if not force and is_synced(path):
        return
    adc = _get_adc()
    item = _get_item(adc, path)
    local_path = _ensure_local_path(adc, path)
    for proc_id in _get_all_processids():
        adc.FileClosedWithinRunningProcess(proc_id, local_path)
    adc.SyncFiles([item.Id])
