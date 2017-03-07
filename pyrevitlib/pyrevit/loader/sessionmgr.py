"""
The loader module manages the workflow of loading a new pyRevit session.
It's main purpose is to orchestrate the process of finding pyRevit extensions,
creating dll assemblies for them, and creating a user interface
in the host application.

Everything starts from ``sessionmgr.load_session()`` function...

The only public function is ``load_session()`` that loads a new session.
Everything else is private.
"""

import sys
import clr

from pyrevit import HOME_DIR, EXEC_PARAMS, FIRST_LOAD, HOST_APP
from pyrevit.coreutils import Timer
from pyrevit.coreutils.logger import get_logger, stdout_hndlr
from pyrevit.coreutils.appdata import cleanup_appdata_folder

from pyrevit.versionmgr import PYREVIT_VERSION
from pyrevit.userconfig import user_config

from pyrevit.extensions.extensionmgr import get_installed_ui_extensions

from pyrevit.loader.basetypes import BASE_TYPES_ASM, LOADER_BASE_NAMESPACE, \
                                     BASE_TYPES_ASM_NAME
from pyrevit.loader.asmmaker import create_assembly, cleanup_assembly_files
from pyrevit.loader.uimaker import update_pyrevit_ui, cleanup_pyrevit_ui

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


logger = get_logger(__name__)


def _setup_output_window():
    # import module with ScriptOutput and ScriptOutputStream types
    # (base classes module)
    clr.AddReference(BASE_TYPES_ASM)
    base_module = __import__(LOADER_BASE_NAMESPACE)

    # create output window and assign handle
    out_window = base_module.ScriptOutput()
    EXEC_PARAMS.window_handle = out_window

    # create output stream and set stdout to it
    # we're not opening the output window here.
    # The output stream will open the window if anything is being printed.
    outstr = base_module.ScriptOutputStream(out_window)
    sys.stdout = outstr
    sys.stderr = outstr
    stdout_hndlr.stream = outstr


def _report_env():
    # log python version, home directory, config file, ...
    # get python version that includes last commit hash
    pyrvt_ver = PYREVIT_VERSION.get_formatted()

    logger.info('pyRevit version: {} - '
                ':coded: with :small-black-heart: '
                'in Portland, OR'.format(pyrvt_ver))
    logger.info('Host is {} (build: {} id: {})'.format(HOST_APP.version_name,
                                                       HOST_APP.build,
                                                       HOST_APP.proc_id))
    logger.info('Running on: {}'.format(sys.version))
    logger.info('Home Directory is: {}'.format(HOME_DIR))
    logger.info('Base assembly is: {}'.format(BASE_TYPES_ASM_NAME))
    logger.info('Config file is: {}'.format(user_config.config_file))


def _perform_onsessionload_ops():
    # the loader dll addon, does not create an output window
    # if an output window is not provided, create one
    if FIRST_LOAD:
        _setup_output_window()

    # once pre-load is complete, report environment conditions
    _report_env()


def _perform_onsessionloadcomplete_ops():
    # cleanup old assembly files.
    # asmmaker.cleanup_assembly_files() will take care of that
    cleanup_assembly_files()

    # clean up temp app files between sessions.
    cleanup_appdata_folder()


def _new_session():
    """
    Get all installed extensions (UI extension only) and creates an assembly,
    and a ui for each.

    Returns:
        None
    """
    # get all installed ui extensions
    for ui_ext in get_installed_ui_extensions():
        # create a dll assembly and get assembly info
        ext_asm_info = create_assembly(ui_ext)
        if not ext_asm_info:
            logger.critical('Failed to create assembly for: {}'.format(ui_ext))
            continue

        logger.info('Extension assembly created: {}'.format(ui_ext.name))

        # update/create ui (needs the assembly to link button actions
        # to commands saved in the dll)

        update_pyrevit_ui(ui_ext, ext_asm_info, user_config.core.get_option('loadbeta', default_value=False))
        logger.info('UI created for extension: {}'.format(ui_ext.name))

    # cleanup existing UI. This is primarily for cleanups after reloading
    cleanup_pyrevit_ui()


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions.
    To create a proper ui, pyRevit extensions needs to be properly parsed and
    a dll assembly needs to be created. This function handles these tasks
    through interactions with .extensions, .loader.asmmaker, and .loader.uimaker

    Example:
        >>> from pyrevit.loader.sessionmgr import load_session
        >>> load_session()     # start loading a new pyRevit session

    Returns:
        None
    """

    # initialize timer to measure load time
    timer = Timer()

    # perform pre-load tasks
    _perform_onsessionload_ops()

    # create a new session
    _new_session()

    # perform post-load tasks
    _perform_onsessionloadcomplete_ops()

    # log load time and thumbs-up :)
    endtime = timer.get_time()
    success_emoji = ':ok_hand_sign:' if endtime < 3.00 else ':thumbs_up:'
    logger.info('Load time: {} seconds {}'.format(endtime, success_emoji))

    # if everything went well, self destruct
    try:
        from pyrevit.coreutils.console.output import output_window
        timeout = user_config.core.get_option('startuplogtimeout', default_value=5)
        output_window.self_destruct(timeout)
    except Exception as imp_err:
        logger.error('Error setting up self_destruct on output window | {}'.format(imp_err))
