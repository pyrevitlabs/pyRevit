"""
Revit Python Wrapper
github.com/gtalarico/revitpythonwrapper
revitpythonwrapper.readthedocs.io

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

Copyright 2017 Gui Talarico

"""

__title__ = 'revitpythonwrapper'
__version__ = '1.0.0'
__maintainer__ = ['Gui Talarico', 'Ehsan Iran-Nejad']
__license__ = 'MIT'
__contact__ = 'github.com/gtalarico/revitpythonwrapper'


# Basic services for sub-modules -----------------------------------------------

# determining if rpw is running under document generator (sphinx)
try:
    # noinspection PyUnresolvedReferences
    __sphinx__
    DOC_MODE = True
except:
    DOC_MODE = False


# determining if rpw is running under revitpythonshell(RPS)
try:
    # noinspection PyUnresolvedReferences
    global __message__
    RPS_MODE = True
except:
    RPS_MODE = False


# determining if rpw is running under pyRevit,
# in that case, collect command name and path
try:
    # noinspection PyUnresolvedReferences
    __ipyengine__
    PYREVIT_MODE = True
    # noinspection PyUnresolvedReferences
    PYREVIT_CMDNAME = __commandname__
    # noinspection PyUnresolvedReferences
    PYREVIT_CMDPATH = __commandpath__
except:
    PYREVIT_MODE = False
    PYREVIT_CMDNAME = PYREVIT_CMDPATH = None


from rpw.exceptions import *

# rpw configurations
# noinspection PyUnresolvedReferences
import rpw.utils.config as config

# logging facilities
# noinspection PyUnresolvedReferences
from rpw.utils.logger import get_logger

# Interface to host api, app and document access -------------------------------
# noinspection PyUnresolvedReferences
from rpw.hostapp import HOST_APP, ASSEMBLY_FILE_TYPE
# noinspection PyUnresolvedReferences
from rpw.hostapp import DB, UI, HOST_API_NAMESPACE
# noinspection PyUnresolvedReferences
from rpw.hostapp import doc, uidoc, all_docs

# base wrappers
# noinspection PyUnresolvedReferences
from rpw.base import BaseObject, BaseObjectWrapper, BaseEnumWrapper

# And now exposing rpw api to outside ------------------------------------------
# noinspection PyUnresolvedReferences
from rpw.db import *


if RPS_MODE:
    # noinspection PyUnresolvedReferences
    import rpw.geom as geom


    # cleanups of internal imports for a clean user interface
    del(exceptions)
    del(hostapp, base, db, DOC_MODE)
    del(BaseObject, BaseObjectWrapper, BaseEnumWrapper)
    del(HOST_APP, HOST_API_NAMESPACE)
    del(PYREVIT_CMDNAME, PYREVIT_CMDPATH)
