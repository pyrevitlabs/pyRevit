import types
import sys

from pyrevit import EXEC_PARAMS, HOST_APP
from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB, UI

from pyrevit.revit.db import *
from pyrevit.revit.journals import *
from pyrevit.revit.selection import *
from pyrevit.revit.transaction import *
from pyrevit.revit.ui import *
from pyrevit.revit import verify


logger = get_logger(__name__)


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
                                 .format(symbol_name))
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
    def activeview(self):
        return HOST_APP.activeview


if not EXEC_PARAMS.doc_mode:
    sys.modules[__name__] = RevitWrapper()
