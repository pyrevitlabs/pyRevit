# -*- coding: utf-8 -*-
"""Routes HTTP Server."""

# pylint: disable=import-error,invalid-name,broad-except
# pylint: disable=missing-docstring
import sys
import traceback
import json
import threading

from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger
from pyrevit.compat import PY3
from pyrevit.compat import urlparse

if PY3:
    from urllib.parse import parse_qs
else:
    from urlparse import parse_qs

from pyrevit.routes.server import exceptions as excp
from pyrevit.routes.server import base
from pyrevit.routes.server import handler
from pyrevit.routes.server import router

if PY3:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
else:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from SocketServer import ThreadingMixIn


mlogger = get_logger(__name__)


# instance of event handler created when this module is loaded
# on hosts main thread. Creating external events on non-main threads
# are prohibited by the host. this event handler is reconfigured
# for every request registered by this module
REQUEST_HNDLR = handler.RequestHandler()
EVENT_HNDLR = UI.ExternalEvent.Create(REQUEST_HNDLR)


class HttpRequestHandler(BaseHTTPRequestHandler):
    """HTTP Requests Handler."""

    def log_message(self, fmt, *args):
        """Record a request without writing to stderr.

        pyRevit directs stderr to its script output console, a WPF window that
        can only be created on Revit's STA UI thread. Requests are served on
        threads that are never STA, so a write here can terminate the Revit
        process. Request logging must never reach stderr.

        Args:
            fmt (str): printf-style format string.
            *args: Values interpolated into ``fmt``.
        """
        mlogger.debug(fmt, *args)

    def _parse_api_path(self):
        url_parts = urlparse(self.path)
        if url_parts:
            levels = url_parts.path.split("/")
            # host:ip/<api_name>/<route>/.../.../...
            if levels and len(levels) >= 2:
                api_name = levels[1]
                if len(levels) > 2:
                    api_path = "/" + "/".join(levels[2:])
                else:
                    api_path = "/"
                query_string = url_parts.query
                return api_name, api_path, query_string
        return None, None, None

    def _parse_request_info(self):
        # find the app
        api_name, api_path, query_string = self._parse_api_path()  # type: str, str, str
        if not api_name:
            raise excp.APINotDefinedException(api_name)
        return api_name, api_path, query_string

    def _find_route_handler(self, api_name, path, method):
        route, route_handler = router.get_route_handler(
            api_name=api_name, path=path, method=method
        )
        if not route_handler:
            raise excp.RouteHandlerNotDefinedException(api_name, path, method)
        return route, route_handler

    def _prepare_request(self, route, path, method, query_string=None):
        # process request data
        data = None
        content_length = self.headers.get("content-length")  # type: str
        if content_length and content_length.isnumeric():
            data = self.rfile.read(int(content_length))
            # format data
            content_type_header = self.headers.get("content-type")
            if content_type_header:
                content_type = content_type_header.split(";")[0].strip()
                if content_type == "application/json":
                    data = json.loads(data)

        # parse query string into a dictionary
        query_params = {}
        if query_string:
            # parse_qs returns lists for values; flatten single values to strings
            parsed = parse_qs(query_string)
            query_params = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

        return base.Request(
            path=path,
            method=method,
            data=data,
            params=router.extract_route_params(route.pattern, path),
            query_params=query_params,
        )

    def _prepare_host_handler(self, request, route_handler):
        # create the base Revit external event handler
        # upon Raise(), finds and runs the appropriate func
        REQUEST_HNDLR.request = request
        REQUEST_HNDLR.handler = route_handler
        return REQUEST_HNDLR, EVENT_HNDLR

    def _call_host_event(self, req_hndlr, event_hndlr):
        # reset handler
        req_hndlr.reset()
        # raise request to host
        extevent_raise_response = event_hndlr.Raise()
        if extevent_raise_response == UI.ExternalEventRequest.Denied:
            raise excp.RouteHandlerDeniedException(req_hndlr.request)
        elif extevent_raise_response == UI.ExternalEventRequest.TimedOut:
            raise excp.RouteHandlerTimedOutException(req_hndlr.request)

    def _call_host_event_sync(self, req_hndlr, event_hndlr):
        # call handler
        self._call_host_event(req_hndlr, event_hndlr)

        # wait until event has been picked up by host for execution
        while event_hndlr.IsPending:
            pass

        # wait until handler signals completion
        req_hndlr.join()

    def _write_response(self, response):
        r = handler.RequestHandler.parse_response(response)
        self.send_response(r.status)
        body = r.data if r.data is not None else "\n"
        if isinstance(body, str):
            body = body.encode("utf-8")
        elif not isinstance(body, bytes):
            body = str(body).encode("utf-8")

        self.send_header("Content-Length", str(len(body)))
        if r.headers:
            for key, value in r.headers.items():
                if str(key).lower() == "content-length":
                    continue
                self.send_header(key, value)
        self.end_headers()
        # sending \n if no data otherwise Postman panics for some reason
        self.wfile.write(body)

    def _handle_route(self, method):
        # process the given url and find API and route
        api_name, path, query_string = self._parse_request_info()

        # find the handler function registered by the API and route
        route, route_handler = self._find_route_handler(api_name, path, method)

        # prepare a request obj to be passed to registered handler
        request = self._prepare_request(route, path, method, query_string)

        # if handler has uiapp in arguments, run in host api context
        if handler.RequestHandler.wants_api_context(route_handler):
            # create a handler and event object in host
            req_hndlr, event_hndlr = self._prepare_host_handler(request, route_handler)

            # do the handling work
            # if request has callback url, raise the event handler and return
            #   the handler, when executed, will notify the callback url
            if request.callback_url:
                self._call_host_event(req_hndlr, event_hndlr)
                # acknowledge the request is accepted and return
                self._write_response(base.Response(status=base.NO_CONTENT))
            # otherwise run the handler and wait
            else:
                self._call_host_event_sync(req_hndlr, event_hndlr)
                # prepare response
                # grab response from req_hndlr.response
                # req_hndlr.response getter is thread-safe
                self._write_response(req_hndlr.response)
        # otherwise run here
        else:
            # now run the method, and gret response
            response = handler.RequestHandler.run_handler(
                handler=route_handler,
                kwargs=handler.RequestHandler.prepare_handler_kwargs(
                    request=request, handler=route_handler
                ),
            )
            # prepare response
            self._write_response(response)

    def _process_request(self, method):
        # this method is wrapping the actual handler and is
        # catching all the excp
        try:
            self._handle_route(method=method)
        except Exception as ex:
            # get exception info
            exc_type, exc_value, exc_tb = sys.exc_info()
            # go back one frame to grab exception stack from handler
            # and grab traceback lines
            tb_report = "".join(traceback.format_tb(exc_tb)[1:])
            self._write_response(
                excp.ServerException(
                    message=str(ex),
                    exception_type=exc_type,
                    exception_traceback=tb_report,
                )
            )

    # CRUD Methods ------------------------------------------------------------
    # create
    def do_POST(self):
        self._process_request(method="POST")

    # read
    def do_GET(self):
        self._process_request(method="GET")

    # update
    def do_PUT(self):
        self._process_request(method="PUT")

    # delete
    def do_DELETE(self):
        self._process_request(method="DELETE")

    # rest of standard http methods -------------------------------------------
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
    def do_HEAD(self):
        self._process_request(method="HEAD")

    def do_CONNECT(self):
        self._process_request(method="CONNECT")

    def do_OPTIONS(self):
        self._process_request(method="OPTIONS")

    def do_TRACE(self):
        self._process_request(method="TRACE")

    def do_PATCH(self):
        self._process_request(method="PATCH")


class ThreadedHttpServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server.

    Requests are served on threads that are never STA, while pyRevit directs
    stdout and stderr to its script output console, a WPF window that can only
    be created on Revit's STA UI thread. An exception escaping one of these
    threads is printed there and terminates the Revit process, so nothing here
    may write to stderr and no exception may leave a thread.
    """

    allow_reuse_address = True

    def shutdown(self):
        self.socket.close()
        HTTPServer.shutdown(self)

    def handle_error(self, request, client_address):
        """Report a failed request without writing to stderr.

        See the class docstring for why stderr is unsafe here.

        Args:
            request: The request being processed.
            client_address (tuple): Client address the request came from.
        """
        mlogger.debug(
            "Routes request error | %s | %s", client_address, traceback.format_exc()
        )

    def process_request_thread(self, request, client_address):
        """Serve a request, letting no exception escape the thread.

        Stopping the server closes sockets while requests are still in flight,
        so the per-request cleanup can raise. The inherited implementation
        leaves that path unguarded, and an exception escaping here terminates
        Revit for the reason given in the class docstring.

        Args:
            request: The request to process.
            client_address (tuple): Client address the request came from.
        """
        try:
            self.finish_request(request, client_address)
        except Exception:
            try:
                self.handle_error(request, client_address)
            except Exception:
                mlogger.debug(
                    "Routes handle_error failed | %s | %s",
                    client_address,
                    traceback.format_exc(),
                )
        finally:
            try:
                self.shutdown_request(request)
            except Exception:
                mlogger.debug(
                    "Routes request cleanup error | %s | %s",
                    client_address,
                    traceback.format_exc(),
                )


class RoutesServer(object):
    """Route server thread handler.

    It runs an HTTP server on the given host and port.

    Args:
        host (str): host
        port (int): port
    """

    def __init__(self, host, port):
        self.server = ThreadedHttpServer((host, port), HttpRequestHandler)
        self.host = host
        self.port = port
        self.start()

    def __str__(self):
        return "Routes server is listening on http://%s:%s" % (
            self.host or "0.0.0.0",
            self.port,
        )

    def __repr__(self):
        return "<RoutesServer @ http://%s:%s>" % (self.host or "0.0.0.0", self.port)

    def start(self):
        """Start the accept loop, at most once, on a guarded thread.

        Activation starts each server more than once, which left a second
        accept loop running against the same socket that nothing tracked and
        shutdown never joined. The thread is guarded because an exception
        escaping it terminates Revit; see the ``ThreadedHttpServer`` docstring.
        """
        existing = getattr(self, "server_thread", None)
        if existing is not None and existing.is_alive():
            return

        def serve_forever_guarded():
            try:
                self.server.serve_forever()
            except Exception:
                mlogger.debug("Routes server loop exited | %s", traceback.format_exc())

        self.server_thread = threading.Thread(target=serve_forever_guarded)
        self.server_thread.daemon = True
        self.server_thread.start()

    def waitForThread(self):
        self.server_thread.join()

    def stop(self):
        self.server.shutdown()
        self.waitForThread()
