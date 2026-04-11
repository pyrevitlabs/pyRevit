# -*- coding: utf-8 -*-
"""Revit-aware event handler."""

# pylint: disable=import-error,invalid-name,broad-except
import sys
import traceback
import threading
import json
import numbers

from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import moduleutils as modutils
from pyrevit.compat import make_request

from pyrevit.routes.server import exceptions as excp
from pyrevit.routes.server import base

mlogger = get_logger(__name__)


def _safe_json_dumps(obj):
    r"""Serialize obj to a JSON string, safe for IronPython 2.7.

    IronPython 2.7 unifies str and unicode as .NET System.String.
    The standard json.dumps may fail with UnicodeDecodeError when
    strings contain non-ASCII characters (e.g. accented letters in
    French, German, etc.) and the system codec is reported as
    'unknown'.  This function manually builds a JSON string,
    escaping all non-ASCII as \\uXXXX.
    """
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, numbers.Integral):
        return str(obj)
    if isinstance(obj, float):
        import math

        if math.isnan(obj) or math.isinf(obj):
            return "null"
        return repr(obj)
    if isinstance(obj, str):
        # Manually escape to produce a JSON string with \uXXXX for non-ASCII
        parts = ['"']
        for ch in obj:
            cp = ord(ch)
            if ch == "\\":
                parts.append("\\\\")
            elif ch == '"':
                parts.append('\\"')
            elif ch == "\n":
                parts.append("\\n")
            elif ch == "\r":
                parts.append("\\r")
            elif ch == "\t":
                parts.append("\\t")
            elif cp < 0x20:
                parts.append("\\u{:04x}".format(cp))
            elif cp > 127:
                parts.append("\\u{:04x}".format(cp))
            else:
                parts.append(ch)
        parts.append('"')
        return "".join(parts)
    if isinstance(obj, dict):
        items = []
        for k, v in obj.items():
            items.append(_safe_json_dumps(str(k)) + ":" + _safe_json_dumps(v))
        return "{" + ",".join(items) + "}"
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_safe_json_dumps(item) for item in obj) + "]"
    # Fallback: convert to string
    try:
        return _safe_json_dumps(str(obj))
    except Exception:
        return '"<unserializable>"'


ARGS_REQUEST = "request"
ARGS_UIAPP = "uiapp"
ARGS_UIDOC = "uidoc"
ARGS_DOC = "doc"

RESERVED_VAR_NAMES = [
    ARGS_REQUEST,
    ARGS_UIAPP,
]


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
        """Get registered request."""
        with self._lock:  # pylint: disable=not-context-manager
            return self._request

    @request.setter
    def request(self, request):
        """Set a new request to be passed to handler when event is raised."""
        with self._lock:
            self._request = request

    @property
    def handler(self):
        """Get registered handler."""
        with self._lock:  # pylint: disable=not-context-manager
            return self._handler

    @handler.setter
    def handler(self, handler):
        """Set a new handler to be executed when event is raised."""
        if handler and callable(handler):
            with self._lock:
                self._handler = handler
        else:
            raise excp.RouteHandlerIsNotCallableException(handler.__name__)

    @property
    def response(self):
        """Get registered response."""
        with self._lock:  # pylint: disable=not-context-manager
            return self._response

    @property
    def done(self):
        """Check if execution of handler is completed and response is set."""
        with self._lock:  # pylint: disable=not-context-manager
            return self._done

    def _set_response(self, response):
        with self._lock:  # pylint: disable=not-context-manager
            self._response = response
            self._done = True

    def reset(self):
        """Reset internals for new execution."""
        with self._lock:  # pylint: disable=not-context-manager
            self._response = None
            self._done = False

    def join(self):
        """Allow other threads to call this method and wait for completion."""
        # wait until handler signals completion
        while True:
            with self._lock:
                if self._done:
                    return

    @staticmethod
    def run_handler(handler, kwargs):
        """Execute the handler function and return base.Response."""
        response = None
        kwargs = kwargs or {}
        if handler and callable(handler):
            try:
                # now call handler, and save response
                response = handler(**kwargs)  # pylint: disable=not-callable
            except Exception as hndlr_ex:
                # grab original CLS exception (IronPython 2 exposes
                # .clsException; IronPython 3 may not)
                clsx = getattr(hndlr_ex, "clsException", None)
                # get exception info
                exc_type, exc_value, exc_tb = sys.exc_info()
                # go back one frame to grab exception stack from handler
                # and grab traceback lines
                tb_report = "".join(traceback.format_tb(exc_tb)[1:])
                # wrap all the exception info
                response = excp.RouteHandlerException(
                    message=str(hndlr_ex),
                    exception_type=exc_type,
                    exception_traceback=tb_report,
                    clsx_message=clsx.Message if clsx else str(hndlr_ex),
                    clsx_source=clsx.Source if clsx else "",
                    clsx_stacktrace=clsx.StackTrace if clsx else tb_report,
                    clsx_targetsite=(
                        clsx.TargetSite.ToString() if clsx else ""
                    ),
                )
        else:
            response = excp.RouteHandlerIsNotCallableException(handler.__name__)
        return response

    @staticmethod
    def make_callback(callback_url, response):
        """Prepare request from base.Response and submit to callback url."""
        # parse response object
        r = RequestHandler.parse_response(response)
        # prepare and submit request
        make_request(url=callback_url, headers=r.headers, data=r.data)

    @staticmethod
    def wants_api_context(handler):
        """Check if handler needs host api context."""
        return modutils.has_any_arguments(
            function_obj=handler, arg_name_list=[ARGS_UIAPP, ARGS_UIDOC, ARGS_DOC]
        )

    @staticmethod
    def prepare_handler_kwargs(request, handler, uiapp=None):
        """Prepare call arguments for handler function."""
        uidoc = doc = None
        if uiapp:
            uidoc = getattr(uiapp, "ActiveUIDocument", None)
            if uidoc:
                doc = getattr(uidoc, "Document", None)

        kwargs = {}
        kwargs[ARGS_REQUEST] = request
        # if route pattern has parameter, provide those as well
        if request.params:
            kwargs.update({x.key: x.value for x in request.params})
        # add host api context params
        kwargs[ARGS_UIAPP] = uiapp
        kwargs[ARGS_UIDOC] = uidoc
        kwargs[ARGS_DOC] = doc

        return modutils.filter_kwargs(handler, kwargs)

    @staticmethod
    def parse_response(response):
        """Parse any given response data and return Response object."""
        def _json_dumps_safe(value):
            # IronPython may raise different encoding/runtime exceptions
            # for non-ASCII payloads; always fall back to manual serializer.
            try:
                return json.dumps(value, ensure_ascii=True)
            except Exception:
                return _safe_json_dumps(value)

        status = base.OK
        headers = {}
        data = None

        # can not directly check for isinstance(x, Response)
        # this module is executed on a different Engine than the
        # script that registered the request handler function, thus
        # the Response in script engine does not match Response
        # registered when this module was loaded
        #
        # now process reponse based on obj type
        # it is an exception is has .message
        # write the exeption to output and return
        if hasattr(response, "message"):
            status = (
                response.status
                if hasattr(response, "status")
                else base.INTERNAL_SERVER_ERROR
            )
            headers = {"Content-Type": "application/json"}
            exc_data = {
                "exception": {
                    "source": (
                        response.source
                        if hasattr(response, "source")
                        else base.DEFAULT_SOURCE
                    ),
                    "message": str(response),
                }
            }
            data = _json_dumps_safe(exc_data)

        # plain text response
        elif isinstance(response, str):
            # keey default status
            headers["Content-Type"] = "text/html"
            data = _json_dumps_safe(response)

        # any obj that has .status and .data, OR
        # any json serializable object
        # serialize before sending results
        # in case exceptions happen in serialization,
        # there are no double status in response header
        else:
            # determine status
            status = getattr(response, "status", base.OK)

            # determine headers
            headers.update(getattr(response, "headers", {}))

            # determine data, or dump the response object
            data = getattr(response, "data", response)

            # serialize data
            if data is not None:
                data = _json_dumps_safe(data)
                headers["Content-Type"] = "application/json"

        return base.Response(status=status, data=data, headers=headers)

    def Execute(self, uiapp):
        """This method is called to handle the external event."""
        # grab data. getters are thread-safe
        handler = self.handler
        request = self.request
        response = None

        try:
            # process necessary arguments for the handler
            kwargs = RequestHandler.prepare_handler_kwargs(
                request, handler, uiapp=uiapp
            )
            # run handler with prepared arguments, and grab the response
            response = self.run_handler(handler, kwargs)
        except Exception as exec_ex:
            # create exception response
            response = excp.RouteHandlerExecException(message=str(exec_ex))
        finally:
            # send response to callback url if requested
            if request.callback_url:
                RequestHandler.make_callback(request.callback_url, response)
            # or set the response to be picked up by http request handler
            else:
                self._set_response(response)

    def GetName(self):
        """String identification of the event handler."""
        return self.__class__.__name__
