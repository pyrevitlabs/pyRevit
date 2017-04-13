from pyrevit import HOST_APP


class CurrentProject:
    def __init__(self, document):
        self._doc = document
        self._info = self._doc.ProjectInformation
        self.name = self._info.Name
        self.location = self._doc.PathName


doc = HOST_APP.uiapp.ActiveUIDocument.Document
uidoc = HOST_APP.uiapp.ActiveUIDocument
all_docs = HOST_APP.uiapp.Application.Documents
project = CurrentProject(doc)

curview = uidoc.ActiveView


def DocDecorator(orig_cls):
    global doc

    class DerivedDocProvider(orig_cls):
        def __init__(self, *args, **kwargs):
            self.doc = doc
            orig_cls.__init__(self, *args, **kwargs)

    return DerivedDocProvider
