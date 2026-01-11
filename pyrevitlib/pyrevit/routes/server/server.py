# -*- coding: utf-8 -*-
"""Routes HTTP Server."""
#pylint: disable=import-error,invalid-name,broad-except
#pylint: disable=missing-docstring
import sys
import traceback
import cgi
import json
import threading

from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger
from pyrevit.compat import PY3
from pyrevit.compat import urlparse

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
    def _parse_api_path(self):
        url_parts = urlparse(self.path)
        if url_parts:
            levels = url_parts.path.split('/')
            # host:ip/<api_name>/<route>/.../.../...
            if levels and len(levels) >= 2:
                api_name = levels[1]
                if len(levels) > 2:
                    api_path = '/' + '/'.join(levels[2:])
                else:
                    api_path = '/'
                return api_name, api_path
        return None, None

    def _parse_request_info(self):
        # find the app
        api_name, api_path = self._parse_api_path() #type:str, str
        if not api_name:
            raise excp.APINotDefinedException(api_name)
        return api_name, api_path

    def _find_route_handler(self, api_name, path, method):
        route, route_handler = router.get_route_handler(
            api_name=api_name,
            path=path,
            method=method
            )
        if not route_handler:
            raise excp.RouteHandlerNotDefinedException(api_name, path, method)
        return route, route_handler

    def _prepare_request(self, route, path, method):
        # process request data
        data = None
        content_length = self.headers.getheader('content-length') # type: str
        if content_length and content_length.isnumeric():
            data = self.rfile.read(int(content_length))
            # format data
            content_type_header = self.headers.getheader('content-type')
            if content_type_header:
                content_type, _ = cgi.parse_header(content_type_header)
                if content_type == 'application/json':
                    data = json.loads(data)

        return base.Request(
            path=path,
            method=method,
            data=data,
            params=router.extract_route_params(route.pattern, path)
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
        if r.headers:
            for key, value in r.headers.items():
                self.send_header(key, value)
            self.end_headers()
        # sending \n if no data otherwise Postman panics for some reason
        self.wfile.write(r.data or "\n")

    def _handle_route(self, method):
        # process the given url and find API and route
        api_name, path = self._parse_request_info()

        # find the handler function registered by the API and route
        route, route_handler = self._find_route_handler(api_name, path, method)

        # prepare a request obj to be passed to registered handler
        request = self._prepare_request(route, path, method)

        # if handler has uiapp in arguments, run in host api context
        if handler.RequestHandler.wants_api_context(route_handler):
            # create a handler and event object in host
            req_hndlr, event_hndlr = \
                self._prepare_host_handler(request, route_handler)

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
            response = \
                handler.RequestHandler.run_handler(
                    handler=route_handler,
                    kwargs=handler.RequestHandler.prepare_handler_kwargs(
                        request=request,
                        handler=route_handler
                    )
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
            sys.exc_type, sys.exc_value, sys.exc_traceback = \
                sys.exc_info()
            # go back one frame to grab exception stack from handler
            # and grab traceback lines
            tb_report = ''.join(
                traceback.format_tb(sys.exc_traceback)[1:]
            )
            self._write_response(
                excp.ServerException(
                    message=str(ex),
                    exception_type=sys.exc_type,
                    exception_traceback=tb_report
                )
            )

    # CRUD Methods ------------------------------------------------------------
    # create
    def do_POST(self):
        self._process_request(method='POST')

    # read
    def do_GET(self):
        self._process_request(method='GET')

    # update
    def do_PUT(self):
        self._process_request(method='PUT')

    # delete
    def do_DELETE(self):
        self._process_request(method='DELETE')

    # rest of standard http methods -------------------------------------------
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods
    def do_HEAD(self):
        self._process_request(method='HEAD')

    def do_CONNECT(self):
        self._process_request(method='CONNECT')

    def do_OPTIONS(self):
        self._process_request(method='OPTIONS')

    def do_TRACE(self):
        self._process_request(method='TRACE')

    def do_PATCH(self):
        self._process_request(method='PATCH')


class ThreadedHttpServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server."""
    allow_reuse_address = True

    def shutdown(self):
        self.socket.close()
        HTTPServer.shutdown(self)


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
        return "Routes server is listening on http://%s:%s" \
            % (self.host or "0.0.0.0", self.port)

    def __repr__(self):
        return '<RoutesServer @ http://%s:%s>' \
            % (self.host or "0.0.0.0", self.port)

    def start(self):
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def waitForThread(self):
        self.server_thread.join()

    def stop(self):
        self.server.shutdown()
        self.waitForThread()
