from .exceptions import PyRevitUnknownAssemblyError
from ._parser import get_installed_packages
from ._assemblies import create_assembly
from ._ui import update_revit_ui


def load():
    for parsed_pkg in get_installed_packages():
        try:
            pkg_asm_location = create_assembly(parsed_pkg)
            update_revit_ui(parsed_pkg, pkg_asm_location)
        except PyRevitUnknownAssemblyError as err:
            raise err


# todo: session object will have all the functionality that a user needs e.g. providing a list of installed packages, handling ui, and others
def get_this_command():
    pass

