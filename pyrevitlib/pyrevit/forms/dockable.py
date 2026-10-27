"""Revit dockable panes built from pyRevit WPF pages, shared by both engines.

The backend supplies only the page root (``_backend.Panel``) and the Revit
pane provider (``_backend.make_pane_provider``). Registration, lookup and the
deferred show below behave identically under IronPython and CPython.

Note:
    This module must stay importable by IronPython 2.7.
"""

import time

from pyrevit import HOST_APP, UI, PyRevitException, coreutils, framework
from pyrevit.coreutils.logger import get_logger

from . import _backend
from .base import THEME_XAML_FILE, _WPFMixin, _resolve_xaml_source


mlogger = get_logger(__name__)

_PENDING_SHOWS_SLOT = "pyRevit.forms.pendingDockablePaneShowTokens"
_PENDING_SHOW_TIMEOUT_SECONDS = 60


class WPFPanel(_WPFMixin, _backend.Panel):
    r"""WPF panel base class for all pyRevit dockable panels.

    Subclass this, set the three required class attributes, then register
    and open the panel through the module-level helpers.

    Use self.logger and self.output instead of using script.get_logger() and
    script.get_output() to ensure correct titles in the output window.

    Required class attributes:
        panel_id (str): stable UUID string identifying the panel in Revit.
        panel_source (str): XAML filename (resolved relative to the command).
        panel_title (str): title displayed in the panel chrome.

    Optional class attributes:
        initial_state (UI.DockablePaneState):
            initial docking position; Revit picks a default when None.
        editor_interaction (UI.EditorInteractionType):
            how the panel behaves while an editor is active.
        contextual_help (UI.ContextualHelp):
            F1 help associated with the pane.
        resolve_theme (bool):
            resolve the palette from Revit's active UI theme. Defaults to False.

    Examples:
        ```python
        from pyrevit import forms
        import Autodesk.Revit.UI as UI

        state = UI.DockablePaneState()
        state.DockPosition = UI.DockPosition.Right

        class MyPanel(forms.WPFPanel):
            panel_id     = "181e05a4-28f6-4311-8a9f-d2aa528c8755"
            panel_source = "MyPanel.xaml"
            panel_title  = "My Panel"
            initial_state = state

        forms.register_dockable_panel(MyPanel)

        # open from any command button
        forms.open_dockable_panel(MyPanel)

        # retrieve the live instance from anywhere
        dockable_pane = forms.get_dockable_panel(MyPanel)
        ```
    """

    panel_id = None
    panel_source = None
    panel_title = None
    initial_state = None
    editor_interaction = None
    contextual_help = None
    resolve_theme = False

    _live_refresh_root_colors = True

    def __init__(self):
        """Initialize the page described by the panel class attributes."""
        if not self.panel_id:
            raise PyRevitException('"panel_id" class attribute is not set')
        if not self.panel_source:
            raise PyRevitException('"panel_source" class attribute is not set')
        if not self.panel_title:
            raise PyRevitException('"panel_title" class attribute is not set')
        _backend.initialize_panel(self)
        try:
            self.load_xaml(self.panel_source)
        except Exception:
            _backend.dispose(self)
            raise

    def load_xaml(self, xaml_source, literal_string=False):
        """Load the panel XAML and apply pyRevit form resources.

        Supports the full locale-fallback chain (see _resolve_xaml_source) and
        can accept raw XAML content via literal_string, matching WPFWindow.

        Args:
            xaml_source (str): XAML content string or file path.
            literal_string (bool): True when xaml_source is raw content.
        """
        _WPFMixin.setup_resources(self, resolve_theme=self.resolve_theme)
        self.merge_resource_dict(THEME_XAML_FILE)
        if literal_string:
            _backend.load_component(self, framework.StringReader(xaml_source))
        else:
            xaml_path, pending_resource_merge = _resolve_xaml_source(xaml_source)
            if pending_resource_merge:
                self.merge_resource_dict(pending_resource_merge)
            _backend.load_component(self, xaml_path)
        self.apply_contrast_foregrounds()
        self.thread_id = framework.get_current_thread_id()
        if self.resolve_theme:
            self._subscribe_theme_changed()

    def _get_panel_output(self):
        out = getattr(self, "_output", None)
        try:
            from pyrevit import script as _script

            current_out = _script.get_output()
            if current_out:
                self._output = current_out
                out = current_out
                current_out.set_title(self.panel_title)
        except Exception:
            pass
        return out

    @property
    def logger(self):
        """Logger named after the panel, created on first access."""
        try:
            logger = self._logger
        except AttributeError:
            logger = self._logger = get_logger(self.panel_title)
        self._get_panel_output()
        return logger

    @property
    def output(self):
        """Output window with title corrected to panel_title whenever accessed."""
        return self._get_panel_output()


def is_registered_dockable_panel(panel_type):
    """Return whether Revit has registered the panel type's stable pane identifier."""
    return UI.DockablePane.PaneIsRegistered(_get_dockable_panel_id(panel_type))


def register_dockable_panel(panel_type, default_visible=True):
    """Register a dockable panel with Revit and return its live page.

    Args:
        panel_type (type): A WPFPanel subclass describing the Revit pane.
        default_visible (bool): Whether Revit initially shows the pane.

    Returns:
        WPFPanel: The page instance Revit hosts in the pane.
    """
    if not isinstance(panel_type, type) or not issubclass(panel_type, WPFPanel):
        raise PyRevitException("Dockable pane must be a subclass of forms.WPFPanel")
    pane_id = _get_dockable_panel_id(panel_type)
    panel = panel_type()
    provider = _backend.make_pane_provider(panel, default_visible)
    HOST_APP.uiapp.RegisterDockablePane(pane_id, panel.panel_title, provider)
    return panel


def get_dockable_panel(panel_type_or_id):
    """Return Revit's dockable-pane handle for a registered panel type or UUID.

    Raises:
        PyRevitException: The reference is invalid or not registered.
    """
    pane_id = _get_registered_dockable_panel_id(panel_type_or_id)
    return HOST_APP.uiapp.GetDockablePane(pane_id)


def open_dockable_panel(panel_type_or_id):
    """Show a previously registered dockable panel.

    See ``toggle_dockable_panel`` for when the pane becomes visible.
    """
    toggle_dockable_panel(panel_type_or_id, True)


def close_dockable_panel(panel_type_or_id):
    """Hide a previously registered dockable panel."""
    toggle_dockable_panel(panel_type_or_id, False)


def toggle_dockable_panel(panel_type_or_id, state):
    """Show or hide a previously registered dockable panel.

    Revit creates a pane's window some time after registration. Showing a
    pane whose window does not exist yet returns immediately and shows it on
    a later ``Idling`` event. The wait has no limit while no document is open;
    once one is, it gives up with a warning after
    ``_PENDING_SHOW_TIMEOUT_SECONDS``. Hiding cancels a pending show, whichever
    engine started it.

    Args:
        panel_type_or_id (type | WPFPanel | str): WPFPanel subclass or
            instance, or its UUID.
        state (bool): True to show the panel, False to hide it.

    Raises:
        PyRevitException: The reference is invalid or not registered.
    """
    pane_id = _get_registered_dockable_panel_id(panel_type_or_id)
    if not state:
        _cancel_dockable_panel_show(pane_id)
    if not UI.DockablePane.PaneExists(pane_id):
        if state:
            _defer_dockable_panel_show(pane_id)
        return

    pane = HOST_APP.uiapp.GetDockablePane(pane_id)
    if state:
        pane.Show()
        return
    pane.Hide()


def _get_dockable_panel_id(panel_type_or_id):
    if isinstance(panel_type_or_id, str):
        panel_id = panel_type_or_id
    elif isinstance(panel_type_or_id, type) and issubclass(panel_type_or_id, WPFPanel):
        panel_id = panel_type_or_id.panel_id
    elif isinstance(panel_type_or_id, WPFPanel):
        panel_id = panel_type_or_id.panel_id
    else:
        raise PyRevitException("Given type is not a forms.WPFPanel")
    try:
        return UI.DockablePaneId(coreutils.Guid.Parse(panel_id))
    except framework.System.FormatException:
        raise PyRevitException('Invalid dockable panel id "{}"'.format(panel_id))


def _get_registered_dockable_panel_id(panel_type_or_id):
    pane_id = _get_dockable_panel_id(panel_type_or_id)
    if not UI.DockablePane.PaneIsRegistered(pane_id):
        raise PyRevitException(
            'Panel with id "{}" is not registered'.format(pane_id.Guid)
        )
    return pane_id


def _pending_panel_shows():
    """Return the pending shows shared by every engine in this Revit process.

    Values are token strings, never engine objects, so each engine can see and
    cancel a show another engine deferred. ``coreutils.envvars`` does not
    fit: it stores an engine-specific Python dictionary.
    """
    system = framework.System
    domain = system.AppDomain.CurrentDomain
    pending = domain.GetData(_PENDING_SHOWS_SLOT)
    if pending is None:
        pending = system.Collections.Generic.Dictionary[system.String, system.Object]()
        domain.SetData(_PENDING_SHOWS_SLOT, pending)
    return pending


def _cancel_dockable_panel_show(pane_id):
    _pending_panel_shows().Remove(pane_id.Guid.ToString())


def _defer_dockable_panel_show(pane_id):
    pending = _pending_panel_shows()
    panel_key = pane_id.Guid.ToString()
    if pending.ContainsKey(panel_key):
        return
    token = framework.System.Guid.NewGuid().ToString()
    pending[panel_key] = token
    uiapp = HOST_APP.uiapp
    waited = [0.0]
    last_tick = [time.time()]

    def is_current():
        return pending.ContainsKey(panel_key) and pending[panel_key] == token

    def stop():
        uiapp.Idling -= show_when_created
        if is_current():
            pending.Remove(panel_key)

    def show_when_created(sender, args):
        if not is_current():
            uiapp.Idling -= show_when_created
            return
        if UI.DockablePane.PaneExists(pane_id):
            stop()
            _show_deferred_pane(uiapp, pane_id)
            return
        now = time.time()
        if getattr(uiapp, "ActiveUIDocument", None) is not None:
            waited[0] += now - last_tick[0]
        last_tick[0] = now
        if waited[0] >= _PENDING_SHOW_TIMEOUT_SECONDS:
            stop()
            mlogger.warning(
                "Dockable panel %s was not created within %s seconds of a "
                "document being open; not shown.",
                panel_key,
                _PENDING_SHOW_TIMEOUT_SECONDS,
            )

    uiapp.Idling += show_when_created


def _show_deferred_pane(uiapp, pane_id):
    try:
        uiapp.GetDockablePane(pane_id).Show()
    except Exception as error:
        mlogger.error("Could not show dockable panel %s: %s", pane_id.Guid, error)
