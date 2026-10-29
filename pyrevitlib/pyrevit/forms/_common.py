"""The engine-neutral public ``pyrevit.forms`` API.

``__all__`` here is the single list of names both engines export. It includes
the engine-neutral names ``pyrevit.forms`` re-exported before the engine split
(constants, pyrevit helpers, framework namespaces and standard modules), so
both engines keep them. The IronPython facade adds only the IronPython-only
legacy names on top; CPython exports exactly this list and reports anything
else as unsupported.

Note:
    This module must stay importable by IronPython 2.7, and ``__all__`` must
    stay a literal list: tooling reads it without importing the module.
"""

import datetime
import os
import os.path as op
import re
import string
import sys
import threading
import webbrowser
from collections import OrderedDict

from pyrevit import HOST_APP, EXEC_PARAMS, DOCS, BIN_DIR
from pyrevit import PyRevitCPythonNotSupported, PyRevitException
from pyrevit import coreutils, framework, revit, versionmgr, UI, DB
from pyrevit.api import AdWindows
from pyrevit.compat import IRONPY, safe_strtype, get_elementid_value_func
from pyrevit.coreutils import colors, envvars
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import System, Threading, Interop, Input
from pyrevit.framework import Forms, Controls, Documents, Media
from pyrevit.framework import CPDialogs, ComponentModel, ObservableCollection
from pyrevit.framework import Uri, UriKind, ResourceDictionary
from pyrevit.labs import Common
from pyrevit.userconfig import user_config

from . import toaster, utils
from .base import (
    DEFAULT_CMDSWITCHWND_WIDTH,
    DEFAULT_INPUTWINDOW_HEIGHT,
    DEFAULT_INPUTWINDOW_WIDTH,
    DEFAULT_RECOGNIZE_ACCESS_KEY,
    DEFAULT_SEARCHWND_HEIGHT,
    DEFAULT_SEARCHWND_WIDTH,
    THEME_XAML_FILE,
)
from .base import (
    WPFWindow,
    WPF_VISIBLE,
    WPF_COLLAPSED,
    WPF_HIDDEN,
    XAML_FILES_DIR,
    is_dark_theme,
    WindowToggler,
    set_data_context,
    activate_open_window,
)
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
from .dockable import (
    WPFPanel,
    is_registered_dockable_panel,
    register_dockable_panel,
    get_dockable_panel,
    open_dockable_panel,
    close_dockable_panel,
    toggle_dockable_panel,
)


mlogger = get_logger(__name__)


__all__ = [
    "WPFWindow",
    "WPFPanel",
    "WPF_VISIBLE",
    "WPF_COLLAPSED",
    "WPF_HIDDEN",
    "XAML_FILES_DIR",
    "is_dark_theme",
    "WindowToggler",
    "set_data_context",
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
    "AdWindows",
    "BIN_DIR",
    "CPDialogs",
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
    "Forms",
    "HOST_APP",
    "IRONPY",
    "Input",
    "Interop",
    "Media",
    "ObservableCollection",
    "OrderedDict",
    "PyRevitCPythonNotSupported",
    "PyRevitException",
    "ResourceDictionary",
    "System",
    "THEME_XAML_FILE",
    "Threading",
    "UI",
    "Uri",
    "UriKind",
    "colors",
    "coreutils",
    "datetime",
    "envvars",
    "framework",
    "get_elementid_value_func",
    "get_logger",
    "mlogger",
    "op",
    "os",
    "re",
    "revit",
    "safe_strtype",
    "string",
    "sys",
    "threading",
    "toaster",
    "user_config",
    "utils",
    "versionmgr",
    "webbrowser",
]
