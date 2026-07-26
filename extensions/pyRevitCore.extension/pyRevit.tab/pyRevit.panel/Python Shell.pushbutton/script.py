# -*- coding: utf-8 -*-
"""Open the interactive pyRevit Python shell.

How the shell opens (modal window, modeless window, dockable pane, or the same
windows with a built-in code editor) is configurable: Shift+Click this button to
choose the mode.
"""
import sys
import clr

from pyrevit import script, forms
from System import AppDomain
from System.IO import File, Path
from System.Collections.Generic import List

# Must stay in sync with the dockable pane registered in pyRevitCore.extension/startup.py.
DOCKABLE_PANEL_ID = "8e2a1f4b-3c57-4d9a-b6e8-7f1a2c3d4e5b"

shell_mode = script.get_config().get_option("mode", "Modeless")
mlogger = script.get_logger()


def _load_shell():
    # The shell DLL ships into the active engine folder (the IronPython fork pyRevit runs),
    # alongside the loaded pyRevitLoader; loading it from there makes the shell use that engine.
    engine_dir = None
    for asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == "pyRevitLoader":
            engine_dir = Path.GetDirectoryName(asm.Location)
            break
    if engine_dir is None:
        forms.alert(
            "Python Shell could not find the loaded pyRevit engine.",
            title="Python Shell",
            exitscript=True,
        )

    shell_path = Path.Combine(
        engine_dir, "pyRevitLabs.PyRevit.Shell.dll"
    )
    if not File.Exists(shell_path):
        forms.alert(
            "Python Shell is not installed for the active engine:\n\n"
            + shell_path
            + "\n\nRebuild or reinstall pyRevit to deploy the shell.",
            title="Python Shell",
            exitscript=True,
        )

    try:
        clr.AddReferenceToFileAndPath(shell_path)
    except Exception as load_error:
        mlogger.exception("Failed to load Python Shell assembly")
        forms.alert(
            "Python Shell could not load:\n\n"
            + shell_path
            + "\n\n"
            + str(load_error),
            title="Python Shell",
            exitscript=True,
        )
    from PyRevitLabs.PyRevit.Shell import Shell

    # Forward this engine's sys.path so `from pyrevit import ...` resolves in the shell as here.
    search_paths = List[str]()
    for path in sys.path:
        search_paths.Add(path)
    return Shell, search_paths


if shell_mode in ("Docked", "Docked Editor"):
    forms.open_dockable_panel(DOCKABLE_PANEL_ID)
else:
    shell, paths = _load_shell()
    if shell_mode == "Modal":
        shell.Modal(__revit__, paths)
    elif shell_mode == "Modal Editor":
        shell.ModalEditor(__revit__, paths)
    elif shell_mode == "Modeless Editor":
        shell.ModelessEditor(__revit__, paths)
    else:
        shell.Modeless(__revit__, paths)
