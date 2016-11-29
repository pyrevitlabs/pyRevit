"""
Description:
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This module provide a series of functions to create and manage a pyRevit session under Revit (using the 4 modules).
Each time Revit is run, the loader script imports pyRevit.session and creates a session. The session (this module)
then calls the parser, assembly maker, and lastly ui maker to create the buttons in Revit.
Each pyRevit session will have its own .dll and log file.
"""

import os.path as op
import sys

from pyrevit import HOME_DIR, PyRevitVersion
from pyrevit import HOST_VERSION, HOST_USERNAME, PYREVIT_ASSEMBLY_NAME
from pyrevit import USER_TEMP_DIR
from pyrevit.core.exceptions import PyRevitCacheError, PyRevitCacheExpiredError
from pyrevit.core.logger import get_logger
from pyrevit.coreutils import Timer
from pyrevit.extensions.parser import get_installed_lib_package_data, get_installed_package_data, get_parsed_package
from pyrevit.loader.asmmaker import create_assembly, cleanup_existing_pyrevit_asm_files
from pyrevit.loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui
from pyrevit.scriptutils.usagedata import archive_script_usage_logs
from pyrevit.updater import get_pyrevit_repo
from pyrevit.userconfig import user_config

# Load CACHE_TYPE_ASCII or CACHE_TYPE_BINARY based on user settings.
if user_config.cache_type == CACHE_TYPE_ASCII:
    from pyrevit.extensions.parser.cacher_asc import is_cache_valid, get_cached_package, update_cache
else:
    from pyrevit.extensions.parser.cacher_bin import is_cache_valid, get_cached_package, update_cache


logger = get_logger(__name__)


# noinspection PyUnresolvedReferences
from System.Diagnostics import Process

# ----------------------------------------------------------------------------------------------------------------------
# session defaults
# ----------------------------------------------------------------------------------------------------------------------
SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, HOST_VERSION.version, HOST_USERNAME)

# creating a session id that is stamped with the process id of the Revit session.
# This id is unique for all python scripts running under this session.
# Previously the session id was stamped by formatted time
# SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, datetime.now().strftime('%y%m%d%H%M%S'))
SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, Process.GetCurrentProcess().Id)


# ----------------------------------------------------------------------------------------------------------------------
# asm maker defaults
# ----------------------------------------------------------------------------------------------------------------------
ASSEMBLY_FILE_TYPE = '.dll'
LOADER_ADDIN = 'PyRevitLoader'

# template python command class
LOADER_BASE_CLASSES_ASM = 'PyRevitBaseClasses'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommand')

# template python command availability class
LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME = 'PyRevitCommandDefaultAvail'
LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM,
                                                          LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME)
LOADER_ADDIN_COMMAND_CAT_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommandCategoryAvail')
LOADER_ADDIN_COMMAND_SEL_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommandSelectionAvail')


# ----------------------------------------------------------------------------------------------------------------------
# caching tabs, panels, buttons and button groups
# ----------------------------------------------------------------------------------------------------------------------
SUB_CMP_KEY = '_sub_components'
HASH_VALUE_PARAM = 'hash_value'
HASH_VERSION_PARAM = 'hash_version'

# ----------------------------------------------------------------------------------------------------------------------
# script usage logging defaults
# ----------------------------------------------------------------------------------------------------------------------
# creating log file name from stamped session id
LOG_FILE_TYPE = '.log'
SESSION_LOG_FILE_NAME = SESSION_STAMPED_ID + LOG_FILE_TYPE
SESSION_LOG_FILE_PATH = op.join(USER_TEMP_DIR, SESSION_LOG_FILE_NAME)
LOG_ENTRY_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def _update_pkg_syspaths(pkg, all_installed_lib_pkgs):
    for installed_lib_pkg in all_installed_lib_pkgs:
        pkg.add_syspath(installed_lib_pkg.directory)


def _perform_startup_cleanup_operations():
    # archive previous sessions logs
    archive_script_usage_logs()

    # Cleanups previous temporary assembly files
    cleanup_existing_pyrevit_asm_files()


def _report_env():
    # log python version, home directory, config file and loader script location.
    last_commit_hash = get_pyrevit_repo().last_commit_hash[:7]
    pyrvt_ver = '{}:{}'.format(PyRevitVersion.full_version_as_str(), last_commit_hash)
    logger.info('pyRevit version: {} - Made with :small-black-heart: in Portland, OR'.format(pyrvt_ver))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Config file is: {}'.format(user_config.config_file))
    logger.info('Generated log name for this session: {}'.format(SESSION_LOG_FILE_NAME))


def _get_pkg_from_cache_or_parser(package_info):
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

    return package


def _new_session():
    _report_env()
    _perform_startup_cleanup_operations()

    # for every package of installed extensions, create an assembly, and create a ui
    # _parser, assembly maker, and ui creator all understand loader.components classes. (They speak the same language)
    # the session.load() function (this function) moderates the communication and keeps a list of all extensions that
    # are successfully loaded in this session. In another language, pyrevit.session sees the big picture whereas,
    # cacher, _parser, asmmaker, and uimaker only see the package they've been asked to work on.
    # Session, creates an independent dll (using asmmaker) and ui (using uimaker) for every package.
    # This isolates other extensions from any errors that might occur during package startup.
    # get a list of all directories that could include extensions
    pkg_search_dirs = user_config.get_package_root_dirs()
    logger.debug('Package Directories: {}'.format(pkg_search_dirs))

    # collect all library extensions. Their dir paths need to be added to sys.path for all commands
    all_lib_pkgs = []
    for root_dir in pkg_search_dirs:
        for libpkg in get_installed_lib_package_data(root_dir):
            all_lib_pkgs.append(libpkg)
            logger.info(':python: Library package found: {}'.format(libpkg.directory))

    for root_dir in pkg_search_dirs:
        # Get a list of all installed extensions in this directory
        # _parser.get_installed_package_data() returns a list of extensions in given directory
        # then iterater through extensions and load one by one
        for package_info in get_installed_package_data(root_dir):
            # test if cache is valid for this package
            # it might seem unusual to create a package and then re-load it from cache but minimum information
            # about the package needs to be passed to the cache module for proper hash calculation and package recovery.
            # at this point `package` does not include any sub-components (e.g, tabs, panels, etc)
            # package object is very small and its creation doesn't add much overhead.
            package = _get_pkg_from_cache_or_parser()

            # update package master syspaths with lib address of other extensions
            # this is to support extensions that provide library only to be used by other extensions
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


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions extensions.
    To create a proper ui, pyRevit needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through private interactions with ._parser and ._ui

    Usage Example:
        import pyrevit.session as current_session
        current_session.load()
    """

    # initialize timer
    timer = Timer()

    _new_session()

    # log load time
    endtime = timer.get_time()
    logger.info('Load time: {} seconds {}'.format(endtime,':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'))
