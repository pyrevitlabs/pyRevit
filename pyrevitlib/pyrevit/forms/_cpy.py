"""CPython forms share behavior with IronPython through the native WPF backend."""

import time

from pyrevit import HOST_APP, UI, PyRevitException, coreutils, framework
from pyrevit.coreutils.logger import get_logger

from . import _backend

from .base import (
    THEME_XAML_FILE,
    WPFWindow,
    WPF_VISIBLE,
    WPF_COLLAPSED,
    WPF_HIDDEN,
    XAML_FILES_DIR,
    is_dark_theme,
    _resolve_xaml_source,
    _WPFMixin,
    WindowToggler,
)
from .backends._cpy import activate_open_window
from .dialogs import (
    TemplateUserInputWindow,
    GetValueWindow,
    ask_for_string,
    ask_for_unique_string,
    ask_for_date,
    ask_for_number_slider,
    ask_for_one_item,
)
from .native import (
    alert,
    alert_ifnot,
    warning,
    pick_folder,
    pick_file,
    save_file,
    pick_excel_file,
    save_excel_file,
    ask_for_color,
)
from .reactive import (
    Reactive,
    reactive,
    TemplateListItem,
    ParamDef,
)
from .listdialog import (
    SelectFromList,
)
from .commanddialog import (
    CommandSwitchWindow,
)
from .promptbars import (
    TemplatePromptBar,
    WarningBar,
    ProgressBar,
)
from .search import (
    SearchPrompt,
)
from .selection import (
    RevisionOption,
    SheetOption,
    ViewOption,
    LevelOption,
    FamilyParamOption,
    select_revisions,
    select_sheets,
    select_views,
    select_levels,
    select_viewtemplates,
    select_schedules,
    select_open_docs,
    select_titleblocks,
    select_swatch,
    select_image,
    select_parameters,
    select_family_parameters,
)
from .checks import (
    check_workshared,
    check_selection,
    check_familydoc,
    check_modeldoc,
    check_modelview,
    check_viewtype,
    check_graphicalview,
    ask_to_use_selected,
    inform_wip,
)
from .notify import (
    result_item_result_clicked,
    show_balloon,
    toast,
)


mlogger = get_logger(__name__)

_panel_providers = {}
_PENDING_SHOWS_SLOT = "pyRevit.forms.pendingDockablePaneShows"
_PENDING_SHOW_TIMEOUT_SECONDS = 60


class WPFPanel(_WPFMixin, _backend.Panel):
    """CPython controller for a Revit dockable-page XAML root.

    Registration remains an explicit Revit-host operation. This class owns the
    page's XAML, resources, named controls and Python event callbacks.
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
        """Load page XAML and apply pyRevit form resources.

        Args:
            xaml_source (str): Path to XAML or raw XAML content.
            literal_string (bool): Whether xaml_source is raw XAML content.
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


def is_registered_dockable_panel(panel_type):
    """Return whether Revit has registered the panel type's stable pane identifier."""
    return UI.DockablePane.PaneIsRegistered(_get_dockable_panel_id(panel_type))


def register_dockable_panel(panel_type, default_visible=True):
    """Register a composed CPython page with Revit's managed pane provider.

    Args:
        panel_type (type): A WPFPanel subclass describing the Revit pane.
        default_visible (bool): Whether Revit initially shows the pane.

    Returns:
        WPFPanel: The controller owning the registered native page.
    """
    if not isinstance(panel_type, type) or not issubclass(panel_type, WPFPanel):
        raise PyRevitException("Dockable pane must be a subclass of forms.WPFPanel")
    pane_id = _get_dockable_panel_id(panel_type)
    panel = panel_type()
    from pyrevit.runtime.types import DockablePaneProvider

    provider = DockablePaneProvider(_backend.unwrap(panel), default_visible)
    if panel.initial_state is not None:
        provider.InitialState = panel.initial_state
    if panel.editor_interaction is not None:
        provider.EditorInteraction = panel.editor_interaction
    if panel.contextual_help is not None:
        provider.ContextualHelp = panel.contextual_help
    HOST_APP.uiapp.RegisterDockablePane(pane_id, panel.panel_title, provider)
    _panel_providers[panel.panel_id] = provider
    return panel


def get_dockable_panel(panel_type_or_id):
    """Return Revit's dockable-pane handle for a registered panel type or UUID."""
    pane_id = _get_registered_dockable_panel_id(panel_type_or_id)
    return HOST_APP.uiapp.GetDockablePane(pane_id)


def open_dockable_panel(panel_type_or_id):
    """Show a previously registered CPython dockable panel.

    See ``toggle_dockable_panel`` for when the pane becomes visible.
    """
    toggle_dockable_panel(panel_type_or_id, True)


def close_dockable_panel(panel_type_or_id):
    """Hide a previously registered CPython dockable panel."""
    toggle_dockable_panel(panel_type_or_id, False)


def toggle_dockable_panel(panel_type_or_id, state):
    """Show or hide a previously registered CPython dockable panel.

    Revit creates a pane's window some time after registration. Showing a
    pane whose window does not exist yet returns immediately and shows it on
    a later ``Idling`` event, or logs a warning and gives up after
    ``_PENDING_SHOW_TIMEOUT_SECONDS``. Hiding cancels such a pending show.

    Args:
        panel_type_or_id (type | str): WPFPanel subclass or its UUID.
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
    """Return the native identifier for a dockable panel reference."""
    if isinstance(panel_type_or_id, str):
        panel_id = panel_type_or_id
    elif isinstance(panel_type_or_id, type) and issubclass(panel_type_or_id, WPFPanel):
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
    """Return the process-wide pending shows, which outlive module reloads."""
    system = framework.System
    domain = system.AppDomain.CurrentDomain
    pending = domain.GetData(_PENDING_SHOWS_SLOT)
    if pending is None:
        pending = system.Collections.Generic.Dictionary[system.String, system.Object]()
        domain.SetData(_PENDING_SHOWS_SLOT, pending)
    return pending


def _cancel_dockable_panel_show(pane_id):
    pending = _pending_panel_shows()
    panel_key = pane_id.Guid.ToString()
    if not pending.ContainsKey(panel_key):
        return
    uiapp, handler = pending[panel_key]
    pending.Remove(panel_key)
    uiapp.Idling -= handler


def _defer_dockable_panel_show(pane_id):
    pending = _pending_panel_shows()
    panel_key = pane_id.Guid.ToString()
    if pending.ContainsKey(panel_key):
        return
    uiapp = HOST_APP.uiapp
    deadline = time.monotonic() + _PENDING_SHOW_TIMEOUT_SECONDS

    def show_when_created(sender, args):
        if UI.DockablePane.PaneExists(pane_id):
            _cancel_dockable_panel_show(pane_id)
            uiapp.GetDockablePane(pane_id).Show()
            return
        if time.monotonic() > deadline:
            _cancel_dockable_panel_show(pane_id)
            mlogger.warning(
                "Dockable panel %s was not created within %s seconds; not shown.",
                panel_key,
                _PENDING_SHOW_TIMEOUT_SECONDS,
            )

    pending[panel_key] = (uiapp, show_when_created)
    uiapp.Idling += show_when_created


__all__ = [
    "WPFWindow",
    "WPFPanel",
    "WPF_VISIBLE",
    "WPF_COLLAPSED",
    "WPF_HIDDEN",
    "XAML_FILES_DIR",
    "is_dark_theme",
    "WindowToggler",
    "TemplateUserInputWindow",
    "GetValueWindow",
    "ask_for_string",
    "ask_for_unique_string",
    "ask_for_date",
    "ask_for_number_slider",
    "ask_for_one_item",
    "alert",
    "alert_ifnot",
    "warning",
    "pick_folder",
    "pick_file",
    "save_file",
    "pick_excel_file",
    "save_excel_file",
    "ask_for_color",
    "Reactive",
    "reactive",
    "TemplateListItem",
    "ParamDef",
    "SelectFromList",
    "CommandSwitchWindow",
    "TemplatePromptBar",
    "WarningBar",
    "ProgressBar",
    "SearchPrompt",
    "RevisionOption",
    "SheetOption",
    "ViewOption",
    "LevelOption",
    "FamilyParamOption",
    "select_revisions",
    "select_sheets",
    "select_views",
    "select_levels",
    "select_viewtemplates",
    "select_schedules",
    "select_open_docs",
    "select_titleblocks",
    "select_swatch",
    "select_image",
    "select_parameters",
    "select_family_parameters",
    "check_workshared",
    "check_selection",
    "check_familydoc",
    "check_modeldoc",
    "check_modelview",
    "check_viewtype",
    "check_graphicalview",
    "ask_to_use_selected",
    "inform_wip",
    "result_item_result_clicked",
    "show_balloon",
    "toast",
    "activate_open_window",
    "is_registered_dockable_panel",
    "register_dockable_panel",
    "get_dockable_panel",
    "open_dockable_panel",
    "close_dockable_panel",
    "toggle_dockable_panel",
]
