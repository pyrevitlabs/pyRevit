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


def DocDecorator(orig_obj):
    global doc

    # if given object is a function, wrap it in FuncDocProvider
    if hasattr(orig_obj, '__closure__'):
        def FuncDocProvider(*args, **kwargs):
            orig_obj(*args, **kwargs)

        return FuncDocProvider
    # if given object is a class, create a dervided class and add doc attribute
    else:
        class DerivedDocProvider(orig_obj):
            def __init__(self, *args, **kwargs):
                self.doc = doc
                orig_obj.__init__(self, *args, **kwargs)

        return DerivedDocProvider
