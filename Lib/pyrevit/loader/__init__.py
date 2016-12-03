import sys

from System.Diagnostics import Process

from pyrevit import HOME_DIR
from pyrevit import HOST_VERSION, HOST_USERNAME, PYREVIT_ADDON_NAME
from pyrevit.coreutils import Timer
from pyrevit.coreutils.logger import get_logger
from pyrevit.extensions import get_installed_ui_extensions
from pyrevit.loader.asmmaker import create_assembly
from pyrevit.loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui
from pyrevit.repo import PYREVIT_VERSION
from pyrevit.usagedata import SESSION_LOG_FILE_NAME, archive_script_usage_logs
from pyrevit.userconfig import user_config


logger = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------------
# session defaults
# ----------------------------------------------------------------------------------------------------------------------
SESSION_ID = "{}{}_{}".format(PYREVIT_ADDON_NAME, HOST_VERSION.version, HOST_USERNAME)

# creating a session id that is stamped with the process id of the Revit session.
# This id is unique for all python scripts running under this session.
# Previously the session id was stamped by get_formatted time
# SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, datetime.now().strftime('%y%m%d%H%M%S'))
SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, Process.GetCurrentProcess().Id)


def _perform_onstartup_operations():
    # archive previous sessions logs
    archive_script_usage_logs()


def _report_env():
    # log python version, home directory, config file, ...
    pyrvt_ver = PYREVIT_VERSION.get_formatted()
    logger.info('pyRevit version: {} - Made with :small-black-heart: in Portland, OR'.format(pyrvt_ver))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Config file is: {}'.format(user_config.config_file))
    logger.info('Generated log name for this session: {}'.format(SESSION_LOG_FILE_NAME))


def _new_session():
    # report environment conditions
    _report_env()

    # for every extension of installed extensions, create an assembly, and create a ui
    # get a list of all directories that could include extensions
    pkg_search_dirs = user_config.get_ext_root_dirs()
    logger.debug('Extension Directories: {}'.format(pkg_search_dirs))

    # collect all library extensions. Their dir paths need to be added to sys.path for all commands
    for root_dir in pkg_search_dirs:
        # Get a list of all installed extensions in this directory
        # _parser.get_installed_extension_data() returns a list of extensions in given directory
        # then iterater through extensions and load one by one
        for ui_ext in get_installed_ui_extensions(root_dir):
            # create a dll assembly and get assembly info
            pkg_asm_info = create_assembly(ui_ext)
            if not pkg_asm_info:
                logger.critical('Failed to create assembly for: {}'.format(ui_ext))
                continue

            logger.info('Extension assembly created: {}'.format(ui_ext.name))

            # update/create ui (needs the assembly to link button actions to commands saved in the dll)
            update_pyrevit_ui(ui_ext, pkg_asm_info)
            logger.info('UI created for extension: {}'.format(ui_ext.name))

    cleanup_pyrevit_ui()

    _perform_onstartup_operations()


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions.
    To create a proper ui, pyRevit extensions needs to be properly parsed and a dll assembly needs to be created.
    This function handles both tasks through interactions with .extensions and .coreutils

    Usage Example:
        from pyrevit.loader import load_session
        load_session()
    """

    # initialize timer
    timer = Timer()

    _new_session()

    # log load time
    endtime = timer.get_time()
    logger.info('Load time: {} seconds {}'.format(endtime, ':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'))
