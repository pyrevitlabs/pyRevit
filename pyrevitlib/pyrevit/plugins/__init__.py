from pyrevit import PyRevitException


class PyRevitPluginAlreadyInstalledException(PyRevitException):
    def __init__(self, ext_pkg):
        self.ext_pkg = ext_pkg
        PyRevitException(self)


class PyRevitPluginNoInstallLinkException(PyRevitException):
    pass


class PyRevitPluginRemoveException(PyRevitException):
    pass


PLUGIN_EXT_DEF_FILE = 'extensions.json'


import pyrevit.plugins.extpackages
import pyrevit.plugins.ipymodules
