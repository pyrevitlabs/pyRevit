"""pyRevit core startup script"""
#pylint: disable=import-error,unused-import,invalid-name
from pyrevit._perf import mark as _perfmark
_perfmark("startup.pyRevitCore:entry")

import os.path as op
import sys

from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config


mlogger = get_logger(__name__)


# decide to load the core api
if user_config.load_core_api:
    import pyrevitcore_api
    # mlogger.info("pyRevit Core Routes API is activated")


# dockable interactive python shell ==========================================
# Registered through pyRevit's own forms.register_dockable_panel so it follows the same lifecycle
# as every other pyRevit dockable pane (registered here during startup, visible by default). The
# console control itself is built by the pyRevitLabs.PyRevit.Shell assembly that ships in the
# active engine folder; it configures the full pyRevit environment and marshals each statement
# through an ExternalEvent so Revit stays interactive while the pane is open.

PYTHON_SHELL_DOCKABLE_PANEL_ID = "8e2a1f4b-3c57-4d9a-b6e8-7f1a2c3d4e5b"


def _build_dockable_shell_console():
    """Return a configured IronPythonConsole control, or None if the shell is unavailable.

    Uses __revit__ (the live UIApplication of the running engine) exactly like the modeless shell
    launcher script, so the REPL is configured with the same API context.
    """
    import clr
    from System import AppDomain
    from System.IO import Path, File
    from System.Collections.Generic import List

    # The shell DLL lives in the active engine folder next to pyRevitLoader; loading it from
    # there makes the shell use the engine pyRevit is configured to run.
    engine_dir = None
    for asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == "pyRevitLoader":
            engine_dir = Path.GetDirectoryName(asm.Location)
            break
    if engine_dir is None:
        return None
    shell_dll = Path.Combine(engine_dir, "pyRevitLabs.PyRevit.Shell.dll")
    if not File.Exists(shell_dll):
        return None
    clr.AddReferenceToFileAndPath(shell_dll)
    from PyRevitLabs.PyRevit.Shell import Shell

    # Forward this engine's sys.path so `from pyrevit import ...` resolves in the shell exactly
    # as in a normal script.
    search_paths = List[str]()
    for path in sys.path:
        search_paths.Add(path)

    return Shell.CreateDockableConsole(__revit__, search_paths)


try:
    from pyrevit import forms
    from pyrevit.framework import System, Threading

    class PythonShellDockablePanel(forms.WPFPanel):
        panel_title = "pyRevit Python Shell"
        panel_id = PYTHON_SHELL_DOCKABLE_PANEL_ID
        panel_source = op.join(op.dirname(__file__), "PythonShellDockablePanel.xaml")

        def __init__(self):
            # Mark not-built before loading XAML, in case Loaded fires during LoadComponent.
            self._console = None
            forms.WPFPanel.__init__(self)
            # Defer building the console until the UI thread is idle (i.e. after pyRevit has
            # finished its startup pass), so the shell engine is configured against a fully
            # initialised pyRevit runtime. The Loaded handler below covers the same need; both
            # are guarded so the console is only built once.
            try:
                self.Dispatcher.BeginInvoke(
                    Threading.DispatcherPriority.Background,
                    System.Action(lambda: self._attach_console()),
                )
            except Exception:
                mlogger.debug("Could not schedule dockable shell console build")

        def on_loaded(self, sender, args):
            self._attach_console()

        def _attach_console(self):
            if self._console is not None:
                return
            try:
                console = _build_dockable_shell_console()
                if console is not None:
                    self._console = console
                    self.console_host.Children.Add(console)
            except Exception:
                mlogger.exception("Failed to create dockable Python shell console")

    if not forms.is_registered_dockable_panel(PythonShellDockablePanel):
        forms.register_dockable_panel(PythonShellDockablePanel, default_visible=True)
except Exception:
    mlogger.exception("Failed to register dockable Python shell panel")


_perfmark("startup.pyRevitCore:exit")