import types
import sys

from pyrevit import HOST_APP
from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB, UI

from pyrevit.revit import db
from pyrevit.revit import journals
from pyrevit.revit import selection
from pyrevit.revit import transaction
from pyrevit.revit import ui


logger = get_logger(__name__)


class RevitWrapper(types.ModuleType):
    def __init__(self):
        self.ElementWrapper = db.ElementWrapper
        self.get_project_info = db.get_project_info

        self.get_journals_folder = journals.get_journals_folder
        self.get_current_journal_file = journals.get_current_journal_file

        self.pick_element = selection.pick_element
        self.pick_elementpoint = selection.pick_elementpoint
        self.pick_edge = selection.pick_edge
        self.pick_face = selection.pick_face
        self.pick_linked = selection.pick_linked
        self.pick_elements = selection.pick_elements
        self.pick_elementpoints = selection.pick_elementpoints
        self.pick_edges = selection.pick_edges
        self.pick_faces = selection.pick_faces
        self.pick_linkeds = selection.pick_linkeds
        self.pick_point = selection.pick_point
        self.get_selection = selection.get_selection

        self.Transaction = transaction.Transaction
        self.DryTransaction = transaction.DryTransaction
        self.TransactionGroup = transaction.TransactionGroup
        self.carryout = transaction.carryout

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
