import sys
import clr

from pyrevit import HOME_DIR, EXEC_PARAMS
from pyrevit.coreutils import Timer
from pyrevit.coreutils.logger import get_logger, stdout_hndlr
from pyrevit.coreutils.appdata import cleanup_appdata_folder

from pyrevit.versionmgr import PYREVIT_VERSION
from pyrevit.userconfig import user_config

from pyrevit.extensions.extensionmgr import get_installed_ui_extensions

from pyrevit.loader.interfacetypes import BASE_CLASSES_ASM, LOADER_BASE_NAMESPACE, BASE_CLASSES_ASM_NAME
from pyrevit.loader.asmmaker import create_assembly, cleanup_assembly_files
from pyrevit.loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


logger = get_logger(__name__)


def _setup_output_window():
    # import module with ScriptOutput and ScriptOutputStream types (base classes module)
    clr.AddReference(BASE_CLASSES_ASM)
    base_module = __import__(LOADER_BASE_NAMESPACE)

    # create output window and assign handle
    out_window = base_module.ScriptOutput()
    EXEC_PARAMS.window_handle = out_window.Handle

    # create output stream and set stdout to it
    outstr = base_module.ScriptOutputStream(out_window)
    sys.stdout = outstr
    sys.stderr = outstr
    stdout_hndlr.stream = outstr


def _report_env():
    # log python version, home directory, config file, ...
    pyrvt_ver = PYREVIT_VERSION.get_formatted()
    logger.info('pyRevit version: {} - :coded: with :small-black-heart: in Portland, OR'.format(pyrvt_ver))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Base assembly is: {}'.format(BASE_CLASSES_ASM_NAME))
    logger.info('Config file is: {}'.format(user_config.config_file))


def _perform_onsessionload_ops():
    # if an output window is not provided, create one
    if EXEC_PARAMS.window_handle is None:
        _setup_output_window()
    # report environment conditions
    _report_env()


def _perform_onsessionloadcomplete_ops():
    cleanup_assembly_files()
    cleanup_appdata_folder()


def _new_session():
    # for every extension of installed extensions, create an assembly, and create a ui
    for ui_ext in get_installed_ui_extensions():
        # create a dll assembly and get assembly info
        ext_asm_info = create_assembly(ui_ext)
        if not ext_asm_info:
            logger.critical('Failed to create assembly for: {}'.format(ui_ext))
            continue

        logger.info('Extension assembly created: {}'.format(ui_ext.name))

        # update/create ui (needs the assembly to link button actions to commands saved in the dll)
        update_pyrevit_ui(ui_ext, ext_asm_info)
        logger.info('UI created for extension: {}'.format(ui_ext.name))

    cleanup_pyrevit_ui()


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

    _perform_onsessionload_ops()

    _new_session()

    _perform_onsessionloadcomplete_ops()

    # log load time
    endtime = timer.get_time()
    logger.info('Load time: {} seconds {}'.format(endtime, ':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'))
