"""CPython forms share behavior with IronPython through the native WPF backend."""

from pyrevit import PyRevitException, framework

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
]
