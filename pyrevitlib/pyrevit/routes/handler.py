"""Revit-aware event handler"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import HOST_APP
from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


class RequestHandler(UI.IExternalEventHandler):
    """Revit external event handler type."""
    request = None
    handler = None
    response = None
    # thread management
    # lock is set by server, done is set by self and checked by server
    lock = None
    done = False

    def Execute(self, uiapp):
        """This method is called to handle the external event."""
        with self.lock: #pylint: disable=not-context-manager
            self.response = None
            self.done = False

        response = None
        if self.handler and callable(self.handler):
            try:
                response = \
                    self.handler(self.request, uiapp) #pylint: disable=not-callable
            except Exception as hndlr_ex:
                self.response = {
                    "exception": {
                        "source": HOST_APP.pretty_name,
                        "message": str(hndlr_ex)
                    }
                }
        else:
            self.response = {
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
