from .exceptions import PyRevitUnknownAssemblyError
from ._parser import get_installed_packages
from ._assemblies import create_assembly
from ._ui import create_ui, update_ui


def _get_active_sessions():
    pass


def _is_active():
    return _get_active_sessions() > 0


def load():
    for parsed_pkg in get_installed_packages():
        try:
            create_assembly(parsed_pkg)
            if _is_active():
                update_ui(parsed_pkg)
            else:
                create_ui(parsed_pkg)
        except PyRevitUnknownAssemblyError as err:
            raise err


# todo: session object will have all the functionality that a user needs e.g. providing a list of installed packages, handling ui, and others
def get_this_command():
    pass

