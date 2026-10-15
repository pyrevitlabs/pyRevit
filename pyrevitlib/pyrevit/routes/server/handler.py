# -*- coding: utf-8 -*-
"""Revit-aware event handler."""

# pylint: disable=import-error,invalid-name,broad-except
import sys
import traceback
import threading
import json
import numbers
from collections import deque

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


class RequestWorkItem(object):
    """One queued request, with an independent response and completion signal."""

    def __init__(self, request, handler):
        self.request = request
        self.handler = handler
        self.event = threading.Event()
        self.response = None
        self._lock = threading.Lock()

    def complete(self, response):
        """Publish the first result, preserving queued-request rejections."""
        with self._lock:
            if not self.event.is_set():
                self.response = response
                self.event.set()


class RequestHandler(UI.IExternalEventHandler):
    """Drain API requests using one external event per server lifetime.

    Revit may coalesce Raise calls. The queue, rather than the number of event
    invocations, therefore determines how many handlers Execute must run.
    """

    def __init__(self):
        self._queue = deque()
        self._lock = threading.Lock()
        self._stopped = False
        self.external_event = None
        self._awaiting_idle = False
        self._uiapp = None

    def enqueue(self, item):
        """Register work, returning a server rejection only when stopped."""
        with self._lock:
            if self._stopped:
                response = self.stopped_response(item.request)
                item.complete(response)
                return response
            self._queue.append(item)
        return None

    @staticmethod
    def stopped_response(request):
        """Explain why queued work cannot run during stop or session reload."""
        return excp.RouteHandlerDeniedException(
            request, message="Routes server stopped or reloaded: %s" % request.path
        )

    def cancel(self, item, response):
        """Reject only work that has not been taken by Execute."""
        with self._lock:
            try:
                self._queue.remove(item)
            except ValueError:
                return False
            item.complete(response)
            return True

    def stop(self):
        """Reject queued work and notify callbacks without holding the queue lock.

        Disposal waits for the next Idling event if Execute has run since the
        last idle cycle, so a route can reload its own server safely.
        """
        callbacks = []
        external_event = None
        with self._lock:
            self._stopped = True
            while self._queue:
                item = self._queue.popleft()
                item.complete(self.stopped_response(item.request))
                if item.request.callback_url:
                    callbacks.append(item)
            if not self._awaiting_idle:
                external_event = self.external_event
                self.external_event = None
        self._dispose_external_event(external_event)
        if callbacks:

            def notify_callbacks():
                for item in callbacks:
                    self._notify_callback(item)

            notifier = threading.Thread(target=notify_callbacks)
            notifier.daemon = True
            notifier.start()

    @staticmethod
    def _dispose_external_event(external_event):
        """Release the native event without letting teardown errors escape."""
        if external_event is not None:
            try:
                external_event.Dispose()
            except Exception:
                mlogger.debug(
                    "Routes event disposal failed | %s", traceback.format_exc()
                )

    def _on_idle(self, sender, args):
        """Dispose a stopped event only after Revit has returned from Execute."""
        external_event = None
        with self._lock:
            self._uiapp.Idling -= self._on_idle
            self._uiapp = None
            self._awaiting_idle = False
            if self._stopped:
                external_event = self.external_event
                self.external_event = None
        self._dispose_external_event(external_event)

    def _notify_callback(self, item):
        """Deliver either a handler result or a queued-request rejection."""
        try:
            if item.request.callback_url:
                self.make_callback(item.request.callback_url, item.response)
        except Exception:
            mlogger.debug("Routes callback failed | %s", traceback.format_exc())

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
                    clsx_targetsite=(clsx.TargetSite.ToString() if clsx else ""),
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
        # if query parameters are present, provide those as well
        if request.query_params:
            reserved = {ARGS_REQUEST, ARGS_UIAPP, ARGS_UIDOC, ARGS_DOC}
            kwargs.update(
                {k: v for k, v in request.query_params.items() if k not in reserved}
            )
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
        if isinstance(response, Exception) or hasattr(response, "message"):
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
        """Drain all queued work, isolating both handler and callback failures."""
        with self._lock:
            if self._stopped:
                return
            if self.external_event is not None and not self._awaiting_idle:
                uiapp.Idling += self._on_idle
                self._uiapp = uiapp
                self._awaiting_idle = True
        while True:
            with self._lock:
                if self._stopped or not self._queue:
                    return
                item = self._queue.popleft()
            response = None
            try:
                kwargs = self.prepare_handler_kwargs(
                    item.request, item.handler, uiapp=uiapp
                )
                response = self.run_handler(item.handler, kwargs)
            except Exception as exec_ex:
                response = excp.RouteHandlerExecException(message=str(exec_ex))
            finally:
                item.complete(response)
                self._notify_callback(item)

    def GetName(self):
        """String identification of the event handler."""
        return self.__class__.__name__
