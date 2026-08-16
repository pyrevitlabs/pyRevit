"""pyRevit core startup script"""
#pylint: disable=import-error,unused-import,invalid-name
from pyrevit._perf import mark as _perfmark, time_block as _perfblock
_perfmark("startup.pyRevitCore:entry")

import sys

from pyrevit import HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config


mlogger = get_logger(__name__)


# decide to load the core api
if user_config.load_core_api:
    import pyrevitcore_api
    # mlogger.info("pyRevit Core Routes API is activated")


_perfmark("startup.pyRevitCore:before shell")


def _get_shell_mode():
    try:
        section = user_config.get_section("Python Shell_config")
        if section is None:
            return "Modeless"
        return section.get_option("mode", "Modeless")
    except Exception:
        return "Modeless"


try:
    with _perfblock("startup.pyRevitCore:shell imports"):
        import clr
        from System import AppDomain
        from System.IO import File, Path
        from System.Collections.Generic import List

        # Loading beside pyRevitLoader preserves the active engine fork.
        engine_dir = None
        for asm in AppDomain.CurrentDomain.GetAssemblies():
            if asm.GetName().Name == "pyRevitLoader":
                engine_dir = Path.GetDirectoryName(asm.Location)
                break
        shell_dll = (
            Path.Combine(engine_dir, "pyRevitLabs.PyRevit.Shell.dll")
            if engine_dir
            else None
        )
        if shell_dll and File.Exists(shell_dll):
            clr.AddReferenceToFileAndPath(shell_dll)
            from PyRevitLabs.PyRevit.Shell import Shell
        else:
            Shell = None

    if Shell is not None and HOST_APP.uiapp is not None:
        search_paths = List[str]()
        for path in sys.path:
            search_paths.Add(path)
        with _perfblock("startup.pyRevitCore:shell pane registration"):
            Shell.RegisterDockablePane(
                HOST_APP.uiapp,
                search_paths,
                _get_shell_mode() == "Docked Editor",
            )
except Exception:
    mlogger.exception("Failed to register dockable Python shell panel")

_perfmark("startup.pyRevitCore:shell total")
_perfmark("startup.pyRevitCore:exit")
