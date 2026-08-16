"""pyRevit core startup script"""
#pylint: disable=import-error,unused-import,invalid-name
from pyrevit._perf import mark as _perfmark, time_block as _perfblock
_perfmark("startup.pyRevitCore:entry")

import os.path as op
import sys

from pyrevit import HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.userconfig import user_config


mlogger = get_logger(__name__)


# decide to load the core api
if user_config.load_core_api:
    import pyrevitcore_api
    # mlogger.info("pyRevit Core Routes API is activated")


# dockable interactive python shell ==========================================
# Register the pane at startup but defer its console until first display.

PYTHON_SHELL_DOCKABLE_PANEL_ID = "8e2a1f4b-3c57-4d9a-b6e8-7f1a2c3d4e5b"

# Deferred construction cannot rely on the command-scoped __revit__ builtin.
_SHELL_UIAPP = HOST_APP.uiapp


def _build_dockable_shell_console():
    """Create the configured dockable shell surface."""
    import clr
    from System import AppDomain
    from System.IO import Path, File
    from System.Collections.Generic import List

    # Loading beside pyRevitLoader preserves the active engine fork.
    engine_dir = None
    for asm in AppDomain.CurrentDomain.GetAssemblies():
        if asm.GetName().Name == "pyRevitLoader":
            engine_dir = Path.GetDirectoryName(asm.Location)
            break
    if engine_dir is None or _SHELL_UIAPP is None:
        return None
    shell_dll = Path.Combine(engine_dir, "pyRevitLabs.PyRevit.Shell.dll")
    if not File.Exists(shell_dll):
        return None
    clr.AddReferenceToFileAndPath(shell_dll)
    from PyRevitLabs.PyRevit.Shell import Shell

    # Preserve the launching engine's module search paths.
    search_paths = List[str]()
    for path in sys.path:
        search_paths.Add(path)

    if _get_shell_mode() == "Docked Editor":
        return Shell.CreateDockableEditor(_SHELL_UIAPP, search_paths)
    return Shell.CreateDockableConsole(_SHELL_UIAPP, search_paths)


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
        from pyrevit import forms
        from pyrevit.framework import System, Media
        from pyrevit.revit import ui as rvt_ui
        from Autodesk.Revit.UI.Events import IdlingEventArgs

    class PythonShellDockablePanel(forms.WPFPanel):
        panel_title = "pyRevit Python Shell"
        panel_id = PYTHON_SHELL_DOCKABLE_PANEL_ID
        panel_source = op.join(op.dirname(__file__), "PythonShellDockablePanel.xaml")

        def __init__(self):
            # Loaded may fire during WPFPanel initialization.
            self._console = None
            self._pane_shown = False
            self._build_idling_handler = None
            forms.WPFPanel.__init__(self)
            # Avoid a mismatched background before deferred content is created.
            self._apply_panel_theme()
            # Event subscription requires the startup API context.
            if _SHELL_UIAPP is not None:
                self._build_idling_handler = \
                    System.EventHandler[IdlingEventArgs](self._build_on_idling)
                _SHELL_UIAPP.Idling += self._build_idling_handler

        def on_loaded(self, sender, args):
            # WPF loading is not a valid Revit API context for console construction.
            self._pane_shown = True

        def _build_on_idling(self, sender, args):
            # Idling provides the API context required by deferred construction.
            if self._console is not None or not self._pane_shown:
                return
            if self._build_idling_handler is not None:
                try:
                    _SHELL_UIAPP.Idling -= self._build_idling_handler
                except Exception:
                    pass
                self._build_idling_handler = None
            self._attach_console()

        def _apply_panel_theme(self):
            # Older Revit versions have no dark theme and remain light.
            try:
                is_dark = rvt_ui.get_current_theme() == rvt_ui.UITheme.Dark
            except Exception:
                is_dark = False
            self.Background = (
                Media.SolidColorBrush(Media.Color.FromRgb(0x1F, 0x2D, 0x3D))
                if is_dark
                else Media.SolidColorBrush(Media.Colors.White)
            )

        def _attach_console(self):
            if self._console is not None:
                return
            try:
                console = _build_dockable_shell_console()
                if console is not None:
                    self._console = console
                    self.console_host.Children.Add(console)
                else:
                    self._show_error("Shell console could not be created (no console returned).")
            except Exception as build_error:
                import traceback
                mlogger.exception("Failed to create dockable Python shell console")
                self._show_error(traceback.format_exc() or str(build_error))

        def _show_error(self, message):
            # Do not leave the pane blank when deferred construction fails.
            try:
                from pyrevit.framework import Controls
                block = Controls.TextBlock()
                block.Text = message
                block.TextWrapping = System.Windows.TextWrapping.Wrap
                block.Margin = System.Windows.Thickness(8)
                self.console_host.Children.Clear()
                self.console_host.Children.Add(block)
            except Exception:
                mlogger.exception("Failed to render dockable Python shell error")

    _hide_idling_handler = None

    def _ensure_shell_pane_hidden(sender, args):
        # Revit persists pane visibility, so enforce the hidden startup state in API context.
        global _hide_idling_handler
        if _hide_idling_handler is not None:
            try:
                _SHELL_UIAPP.Idling -= _hide_idling_handler
            except Exception:
                pass
            _hide_idling_handler = None
        try:
            from Autodesk.Revit.UI import DockablePaneId
            pane_id = DockablePaneId(System.Guid(PYTHON_SHELL_DOCKABLE_PANEL_ID))
            _SHELL_UIAPP.GetDockablePane(pane_id).Hide()
        except Exception:
            mlogger.debug("Could not hide dockable Python shell pane at startup")

    if not forms.is_registered_dockable_panel(PythonShellDockablePanel):
        with _perfblock("startup.pyRevitCore:shell pane registration"):
            forms.register_dockable_panel(PythonShellDockablePanel, default_visible=False)
        if _SHELL_UIAPP is not None:
            _hide_idling_handler = System.EventHandler[IdlingEventArgs](
                _ensure_shell_pane_hidden
            )
            _SHELL_UIAPP.Idling += _hide_idling_handler
except Exception:
    mlogger.exception("Failed to register dockable Python shell panel")

_perfmark("startup.pyRevitCore:exit")
