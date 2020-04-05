"""Revit-aware event handler"""
#pylint: disable=import-error,invalid-name,broad-except
import sys
import json
import urllib2
import traceback
import threading

from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.routes import exceptions as excp
from pyrevit.routes import router
from pyrevit.routes import utils


mlogger = get_logger(__name__)


class RequestHandler(UI.IExternalEventHandler):
    """Revit external event handler type."""
    # static privates
    _request = None
    _handler = None
    _response = None
    _done = False
    _lock = threading.Lock()

    @property
    def request(self):
        """Get registered request"""
        with self._lock: #pylint: disable=not-context-manager
            return self._request

    @request.setter
    def request(self, request):
        """Set a new request to be passed to handler when event is raised"""
        with self._lock:
            self._request = request

    @property
    def handler(self):
        """Get registered handler"""
        with self._lock: #pylint: disable=not-context-manager
            return self._handler

    @handler.setter
    def handler(self, handler):
        """Set a new handler to be executed when event is raised"""
        if handler and callable(handler):
            with self._lock:
                self._handler = handler
        else:
            raise excp.RouteHandlerIsNotCallableException(handler.__name__)

    @property
    def response(self):
        """Get registered response"""
        with self._lock: #pylint: disable=not-context-manager
            return self._response

    @property
    def done(self):
        """Check if execution of handler is completed and response is set"""
        with self._lock: #pylint: disable=not-context-manager
            return self._done

    def _set_response(self, response):
        with self._lock: #pylint: disable=not-context-manager
            self._response = response
            self._done = True

    def reset(self):
        """Reset internals for new execution"""
        with self._lock: #pylint: disable=not-context-manager
            self._response = None
            self._done = False

    def join(self):
        """Allow other threads to call this method and wait for completion"""
        # wait until handler signals completion
        while True:
            with self._lock:
                if self._done:
                    return

    @staticmethod
    def run_handler(handler, kwargs):
        response = None
        kwargs = kwargs or {}
        if handler and callable(handler):
            try:
                # now call handler, and save response
                response = handler(**kwargs) #pylint: disable=not-callable
            except Exception as hndlr_ex:
                # grab original CLS exception
                clsx = hndlr_ex.clsException #pylint: disable=no-member
                # get exception info
                sys.exc_type, sys.exc_value, sys.exc_traceback = \
                    sys.exc_info()
                # go back one frame to grab exception stack from handler
                # and grab traceback lines
                tb_report = ''.join(
                    traceback.format_tb(sys.exc_traceback)[1:]
                )
                # wrap all the exception info
                response = excp.RouteHandlerException(
                    message=str(hndlr_ex),
                    exception_type=sys.exc_type,
                    exception_traceback=tb_report,
                    clsx_message=clsx.Message,
                    clsx_source=clsx.Source,
                    clsx_stacktrace=clsx.StackTrace,
                    clsx_targetsite=clsx.TargetSite.ToString()
                    )
        else:
            response = \
                excp.RouteHandlerIsNotCallableException(handler.__name__)
        return response

    def Execute(self, uiapp):
        """This method is called to handle the external event."""
        handler = self.handler
        request = self.request
        response = None

        try:
            # keyword args to the handler
            kwargs = {}
            kwargs[router.ARGS_UIAPP] = uiapp
            if utils.has_argument(handler, router.ARGS_REQUEST):
                kwargs[router.ARGS_REQUEST] = request
            # if route pattern has parameter, provide those as
            if request.params:
                kwargs.update({x.key:x.value for x in request.params})

            # run handler
            response = self.run_handler(handler, kwargs)
        except Exception as exec_ex:
            response = excp.RouteHandlerExecException(message=str(exec_ex))
        finally:
            self._set_response(response)

    def GetName(self):
        """String identification of the event handler."""
        return self.__class__.__name__
