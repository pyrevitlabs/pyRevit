# encoding: utf-8
"""Reusable WPF forms for pyRevit.

Examples:
    ```python
    from pyrevit.forms import WPFWindow
    ```
"""

import re
import sys
import os
import os.path as op
import string
from collections import OrderedDict
import threading
import datetime
import webbrowser

from pyrevit import HOST_APP, EXEC_PARAMS, DOCS, BIN_DIR
from pyrevit import PyRevitCPythonNotSupported, PyRevitException
from pyrevit.compat import IRONPY
from pyrevit.compat import safe_strtype, get_elementid_value_func
from pyrevit._perf import mark as _perfmark

_perfmark("pyrevit.forms._ipy:entry")

if not IRONPY:
    raise PyRevitCPythonNotSupported("pyrevit.forms")

from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import colors
from pyrevit.coreutils import envvars

_perfmark("pyrevit.forms._ipy:after coreutils+logger+colors")
from pyrevit import framework
from pyrevit.framework import System
from pyrevit.framework import Threading
from pyrevit.framework import Interop
from pyrevit.framework import Input
from pyrevit.framework import wpf, Forms, Controls, Documents, Media
from pyrevit.framework import CPDialogs
from pyrevit.framework import ComponentModel
from pyrevit.framework import ObservableCollection
from pyrevit.framework import Uri, UriKind, ResourceDictionary

_perfmark("pyrevit.forms._ipy:after framework re-imports")
from pyrevit.api import AdWindows

_perfmark("pyrevit.forms._ipy:after pyrevit.api.AdWindows")
from pyrevit.labs import Common
from pyrevit import revit, UI, DB

_perfmark("pyrevit.forms._ipy:after `from pyrevit import revit, UI, DB`")
from pyrevit.forms import utils
from pyrevit.forms import toaster

_perfmark("pyrevit.forms._ipy:after forms.utils + forms.toaster")
from pyrevit import versionmgr

_perfmark("pyrevit.forms._ipy:after pyrevit.versionmgr")
from pyrevit.userconfig import user_config

_perfmark("pyrevit.forms._ipy:after `from pyrevit.userconfig import user_config`")

import pyevent

_perfmark("pyrevit.forms._ipy:after pyevent")

import Autodesk.Windows.ComponentManager
import Autodesk.Internal.InfoCenter

_perfmark("pyrevit.forms._ipy:after Autodesk.Windows/Internal")


from .base import (
    DEFAULT_CMDSWITCHWND_WIDTH,
    DEFAULT_INPUTWINDOW_HEIGHT,
    DEFAULT_INPUTWINDOW_WIDTH,
    DEFAULT_RECOGNIZE_ACCESS_KEY,
    DEFAULT_SEARCHWND_HEIGHT,
    DEFAULT_SEARCHWND_WIDTH,
    THEME_XAML_FILE,
    WPFWindow,
    WPF_COLLAPSED,
    WPF_HIDDEN,
    WPF_VISIBLE,
    WindowToggler,
    XAML_FILES_DIR,
    _WPFMixin,
    _argb,
    _background_property,
    _colorref,
    _contrast_ratio,
    _foreground_property,
    _is_authored_value,
    _relative_luminance,
    _resolve_xaml_source,
    _srgb_component,
    _walk_logical_tree,
    is_dark_theme,
)
from .dialogs import (
    GetValueWindow,
    TemplateUserInputWindow,
    ask_for_date,
    ask_for_number_slider,
    ask_for_string,
    ask_for_unique_string,
)
from .native import (
    alert,
    alert_ifnot,
    pick_excel_file,
    pick_file,
    pick_folder,
    save_excel_file,
    save_file,
)


from .reactive import (
    reactive,
    TemplateListItem,
    ParamDef,
    Reactive,
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
    _make_param_def,
    _get_preselect_names,
    RevisionOption,
    SheetOption,
    _get_view_type_label,
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
from .native import ask_for_color
from .dialogs import ask_for_one_item

__all__ = [
    "AdWindows",
    "Autodesk",
    "BIN_DIR",
    "CPDialogs",
    "CommandSwitchWindow",
    "Common",
    "ComponentModel",
    "Controls",
    "DB",
    "DEFAULT_CMDSWITCHWND_WIDTH",
    "DEFAULT_INPUTWINDOW_HEIGHT",
    "DEFAULT_INPUTWINDOW_WIDTH",
    "DEFAULT_RECOGNIZE_ACCESS_KEY",
    "DEFAULT_SEARCHWND_HEIGHT",
    "DEFAULT_SEARCHWND_WIDTH",
    "DOCS",
    "Documents",
    "EXEC_PARAMS",
    "FamilyParamOption",
    "Forms",
    "GetValueWindow",
    "HOST_APP",
    "IRONPY",
    "Input",
    "Interop",
    "LevelOption",
    "Media",
    "ObservableCollection",
    "OrderedDict",
    "ParamDef",
    "ProgressBar",
    "PyRevitCPythonNotSupported",
    "PyRevitException",
    "Reactive",
    "ResourceDictionary",
    "RevisionOption",
    "SearchPrompt",
    "SelectFromList",
    "SheetOption",
    "System",
    "THEME_XAML_FILE",
    "TemplateListItem",
    "TemplatePromptBar",
    "TemplateUserInputWindow",
    "Threading",
    "UI",
    "Uri",
    "UriKind",
    "ViewOption",
    "WPFPanel",
    "WPFWindow",
    "WPF_COLLAPSED",
    "WPF_HIDDEN",
    "WPF_VISIBLE",
    "WarningBar",
    "WindowToggler",
    "XAML_FILES_DIR",
    "activate_open_window",
    "alert",
    "alert_ifnot",
    "ask_for_color",
    "ask_for_date",
    "ask_for_number_slider",
    "ask_for_one_item",
    "ask_for_string",
    "ask_for_unique_string",
    "ask_to_use_selected",
    "check_familydoc",
    "check_graphicalview",
    "check_modeldoc",
    "check_modelview",
    "check_selection",
    "check_viewtype",
    "check_workshared",
    "close_dockable_panel",
    "colors",
    "coreutils",
    "datetime",
    "envvars",
    "framework",
    "get_dockable_panel",
    "get_elementid_value_func",
    "get_logger",
    "inform_wip",
    "is_dark_theme",
    "is_registered_dockable_panel",
    "mlogger",
    "op",
    "open_dockable_panel",
    "os",
    "pick_excel_file",
    "pick_file",
    "pick_folder",
    "pyevent",
    "re",
    "reactive",
    "register_dockable_panel",
    "result_item_result_clicked",
    "revit",
    "safe_strtype",
    "save_excel_file",
    "save_file",
    "select_family_parameters",
    "select_image",
    "select_levels",
    "select_open_docs",
    "select_parameters",
    "select_revisions",
    "select_schedules",
    "select_sheets",
    "select_swatch",
    "select_titleblocks",
    "select_views",
    "select_viewtemplates",
    "show_balloon",
    "string",
    "sys",
    "threading",
    "toast",
    "toaster",
    "toggle_dockable_panel",
    "user_config",
    "utils",
    "versionmgr",
    "webbrowser",
    "wpf",
]

mlogger = get_logger(__name__)


# https://gui-at.blogspot.com/2009/11/inotifypropertychanged-in-ironpython.html


def activate_open_window(envvar):
    """Bring a modeless window left open by an earlier run to the front.

    Single-instance guard for modeless tools: the tool stores its window
    under ``envvar`` with ``script.set_envvar`` when it opens it, and calls
    this on every run before creating a new one. A minimized window is
    restored before activation; a hidden one is left hidden.

    Openness is judged by the window's native handle, which WPF releases on
    close, not by ``IsLoaded``, which stays True after ``Close()``. Callers
    therefore need not clear ``envvar`` in their ``Closed`` handler.

    Args:
        envvar (str): pyRevit environment variable holding the window.

    Returns:
        (bool): True when a window already exists, meaning the caller must
            not open another. It does not promise the window is now in front:
            Windows may refuse the foreground request, and a hidden window
            stays hidden. False otherwise; a stale (closed) reference is
            cleared.

    Examples:
        ```python
        from pyrevit import forms, script

        if not forms.activate_open_window("MYTOOL_WINDOW"):
            window = MyToolWindow("MyTool.xaml")
            script.set_envvar("MYTOOL_WINDOW", window)
            window.show()
        ```
    """
    window = envvars.get_pyrevit_env_var(envvar)
    if window is None:
        return False
    try:
        is_open = Interop.WindowInteropHelper(window).Handle != framework.IntPtr.Zero
    except Exception:
        is_open = False
    if not is_open:
        envvars.set_pyrevit_env_var(envvar, None)
        return False
    if window.IsVisible:
        if window.WindowState == framework.Windows.WindowState.Minimized:
            window.WindowState = framework.Windows.WindowState.Normal
        window.Activate()
    return True


class WPFPanel(_WPFMixin, framework.Windows.Controls.Page):
    r"""WPF panel base class for all pyRevit dockable panels.

        Subclass this, set the three required class attributes, then register
        and open the panel through the module-level helpers.

        Use self.logger and self.output instead of using script.get_logger() and script.get_output()
        to ensure correct titles in the output window.

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
        """Initialize WPF panel and resources."""
        if not self.panel_id:
            raise PyRevitException('"panel_id" class attribute is not set')
        if not self.panel_source:
            raise PyRevitException('"panel_source" class attribute is not set')
        if not self.panel_title:
            raise PyRevitException('"panel_title" class attribute is not set')

        self.load_xaml(self.panel_source)

    def load_xaml(self, xaml_source, literal_string=False):
        """Load the panel XAML file.

        Supports the full locale-fallback chain (see _resolve_xaml_source) and
        can accept raw XAML content via literal_string, matching WPFWindow.

        Args:
            xaml_source (str): XAML content string or file path.
            literal_string (bool): True when xaml_source is raw content.
        """
        _WPFMixin.setup_resources(self, resolve_theme=self.resolve_theme)
        self.merge_resource_dict(THEME_XAML_FILE)
        if not literal_string:
            xaml_path, pending_resource_merge = _resolve_xaml_source(xaml_source)
            # merge before LoadComponent so resources are available during parse
            if pending_resource_merge:
                self.merge_resource_dict(pending_resource_merge)
            wpf.LoadComponent(self, xaml_path)
        else:
            wpf.LoadComponent(self, framework.StringReader(xaml_source))
        self.apply_contrast_foregrounds()
        self.thread_id = framework.get_current_thread_id()
        if self.resolve_theme:
            self._subscribe_theme_changed()

    def _get_panel_output(self):
        """Get current output window and keep its title in sync with panel_title."""
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


class _WPFPanelProvider(UI.IDockablePaneProvider):
    """Internal panel provider for dockable panels."""

    def __init__(self, panel_type, default_visible=True):
        self._panel_type = panel_type
        self._default_visible = default_visible
        self.panel = self._panel_type()

    def SetupDockablePane(self, data):
        """Configure DockablePaneProviderData from the panel type's class attributes."""
        data.FrameworkElement = self.panel
        data.VisibleByDefault = self._default_visible

        if self._panel_type.initial_state is not None:
            data.InitialState = self._panel_type.initial_state

        if self._panel_type.editor_interaction is not None:
            data.EditorInteraction = self._panel_type.editor_interaction

        if self._panel_type.contextual_help is not None:
            data.ContextualHelp = self._panel_type.contextual_help


def is_registered_dockable_panel(panel_type):
    """Check if dockable panel is already registered.

    Args:
        panel_type (forms.WPFPanel): dockable panel type
    """
    panel_uuid = coreutils.Guid.Parse(panel_type.panel_id)
    dockable_panel_id = UI.DockablePaneId(panel_uuid)
    return UI.DockablePane.PaneIsRegistered(dockable_panel_id)


def register_dockable_panel(panel_type, default_visible=True):
    """Register a dockable panel with Revit and return its instance.

    This function creates a provider for the given panel type, registers the
    corresponding dockable pane with Revit, and returns the live WPF panel
    instance managed by that provider.

    Args:
        panel_type (forms.WPFPanel): dockable panel type
        default_visible (bool, optional):
            Whether the panel should be visible by default when registered.

    Returns:
        forms.WPFPanel: The live panel instance created during registration.
    """
    if not isinstance(panel_type, type) or not issubclass(panel_type, WPFPanel):
        raise PyRevitException("Dockable pane must be a subclass of forms.WPFPanel")

    try:
        panel_uuid = coreutils.Guid.Parse(panel_type.panel_id)
    except System.FormatException:
        raise PyRevitException(
            'Invalid dockable panel id "{}"'.format(panel_type.panel_id)
        )
    dockable_panel_id = UI.DockablePaneId(panel_uuid)
    panel_provider = _WPFPanelProvider(panel_type, default_visible)
    HOST_APP.uiapp.RegisterDockablePane(
        dockable_panel_id, panel_type.panel_title, panel_provider
    )

    return panel_provider.panel


def get_dockable_panel(panel_type_or_id):
    """Retrieve the Revit dockable pane handle for a registered panel.

    Args:
        panel_type_or_id (forms.WPFPanel | str):
            dockable panel type (subclass of forms.WPFPanel) or panel id string
            corresponding to the Revit dockable pane id.

    Returns:
        UI.DockablePane: the live panel pane handle.

    Raises:
        PyRevitException: if the panel id is not registered with Revit.
    """
    dpanel_id = None
    if isinstance(panel_type_or_id, str):
        try:
            panel_id = coreutils.Guid.Parse(panel_type_or_id)
        except System.FormatException:
            raise PyRevitException(
                'Invalid dockable panel id "{}"'.format(panel_type_or_id)
            )
        dpanel_id = UI.DockablePaneId(panel_id)
    elif isinstance(panel_type_or_id, type) and issubclass(panel_type_or_id, WPFPanel):
        try:
            panel_id = coreutils.Guid.Parse(panel_type_or_id.panel_id)
        except System.FormatException:
            raise PyRevitException(
                'Invalid dockable panel id "{}"'.format(panel_type_or_id.panel_id)
            )
        dpanel_id = UI.DockablePaneId(panel_id)
    else:
        raise PyRevitException("Given type is not a forms.WPFPanel")

    if dpanel_id:
        if UI.DockablePane.PaneIsRegistered(dpanel_id):
            dockable_panel = HOST_APP.uiapp.GetDockablePane(dpanel_id)
            return dockable_panel
        else:
            raise PyRevitException(
                'Panel with id "%s" is not registered' % panel_type_or_id
            )


def open_dockable_panel(panel_type_or_id):
    """Open previously registered dockable panel.

    Args:
        panel_type_or_id (forms.WPFPanel | str): panel type or id
    """
    toggle_dockable_panel(panel_type_or_id, True)


def close_dockable_panel(panel_type_or_id):
    """Close previously registered dockable panel.

    Args:
        panel_type_or_id (forms.WPFPanel | str): panel type or id
    """
    toggle_dockable_panel(panel_type_or_id, False)


def toggle_dockable_panel(panel_type_or_id, state):
    """Toggle previously registered dockable panel.

    Args:
        panel_type_or_id (forms.WPFPanel | str): panel type or id
        state (bool): True to show the panel, False to hide it.
    """
    dockable_panel = get_dockable_panel(panel_type_or_id)
    if state:
        dockable_panel.Show()
    else:
        dockable_panel.Hide()


_perfmark("pyrevit.forms._ipy:exit (all class defs done)")
