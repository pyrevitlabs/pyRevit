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

import sys

from loader.asmmaker import create_assembly, cleanup_existing_pyrevit_asm_files
from loader.parser import get_installed_lib_package_data, get_installed_package_data, get_parsed_package
from loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui
from pyrevit.core.config import HOME_DIR, SESSION_LOG_FILE_NAME, CACHE_TYPE_ASCII
from pyrevit.core.exceptions import PyRevitCacheError, PyRevitCacheExpiredError
from pyrevit.core.userconfig import user_config

from .logger import get_logger
from .usagedata import archive_script_usage_logs
from .utils import Timer

# Load CACHE_TYPE_ASCII or CACHE_TYPE_BINARY based on user settings.
if user_config.cache_type == CACHE_TYPE_ASCII:
    from loader.cacher_asc import is_cache_valid, get_cached_package, update_cache
else:
    from loader.cacher_bin import is_cache_valid, get_cached_package, update_cache

from pyrevit.core.config import PyRevitVersion
from pyrevit.extension.updater import get_pyrevit_repo

logger = get_logger(__name__)


def _update_pkg_syspaths(pkg, all_installed_lib_pkgs):
    for installed_lib_pkg in all_installed_lib_pkgs:
        pkg.add_syspath(installed_lib_pkg.directory)


def _perform_startup_cleanup_operations():
    # archive previous sessions logs
    archive_script_usage_logs()

    # Cleanups previous temporary assembly files
    cleanup_existing_pyrevit_asm_files()


def load():
    """Handles loading/reloading of the pyRevit addin and extension packages.
    To create a proper ui, pyRevit needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through private interactions with ._parser and ._ui

    Usage Example:
        import pyrevit.session as current_session
        current_session.load()
    """

    # initialize timer
    timer = Timer()

    # log python version, home directory, config file and loader script location.
    last_commit_hash = get_pyrevit_repo().last_commit_hash[:7]
    pyrvt_ver = '{}:{}'.format(PyRevitVersion.full_version_as_str(), last_commit_hash)
    logger.info('pyRevit version: {} - Made with :small-black-heart: in Portland, OR'.format(pyrvt_ver))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Config file is: {}'.format(user_config.config_file))
    logger.info('Generated log name for this session: {}'.format(SESSION_LOG_FILE_NAME))

    # for every package of installed packages, create an assembly, and create a ui
    # parser, assembly maker, and ui creator all understand loader.components classes. (They speak the same language)
    # the session.load() function (this function) moderates the communication and keeps a list of all packages that
    # are successfully loaded in this session. In another language, pyrevit.session sees the big picture whereas,
    # cacher, parser, asmmaker, and uimaker only see the package they've been asked to work on.
    # Session, creates an independent dll (using asmmaker) and ui (using uimaker) for every package.
    # This isolates other packages from any errors that might occur during package startup.

    _perform_startup_cleanup_operations()

    # get a list of all directories that could include packages
    pkg_search_dirs = user_config.get_package_root_dirs()
    logger.debug('Package Directories: {}'.format(pkg_search_dirs))

    # collect all library packages. Their dir paths need to be added to sys.path for all commands
    all_lib_pkgs = []
    for root_dir in pkg_search_dirs:
        for libpkg in get_installed_lib_package_data(root_dir):
            all_lib_pkgs.append(libpkg)
            logger.info(':python: Library package found: {}'.format(libpkg.directory))

    for root_dir in pkg_search_dirs:
        # Get a list of all installed packages in this directory
        # parser.get_installed_package_data() returns a list of packages in given directory
        # then iterater through packages and load one by one
        for package_info in get_installed_package_data(root_dir):
            # test if cache is valid for this package
            # it might seem unusual to create a package and then re-load it from cache but minimum information
            # about the package needs to be passed to the cache module for proper hash calculation and package recovery.
            # at this point `package` does not include any sub-components (e.g, tabs, panels, etc)
            # package object is very small and its creation doesn't add much overhead.

            try:
                # raise error if package does not have a valid cache
                if not is_cache_valid(package_info):
                    raise PyRevitCacheExpiredError('Cache is not valid for: {}'.format(package_info))

                # if cache is valid, load the cached package
                logger.debug('Cache is valid for: {}'.format(package_info))
                # cacher module takes the package object and injects cache data into it.
                package = get_cached_package(package_info)
                logger.info(':three_button_mouse: UI Package successfuly loaded from cache: {}'.format(package.name))

            except PyRevitCacheError as cache_err:
                logger.debug(cache_err)

                # Either cache is not available, not valid, or cache load has failed.
                # parse directory for components and return fully loaded package
                logger.debug('Parsing for package...')
                package = get_parsed_package(package_info)

                # update cache with newly parsed package
                logger.info(':three_button_mouse: UI Package successfuly parsed: {}'.format(package.name))
                logger.info('Updating cache for package: {}'.format(package.name))
                update_cache(package)

            # update package master syspaths with lib address of other packages
            # this is to support packages that provide library only to be used by other packages
            _update_pkg_syspaths(package, all_lib_pkgs)

            # create a dll assembly and get assembly info
            pkg_asm_info = create_assembly(package)
            if not pkg_asm_info:
                logger.critical('Failed to create assembly for: {}'.format(package))
                continue

            logger.info('Package assembly created: {}'.format(package_info.name))

            # update/create ui (needs the assembly to link button actions to commands saved in the dll)
            update_pyrevit_ui(package, pkg_asm_info)
            logger.info('UI created for package: {}'.format(package.name))

    cleanup_pyrevit_ui()

    # log load time
    endtime = timer.get_time()
    logger.info('Load time: {} seconds {}'.format(endtime,':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'))
