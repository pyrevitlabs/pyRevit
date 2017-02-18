from pyrevit import HOST_APP

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Selection import ObjectType


class SelectionUtils:
    def __init__(self, document, uidocument):
        self._doc = document
        self._uidoc = uidocument
        self._uidoc_selection = self._uidoc.Selection

    def pick_element(self, pick_message=''):
        try:
            return doc.GetElement(self._uidoc_selection.PickObject(ObjectType.Element, pick_message))
        except:
            return None


class CurrentElementSelection:
    def __init__(self, document, uidocument):
        self._doc = document
        self._uidoc = uidocument
        self._uidoc_selection = self._uidoc.Selection

        self.element_ids = list(self._uidoc_selection.GetElementIds())
        self.elements = [self._doc.GetElement(el_id) for el_id in self.element_ids]

        self.count = len(self.element_ids)
        self.first = self.last = None
        if self.count > 0:
            self.first = self.elements[0]
            self.last = self.elements[self.count-1]

        self.utils = SelectionUtils(self._doc, self._uidoc)

    @property
    def is_empty(self):
        return len(self.elements) == 0


doc = uidoc = selection = None
try:
    doc = HOST_APP.uiapp.ActiveUIDocument.Document
    uidoc = HOST_APP.uiapp.ActiveUIDocument
    all_docs = HOST_APP.uiapp.Application.Documents
    selection = CurrentElementSelection(doc, uidoc)
except:
    pass
