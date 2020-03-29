"""Revit-aware event handler"""
#pylint: disable=import-error,invalid-name,broad-except
import threading

from pyrevit import HOST_APP
from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


class RequestHandler(UI.IExternalEventHandler):
    """Revit external event handler type."""

    def __init__(self, request, handler):
        self.request = request
        self.handler = handler
        self.response = None
        self.done = False
        self.lock = threading.Lock()

    def reset(self):
        """Reset internals for new execution"""
        with self.lock:
            self.response = None
            self.done = False

    def Execute(self, uiapp):
        """This method is called to handle the external event."""
        handler = None
        with self.lock: #pylint: disable=not-context-manager
            handler = self.handler

        response = None
        if handler and callable(handler):
            try:
                response = \
                    handler(self.request, uiapp) #pylint: disable=not-callable
            except Exception as hndlr_ex:
                response = {
                    "exception": {
                        "source": HOST_APP.pretty_name,
                        "message": str(hndlr_ex)
                    }
                }
        else:
            response = {
                "exception": {
                    "source": HOST_APP.pretty_name,
                    "message": "Route handler is invalid"
                }
            }

        with self.lock: #pylint: disable=not-context-manager
            self.response = response
            self.done = True

    def GetName(self):
        """String identification of the event handler."""
        return self.__class__.__name__
