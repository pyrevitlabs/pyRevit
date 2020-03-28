"""Routes HTTP Server."""
#pylint: disable=import-error,invalid-name,broad-except
import cgi
import json
import threading
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn

from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.routes import exceptions
from pyrevit.routes import router
from pyrevit.routes import handler


mlogger = get_logger(__name__)


# create the base Revit external event handler
# upon Raise(), finds and runs the appropriate func
lock = threading.Lock()
req_hndlr = handler.RequestHandler()
req_hndlr.lock = lock
event_hndlr = UI.ExternalEvent.Create(req_hndlr)


class Request(object):
    # TODO: implement headers and other stuff
    def __init__(self, name, route='/', method='GET', data=None):
        self.name = name
        self.route = route
        self.method = method
        self.data = data


class Response(object):
    # TODO: implement headers and other stuff
    def __init__(self, code='200', data=None):
        self.code = code
        self.data = data


class HttpRequestHandler(BaseHTTPRequestHandler):
    def _parse_path(self):
        if self.path:
            levels = self.path.split('/')
            # host:ip/<api_name>/<route>/.../.../...
            if levels and len(levels) >= 2:
                api_name = levels[1]
                if len(levels) > 2:
                    route = '/' + '/'.join(levels[2:])
                else:
                    route = '/'
                return api_name, route
        return None, None

    def _write_error(self, err_msg, res_code=500):
        self.send_response(res_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(
            {
                "exception": {
                    "source": "pyrevit routes server",
                    "message": err_msg
                }
            }
        ))

    def _handle_route(self, method):
        # find the app
        api_name, route = self._parse_path()
        if not api_name:
            raise exceptions.APINotDefinedException()

        route_handler = router.get_route(
            api_name=api_name,
            route=route,
            method=method
            )
        if not route_handler:
            raise exceptions.RouteHandlerNotDefinedException()

        req_hndlr.handler = route_handler

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

        # configure the handler for this app
        req_hndlr.request = \
            Request(
                name=api_name,
                route=route,
                method=method,
                data=data
            )

        # raise request to host
        # TODO: check for ExternalEventRequest
        event_hndlr.Raise()

        # wait until event has been picked up by host for execution
        while event_hndlr.IsPending:
            pass

        # wait until handler signals completion
        while True:
            with lock:
                if req_hndlr.done:
                    break

        # prepare response
        if isinstance(req_hndlr.response, Response):
            self.send_response(req_hndlr.response.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps(req_hndlr.response.data)
                )
        elif isinstance(req_hndlr.response, str):
            self.send_response(200)
            self.send_header('Content-Type','text/html')
            self.end_headers()
            self.wfile.write(req_hndlr.response)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps(req_hndlr.response)
                )

    def _process_request(self, method):
        try:
            self._handle_route(method=method)
        except exceptions.APINotDefinedException as api_ex:
            self._write_error(
                err_msg=str(api_ex),
                res_code=404
                )
        except exceptions.RouteHandlerNotDefinedException as route_ex:
            self._write_error(
                err_msg=str(route_ex),
                res_code=404
                )
        except Exception as ex:
            self._write_error(
                err_msg=str(ex)
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
    allow_reuse_address = True

    def shutdown(self):
        self.socket.close()
        HTTPServer.shutdown(self)


class RoutesServer(object):
    def __init__(self, ip, port):
        self.server = ThreadedHttpServer((ip, port), HttpRequestHandler)
        self.start()

    def start(self):
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def waitForThread(self):
        self.server_thread.join()

    def stop(self):
        self.server.shutdown()
        self.waitForThread()
