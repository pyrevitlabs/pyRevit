from .exceptions import PyRevitUnknownAssemblyError
from ._parser import get_installed_packages
from ._assemblies import create_assembly
from ._ui import update_revit_ui, ExistingPyRevitUI


# ----------------------------------------------------------------------------------------------------------------------
def load():
    for parsed_pkg in get_installed_packages():
        try:
            pkg_asm_location = create_assembly(parsed_pkg)
            update_revit_ui(parsed_pkg, pkg_asm_location)
        except PyRevitUnknownAssemblyError as err:
            raise err
        # todo handle UI exceptions here


# todo: session object will have all the functionality for the user to interact with the session
# todo: e.g. providing a list of installed packages, handling ui, and others
# todo: user is not expected to use _cache, _parser, _commandtree, _assemblies, or _ui
# ----------------------------------------------------------------------------------------------------------------------
def get_this_command():
    """Returns read only info about the caller script."""
    # todo
    pass


def current_ui():
    """Current read-only state of the ui constructed by pyRevit.
    Returned class provides min required functionality for user interaction
    e.g. A script can find its button and update the icon as necessary.
    """
    return ExistingPyRevitUI()