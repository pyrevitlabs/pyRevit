import sys

from pyrevit import HOME_DIR, PyRevitVersion
from pyrevit import HOST_VERSION, HOST_USERNAME, PYREVIT_ASSEMBLY_NAME
from pyrevit.core.logger import get_logger
from pyrevit.coreutils import Timer

from pyrevit.userconfig import user_config
from pyrevit.usagedata import archive_script_usage_logs
from pyrevit.extensions.parser import get_installed_lib_package_data, get_installed_package_data, get_parsed_package
from pyrevit.loader.asmmaker import create_assembly, cleanup_existing_pyrevit_asm_files
from pyrevit.loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


logger = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------------
# session defaults
# ----------------------------------------------------------------------------------------------------------------------
SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, HOST_VERSION.version, HOST_USERNAME)

# creating a session id that is stamped with the process id of the Revit session.
# This id is unique for all python scripts running under this session.
# Previously the session id was stamped by formatted time
# SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, datetime.now().strftime('%y%m%d%H%M%S'))
SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, Process.GetCurrentProcess().Id)


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
        from pyrevit.loader import load_session
        load_session()
    """

    # initialize timer
    timer = Timer()

    _new_session()

    # log load time
    endtime = timer.get_time()
    logger.info('Load time: {} seconds {}'.format(endtime,':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'))
