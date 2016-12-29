try:
    # noinspection PyUnresolvedReferences
    COMMAND_NAME = __commandname__
    # noinspection PyUnresolvedReferences
    COMMAND_PATH = __commandpath__
except:
    raise Exception('This is not a pyRevit script environment. These tools are irrelevant here.')

import os.path as op
from pyrevit.coreutils.logger import get_logger


scriptutils_logger = get_logger(__name__)
scriptutils_logger.debug('Executing script: {} @ {}'.format(COMMAND_NAME, COMMAND_PATH))


class PyRevitScriptUtils:
    def __init__(self):
        pass

    @property
    def info(self):
        from pyrevit.extensions.extensionmgr import get_command_from_path
        return get_command_from_path(COMMAND_PATH)

    @property
    def pyrevit_version(self):
        from pyrevit.versionmgr import PYREVIT_VERSION
        return PYREVIT_VERSION

    @property
    def ipy_engine(self):
        from pyrevit.coreutils import ipyengine
        try:
            return ipyengine.get_engine_wrapper()
        except:
            raise Exception('__engine__ not found at script runtime.')

    @property
    def output(self):
        from pyrevit.coreutils.console import output_window
        return output_window

    @property
    def config(self):
        from pyrevit.userconfig import user_config
        script_cfg_postfix = 'config'

        try:
            return getattr(user_config, COMMAND_NAME + script_cfg_postfix)
        except:
            user_config.add_section(COMMAND_NAME + script_cfg_postfix)
            return getattr(user_config, COMMAND_NAME + script_cfg_postfix)

    @staticmethod
    def save_config():
        from pyrevit.userconfig import user_config
        user_config.save_changes()

    @property
    def ui_button(self):
        from pyrevit.coreutils.ribbon import get_current_ui
        pyrvt_tabs = get_current_ui().get_pyrevit_tabs()
        for tab in pyrvt_tabs:
            button = tab.find_child(COMMAND_NAME)
            if button:
                return button
        return None

    @staticmethod
    def get_script_data_file(file_id, file_ext):
        """Returns a filename to be used by a user script to store data.
        Data files are saved in PYREVIT_APP_DIR and are NOT cleaned up between Revit sessions.
        """
        from pyrevit.coreutils.appdata import get_session_data_file
        script_file_id = '{}_{}'.format(COMMAND_NAME, file_id)
        return get_session_data_file(script_file_id, file_ext)

    @property
    def data_filename(self):
        return self.get_script_data_file('defaultdata', 'data')

    @staticmethod
    def get_bundle_file(file_name):
        return op.join(__commandpath__, file_name)

    @staticmethod
    def journal_write(data_key, msg):
        # Get the StringStringMap class which can write data into.
        # noinspection PyUnresolvedReferences
        data_map = __commandData__.JournalData
        data_map.Clear()

        # Begin to add the support data
        data_map.Add(data_key, msg)

    @staticmethod
    def journal_read(data_key):
        # Get the StringStringMap class which can write data into.
        # noinspection PyUnresolvedReferences
        data_map = __commandData__.JournalData

        # Begin to get the support data
        return data_map[data_key]

# ----------------------------------------------------------------------------------------------------------------------
# Utilities available to scripts
# ----------------------------------------------------------------------------------------------------------------------
# import useful functions from pyrevit.coreutils but not everything
# noinspection PyUnresolvedReferences
from pyrevit.coreutils import show_file_in_explorer, open_url
# noinspection PyUnresolvedReferences
from pyrevit.coreutils.envvars import get_pyrevit_env_var, set_pyrevit_env_var


# logger for this script
logger = get_logger(COMMAND_NAME)
# setup this script services
this_script = PyRevitScriptUtils()
