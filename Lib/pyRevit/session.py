""" Module name: session.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
This module provide a series of functions to create and manage a pyRevit session under Revit.
Each time Revit is run, pyRevit creates a session and will create buttons in Revit ui.
Each pyRevit session will have its own .dll and log file.
"""

from .exceptions import PyRevitUnknownAssemblyError
from ._parser import get_installed_packages             # get_installed_packages() handles parsing the script libraries
from ._assemblies import create_assembly                # create_assembly() creates the dll assembly for given commands
from ._ui import update_revit_ui, ExistingPyRevitUI     # update_revit_ui() handles ui creation for given commands


# ----------------------------------------------------------------------------------------------------------------------
def load():
    """Handles loading/reloading of the pyRevit addin and extension packages.
    To create a proper ui, pyRevit needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through private interactions with ._parser and ._ui

    Usage Example:
        import pyRevit.session as current_session
        current_session.load()
    """
    # for every package of installed packages
    # get_installed_packages() will read from cache and handles caches internally. viva Law of Demeter.
    # parser, assembly maker, and ui creator all understand ._commandtree classes.
    # this function only moderates the communication and handles errors.
    for parsed_pkg in get_installed_packages():
        try:
            # create a dll assembly
            pkg_asm_location = create_assembly(parsed_pkg)
            # and update ui (needs the assembly to link button actions to commands saved in the dll)
            update_revit_ui(parsed_pkg, pkg_asm_location)
        # and properly handle any exceptions
        except PyRevitUnknownAssemblyError as err:
            raise err
        # todo handle UI exceptions here


# todo: session object will have all the functionality for the user to interact with the session
# todo: e.g. providing a list of installed packages, handling ui, and others
# todo: user is not expected to use _cache, _parser, _commandtree, _assemblies, or _ui
# ----------------------------------------------------------------------------------------------------------------------
def get_this_command():
    """Returns read only info about the caller python script.
    Example:
        this_script = pyRevit.session.get_this_command()
        print(this_script.script_file_address)
    """
    # todo
    pass


def current_ui():
    """Revit UI Wrapper class for interacting with current pyRevit UI.
    Returned class provides min required functionality for user interaction
    Example:
        current_ui = pyRevit.session.current_ui()
        this_script = pyRevit.session.get_this_command()
        current_ui.update_button_icon(this_script, new_icon)
    """
    return ExistingPyRevitUI()