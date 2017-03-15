from pyrevit import HOST_APP
from pyrevit.coreutils.logger import get_logger

from revitutils.selectutils import SelectionUtils


logger = get_logger(__name__)


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


try:
    doc = HOST_APP.uiapp.ActiveUIDocument.Document
    uidoc = HOST_APP.uiapp.ActiveUIDocument
    all_docs = HOST_APP.uiapp.Application.Documents
    selection = CurrentElementSelection(doc, uidoc)
except Exception as ru_setup_err:
    logger.error('Error setting up revitutils | {}'.format(ru_setup_err))
