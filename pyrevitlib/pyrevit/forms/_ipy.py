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
)
from ._common import *  # noqa: F401,F403
from ._common import __all__ as _COMMON_EXPORTS

_LEGACY_EXPORTS = [
    "AdWindows",
    "Autodesk",
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
    "pyevent",
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
    "wpf",
]

__all__ = _COMMON_EXPORTS + _LEGACY_EXPORTS

mlogger = get_logger(__name__)


_perfmark("pyrevit.forms._ipy:exit (all class defs done)")
