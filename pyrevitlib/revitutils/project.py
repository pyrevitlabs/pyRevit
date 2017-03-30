from pyrevit import HOST_APP


class CurrentProject:
    def __init__(self, document):
        self._doc = document
        self._info=self._doc.ProjectInformation
        self.name = self._info.Name


doc = HOST_APP.uiapp.ActiveUIDocument.Document
uidoc = HOST_APP.uiapp.ActiveUIDocument
all_docs = HOST_APP.uiapp.Application.Documents
project = CurrentProject(doc)

curview = uidoc.ActiveView
