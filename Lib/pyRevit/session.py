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
Description:
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This module provide a series of functions to create and manage a pyRevit session under Revit (using the 4 modules).
Each time Revit is run, the loader script imports pyRevit.session and creates a session. The session (this module)
then calls the parser, assembly maker, and lastly ui maker to create the buttons in Revit.
Each pyRevit session will have its own .dll and log file.
"""

from .logger import logger

from ._cache import _is_cache_valid, _get_cached_package, _update_cache
from ._parser import _get_installed_packages, _get_parsed_package
from ._assemblies import _create_assembly
from ._ui import _update_revit_ui

from usagedata import _archive_script_usage_logs

def load_from(root_dir):
    """Handles loading/reloading of the pyRevit addin and extension packages.
    To create a proper ui, pyRevit needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through private interactions with ._parser and ._ui

    Usage Example:
        import pyRevit.session as current_session
        current_session.load()
    """

    # for every package of installed packages, create an assembly, and create a ui
    # parser, assembly maker, and ui creator all understand ._commandtree classes. (They speak the same language)
    # the session.load() function (this function) only moderates the communication and handles errors.
    # Session, creates an independent dll and ui for every package. This isolates other packages from any errors that
    # might occur when setting up a package.

    # archive previous sessions logs
    _archive_script_usage_logs()

    # get_installed_packages() returns a list of discovered packages in root_dir
    for pkg_info in _get_installed_packages(root_dir):
        # test if cache is valid for this package
        # it might seem unusual to create a package and then re-load it from cache but minimum information
        # about the package needs to be passed to the cache module for proper hash calculation and package recovery.
        # Also package object is very small and its creation doesn't add much overhead.
        if _is_cache_valid(pkg_info):
            # if yes, load the cached package and add the cached tabs to the new package
            logger.debug('Cache is valid for: {}'.format(pkg_info))
            logger.debug('Loading package from cache...')
            package = _get_cached_package(pkg_info)

        else:
            logger.debug('Cache is NOT valid for: {}'.format(pkg_info))
            package = _get_parsed_package(pkg_info)

            # update cache with newly parsed package and its components
            logger.debug('Updating cache for package: {}'.format(package))
            _update_cache(package)

        logger.debug('Package successfuly added to this session: {}'.format(package))

        # create a dll assembly and get assembly info
        pkg_asm_info = _create_assembly(package)
        # update/create ui (needs the assembly to link button actions to commands saved in the dll)
        _update_revit_ui(package, pkg_asm_info)


# session object will have all the functionality for the user to interact with the session
# e.g. providing a list of installed packages, and others
# user is not expected to use _cache, _parser, _commandtree, _assemblies, or _ui
# All interactions should be through session module.
# ----------------------------------------------------------------------------------------------------------------------
# def get_command(script_address):
#     """Returns read only info about the caller python script.
#     Example:
#         this_script = pyRevit.session.get_this_command()
#         print(this_script.script_file_address)
#     """
