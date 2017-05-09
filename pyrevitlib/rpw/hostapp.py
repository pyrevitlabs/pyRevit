# noinspection PyUnresolvedReferences
import clr
clr.AddReference('System')
# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


ASSEMBLY_FILE_TYPE = 'dll'


class _HostApplication:
    """Contains current host version and provides comparison functions."""
    def __init__(self):
        # define HOST_SOFTWARE
        try:
            # noinspection PyUnresolvedReferences
            self.uiapp = __revit__
        except Exception:
            raise Exception('Critical Error: Host software is not supported. '
                            '(__revit__ handle is not available)')

    @property
    def version(self):
        return self.uiapp.Application.VersionNumber

    @property
    def version_name(self):
        return self.uiapp.Application.VersionName

    @property
    def build(self):
        return self.uiapp.Application.VersionBuild

    @property
    def username(self):
        """Return the username from Revit API (Application.Username)"""
        uname = self.uiapp.Application.Username
        uname = uname.split('@')[0]  # if username is email
        # removing dots since username will be used in file naming
        uname = uname.replace('.', '')
        return uname

    @property
    def proc(self):
        return Process.GetCurrentProcess()

    @property
    def proc_id(self):
        return Process.GetCurrentProcess().Id

    @property
    def proc_name(self):
        return Process.GetCurrentProcess().ProcessName

    @property
    def proc_screen(self):
        clr.AddReferenceByPartialName('System.Windows.Forms')
        # noinspection PyUnresolvedReferences
        from System.Windows.Forms import Screen
        return Screen.FromHandle(Process.GetCurrentProcess().MainWindowHandle)

    def is_newer_than(self, version):
        return int(self.version) > int(version)

    def is_older_than(self, version):
        return int(self.version) < int(version)


HOST_APP = _HostApplication()


import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
# noinspection PyUnresolvedReferences
import Autodesk.Revit.DB as DB
# noinspection PyUnresolvedReferences
import Autodesk.Revit.UI as UI

HOST_API_NAMESPACE = 'Autodesk.Revit'


doc = HOST_APP.uiapp.ActiveUIDocument.Document
uidoc = HOST_APP.uiapp.ActiveUIDocument
all_docs = HOST_APP.uiapp.Application.Documents


def docprovider(orig_obj):
    global doc
    global uidoc
    global all_docs

    # if given object is a function, wrap it in func_doc_provider
    if hasattr(orig_obj, '__closure__'):
        def func_doc_provider(*args, **kwargs):
            orig_obj(*args, **kwargs)

        return func_doc_provider
    # if given object is a class, create a dervided class and add doc attribute
    else:
        class DerivedDocProvider(orig_obj):
            def __init__(self, *args, **kwargs):
                self.doc = doc
                self.uidoc = uidoc
                self.all_docs
                orig_obj.__init__(self, *args, **kwargs)

        return DerivedDocProvider
