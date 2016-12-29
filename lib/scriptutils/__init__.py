try:
    # noinspection PyUnresolvedReferences
    COMMAND_NAME = __commandname__
    # noinspection PyUnresolvedReferences
    COMMAND_PATH = __commandpath__
except:
    raise Exception('This is not a pyRevit script environment. These tools are irrelevant here.')

from pyrevit import HOST_APP
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
        # fixme: implement get_ui_button
        return 0

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
    def journal_write(data_key, msg):
        # Get the StringStringMap class which can write data into.
        # noinspection PyUnresolvedReferences
        data_map = __commandData__.JournalData
        data_map.Clear()

        # Begin to add the support data
        data_map.Add(data_key, msg)

    @staticmethod
    def journal_write(data_key):
        # Get the StringStringMap class which can write data into.
        # noinspection PyUnresolvedReferences
        data_map = __commandData__.JournalData

        # Begin to get the support data
        return data_map[data_key]


class CurrentElementSelection:
    def __init__(self, document, uidocument):
        self.doc = document
        self._uidoc = uidocument
        self._uidoc_selection = self._uidoc.Selection

        self.element_ids = list(self._uidoc_selection.GetElementIds())
        self.elements = [self.doc.GetElement(el_id) for el_id in self.element_ids]

        self.count = len(self.element_ids)
        self.first = self.last = None
        if self.count > 0:
            self.first = self.elements[0]
            self.last = self.elements[self.count-1]


# ----------------------------------------------------------------------------------------------------------------------
# Utilities available to scripts
# ----------------------------------------------------------------------------------------------------------------------
# import useful functions from pyrevit.coreutils but not everything
# noinspection PyUnresolvedReferences
from pyrevit.coreutils import show_file_in_explorer, open_url


# setup this script services
this_script = PyRevitScriptUtils()

logger = get_logger(COMMAND_NAME)

doc = HOST_APP.uiapp.ActiveUIDocument.Document
uidoc = HOST_APP.uiapp.ActiveUIDocument
selection = CurrentElementSelection(doc, uidoc)
