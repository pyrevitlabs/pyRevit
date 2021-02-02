import types
import sys

from pyrevit import EXEC_PARAMS, HOST_APP
from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB, UI

#pylint: disable=W0401
from pyrevit.revit.db import *
from pyrevit.revit.db import query
from pyrevit.revit.db import select
from pyrevit.revit.db import create
from pyrevit.revit.db import update
from pyrevit.revit.db import ensure
from pyrevit.revit.db import delete
from pyrevit.revit.db.transaction import *
from pyrevit.revit.db import failure
from pyrevit.revit.db.pickling import *
from pyrevit.revit.journals import *
from pyrevit.revit.selection import *
from pyrevit.revit import ui
from pyrevit.revit import events
from pyrevit.revit import report
from pyrevit.revit import files
from pyrevit.revit import serverutils
from pyrevit.revit import geom
from pyrevit.revit import units
from pyrevit.revit import features
from pyrevit.revit import bim360


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def get_imported_symbol(symbol_name):
    return globals().get(symbol_name, None)


class RevitWrapper(types.ModuleType):
    def __init__(self):
        pass

    def __getattribute__(self, attr_name):
        attr = get_imported_symbol(attr_name)
        return attr or object.__getattribute__(self, attr_name)

    def __getattr__(self, attr_name):
        attr = get_imported_symbol(attr_name)
        if not attr:
            raise AttributeError('\'module\' object has no attribute \'{}\''
                                 .format(attr_name))
        return attr

    @property
    def uidoc(self):
        return HOST_APP.uidoc

    @property
    def doc(self):
        return HOST_APP.doc

    @property
    def docs(self):
        return HOST_APP.docs

    @property
    def active_view(self):
        return HOST_APP.active_view

    @active_view.setter
    def active_view(self, value):
        HOST_APP.active_view = value

    @property
    def servers(self):
        return HOST_APP.available_servers

    @staticmethod
    def open_doc(doc_path):
        """Open document at given path.

        Args:
            doc_path (str): document file path

        Returns:
            DB.Document: opened document
        """
        return HOST_APP.app.OpenDocumentFile(doc_path)

    @staticmethod
    def close_doc(doc):
        """Close given document.

        Args:
            doc (DB.Document): document
        """
        return doc.Close()

    @staticmethod
    def post_command(command_id):
        """Request Revit to run a command

        Args:
            command_id (str): command identifier e.g. ID_REVIT_SAVE_AS_TEMPLATE
        """
        HOST_APP.post_command(command_id)


class ErrorSwallower():
    """Suppresses warnings during script execution

    Example:
        >>> with ErrorSwallower() as swallower:
        >>>     for fam in families:
        >>>         revit.doc.EditFamily(fam)
        >>>         if swallower.get_swallowed():
        >>>             logger.warn("Warnings swallowed")
    """

    def __init__(self, log_errors=True):
        self._fswallower = failure.FailureSwallower()
        self._logerror = log_errors

    def on_failure_processing(self, _, event_args):
        """Failure processing event handler"""
        try:
            failure_accesssor = event_args.GetFailuresAccessor()
            mlogger.debug('request for failure processing...')
            result = event_args.GetProcessingResult()
            mlogger.debug('current failure processing result: %s', result)
            result = self._fswallower.preprocess_failures(failure_accesssor)
            mlogger.debug('setting failure processing results to: %s', result)
            event_args.SetProcessingResult(result)
        except Exception as fpex:
            mlogger.error('Error occured while processing failures. | %s', fpex)

    def get_swallowed_errors(self):
        """Return swallowed errors"""
        return self._fswallower.get_swallowed_failures()

    def reset(self):
        """Reset swallowed errors"""
        self._fswallower.reset()

    def __enter__(self):
        """Start listening to failure processing events"""
        HOST_APP.app.FailuresProcessing += self.on_failure_processing
        return self

    def __exit__(self, exception, exception_value, traceback):
        """Stop listening to failure processing events"""
        HOST_APP.app.FailuresProcessing -= self.on_failure_processing
        if exception and self._logerror:
            mlogger.error('Error in ErrorSwallower Context. | %s:%s',
                          exception, exception_value)


if not EXEC_PARAMS.doc_mode:
    sys.modules[__name__] = RevitWrapper()
