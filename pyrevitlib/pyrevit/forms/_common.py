"""The engine-neutral public ``pyrevit.forms`` API.

``__all__`` here is the single list of names both engines export. The
IronPython facade adds only its legacy names on top; CPython exports exactly
this list and reports anything else as unsupported.

Note:
    This module must stay importable by IronPython 2.7, and ``__all__`` must
    stay a literal list: tooling reads it without importing the module.
"""

from . import _backend

from .base import (
    WPFWindow,
    WPF_VISIBLE,
    WPF_COLLAPSED,
    WPF_HIDDEN,
    XAML_FILES_DIR,
    is_dark_theme,
    WindowToggler,
    set_data_context,
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

activate_open_window = _backend.activate_open_window


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
]
