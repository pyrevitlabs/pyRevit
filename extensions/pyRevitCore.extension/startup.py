"""pyRevit core startup script"""
#pylint: disable=import-error,unused-import,invalid-name
from pyrevit._perf import mark as _perfmark
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
# Registered through pyRevit's own forms.register_dockable_panel so it follows the same lifecycle
# as every other pyRevit dockable pane. The pane is registered here during startup but hidden by
# default; the heavy console is only built the first time the pane is shown (see on_loaded). The
# console control itself is built by the pyRevitLabs.PyRevit.Shell assembly that ships in the
# active engine folder; it configures the full pyRevit environment and marshals each statement
# through an ExternalEvent so Revit stays interactive while the pane is open.

PYTHON_SHELL_DOCKABLE_PANEL_ID = "8e2a1f4b-3c57-4d9a-b6e8-7f1a2c3d4e5b"

# Capture the live UIApplication now, while this startup script is executing and the handle is
# valid. The console is built lazily (deferred to when the pane is first shown), and by then the
# __revit__ builtin is no longer reliably resolvable from this module, so resolving it late fails.
_SHELL_UIAPP = HOST_APP.uiapp


def _build_dockable_shell_console():
    """Return a configured Python shell control (console, or editor when configured) for the dockable pane."""
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
    if engine_dir is None or _SHELL_UIAPP is None:
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

    # The dockable pane is shared; pick the editor surface when the user configured a "Docked"
    # Editor" mode (same "mode" option the Python Shell pushbutton writes). Falls back to the
    # console-only pane for every other mode.
    if _get_shell_mode() == "Docked Editor":
        return Shell.CreateDockableEditor(_SHELL_UIAPP, search_paths)
    return Shell.CreateDockableConsole(_SHELL_UIAPP, search_paths)


def _get_shell_mode():
    # Mirrors the pushbutton config section ("Python Shell_config") so the dockable pane honors the
    # same preference the Python Shell button writes.
    try:
        section = user_config.get_section("Python Shell_config")
        if section is None:
            return "Modeless"
        return section.get_option("mode", "Modeless")
    except Exception:
        return "Modeless"


try:
    from pyrevit import forms
    from pyrevit.framework import System, Media
    from pyrevit.revit import ui as rvt_ui
    from Autodesk.Revit.UI.Events import IdlingEventArgs

    class PythonShellDockablePanel(forms.WPFPanel):
        panel_title = "pyRevit Python Shell"
        panel_id = PYTHON_SHELL_DOCKABLE_PANEL_ID
        panel_source = op.join(op.dirname(__file__), "PythonShellDockablePanel.xaml")

        def __init__(self):
            # Mark not-built before loading XAML, in case Loaded fires during LoadComponent.
            self._console = None
            self._pane_shown = False
            self._build_idling_handler = None
            forms.WPFPanel.__init__(self)
            # Match the pane background to the active Revit UI theme so the shell does not flash
            # dark on a light-themed Revit; the console control is themed by the shell assembly.
            self._apply_panel_theme()
            # Subscribing to Idling must happen in a valid API context; __init__ runs during
            # register_dockable_panel (called from this startup script), which is one. The handler
            # builds the console only after the pane is shown, so nothing heavy loads at startup.
            if _SHELL_UIAPP is not None:
                self._build_idling_handler = \
                    System.EventHandler[IdlingEventArgs](self._build_on_idling)
                _SHELL_UIAPP.Idling += self._build_idling_handler

        def on_loaded(self, sender, args):
            # Record visibility only. The console build needs a Revit API context, which this WPF
            # callback is not, so the actual build runs from the Idling handler above.
            self._pane_shown = True

        def _build_on_idling(self, sender, args):
            # Idling runs in a valid API context, which the shell build requires (it creates an
            # ExternalEvent). Build once the pane has been shown, then stop listening.
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
            # UIThemeManager only exists in Revit 2024+; older releases have no dark theme and
            # stay light, so any failure to resolve the theme falls back to light.
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
            # Surface build failures directly in the pane; otherwise the pane just renders empty
            # and the only trace is in the pyRevit log.
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
        # Revit persists pane visibility across sessions, so a pane that was shown before reopens
        # on startup even though it now registers hidden. Hiding needs a valid API context, which
        # this Idling tick provides; run once, then stop listening.
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
        forms.register_dockable_panel(PythonShellDockablePanel, default_visible=False)
        if _SHELL_UIAPP is not None:
            _hide_idling_handler = System.EventHandler[IdlingEventArgs](
                _ensure_shell_pane_hidden
            )
            _SHELL_UIAPP.Idling += _hide_idling_handler
except Exception:
    mlogger.exception("Failed to register dockable Python shell panel")


_perfmark("startup.pyRevitCore:exit")
