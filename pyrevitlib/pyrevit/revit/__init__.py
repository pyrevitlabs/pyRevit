import types
import sys

from pyrevit import HOST_APP
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


class RevitWrapper(types.ModuleType):
    def __init__(self):
        pass

    def __getattr__(self, attr_name):
        gbls = globals()
        if attr_name in gbls:
            return gbls[attr_name]
        else:
            raise AttributeError('\'module\' object has no attribute \'{}\''
                                 .format(attr_name))

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


sys.modules[__name__] = RevitWrapper()
