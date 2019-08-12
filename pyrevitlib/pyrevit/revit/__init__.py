import types
import sys

from pyrevit import EXEC_PARAMS, HOST_APP
from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB, UI

#pylint: disable=W0401
from pyrevit.revit.db import *
from pyrevit.revit.db import query
from pyrevit.revit.db import create
from pyrevit.revit.db import update
from pyrevit.revit.db import ensure
from pyrevit.revit.db import delete
from pyrevit.revit.db.transaction import *
from pyrevit.revit.journals import *
from pyrevit.revit.selection import *
from pyrevit.revit.ui import *
from pyrevit.revit import report
from pyrevit.revit import files
from pyrevit.revit import serverutils
from pyrevit.revit import geom
from pyrevit.revit import units


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def get_imported_symbol(symbol_name):
    return globals().get(symbol_name, None)


class RevitWrapper(types.ModuleType):
    def __init__(self):
        pass

    def __getattribute__(self, attr_name):
        attr = get_imported_symbol(attr_name)
        return attr or object.__getattribute__(self, attr_name)

    def __getattr__(self, attr_name):
        attr = get_imported_symbol(attr_name)
        if not attr:
            raise AttributeError('\'module\' object has no attribute \'{}\''
                                 .format(attr_name))
        return attr

    @property
    def uidoc(self):
        return HOST_APP.uidoc

    @property
    def doc(self):
        return HOST_APP.doc

    @property
    def docs(self):
        return HOST_APP.docs

    @property
    def active_view(self):
        return HOST_APP.active_view

    @active_view.setter
    def active_view(self, value):
        HOST_APP.active_view = value

    @property
    def servers(self):
        return HOST_APP.available_servers

    @staticmethod
    def get_project_info():
        mlogger.deprecate('Method revit.get_project_info() is deprecated. '
                          'Use revit.query.get_project_info() instead.')
        return query.get_project_info()


if not EXEC_PARAMS.doc_mode:
    sys.modules[__name__] = RevitWrapper()
