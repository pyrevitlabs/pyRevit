""" Document Wrapper """


class Document(BaseObjectWrapper):
    """Document Application Wrapper
    Autodesk.Revit.UI.UIDocument
    """

    _revit_object_class = UI.UIDocument

    def load_family(self, filepath):
        raise NotImplemented

    def close(self):
        raise NotImplemented

    def __init__(self):
        raise NotImplemented
