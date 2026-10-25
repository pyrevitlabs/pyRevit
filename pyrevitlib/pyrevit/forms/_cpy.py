"""CPython forms exports, with stable errors for features awaiting migration."""

from pyrevit import PyRevitCPythonNotSupported
from .base import WPFWindow
from .dialogs import (
    TemplateUserInputWindow,
    GetValueWindow,
    ask_for_string,
    ask_for_unique_string,
    ask_for_date,
    ask_for_number_slider,
)
from .native import (
    alert,
    alert_ifnot,
    pick_file,
    pick_folder,
    save_file,
    pick_excel_file,
    save_excel_file,
)

__all__ = [
    "WPFWindow",
    "TemplateUserInputWindow",
    "GetValueWindow",
    "alert",
    "alert_ifnot",
    "SelectFromList",
    "CommandSwitchWindow",
    "ProgressBar",
    "ask_for_string",
    "ask_for_unique_string",
    "ask_for_one_item",
    "ask_for_date",
    "ask_for_number_slider",
    "pick_file",
    "pick_folder",
    "save_file",
    "pick_excel_file",
    "save_excel_file",
    "show_balloon",
    "activate_open_window",
]


def _raise_not_supported(feature_name):
    raise PyRevitCPythonNotSupported(feature_name)


class _NotSupportedBase(object):
    _feature_name = None

    def __init__(self, *args, **kwargs):
        _raise_not_supported(self._feature_name)

    @classmethod
    def _raise(cls, suffix=None):
        feature_name = cls._feature_name
        if suffix:
            feature_name = "{}.{}".format(feature_name, suffix)
        _raise_not_supported(feature_name)


class _UnsupportedWindow(_NotSupportedBase):
    @classmethod
    def show(cls, *args, **kwargs):
        cls._raise("show")


class SelectFromList(_UnsupportedWindow):
    _feature_name = "pyrevit.forms.SelectFromList"


class CommandSwitchWindow(_UnsupportedWindow):
    _feature_name = "pyrevit.forms.CommandSwitchWindow"


class ProgressBar(_NotSupportedBase):
    _feature_name = "pyrevit.forms.ProgressBar"


def ask_for_one_item(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.ask_for_one_item")


def show_balloon(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.show_balloon")


def activate_open_window(*args, **kwargs):
    _raise_not_supported("pyrevit.forms.activate_open_window")
