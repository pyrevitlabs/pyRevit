"""Routes HTTP Server."""
#pylint: disable=import-error,invalid-name,broad-except
import cgi
import json
import threading
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn

from pyrevit.api import UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.routes import handler


mlogger = get_logger(__name__)


# create the base Revit external event handler
# upon Raise(), finds and runs the appropriate func
req_hndlr = handler.RequestHandler()
event_hndlr = UI.ExternalEvent.Create(req_hndlr)


class HttpRequestHandler(BaseHTTPRequestHandler):
    def _parse_path(self):
        if self.path:
            levels = self.path.split('/')
            if levels and len(levels) >= 2:
                app_name = levels[1]
                if len(levels) > 2:
                    route = '/' + '/'.join(levels[2:])
                else:
                    route = '/'
                return app_name, route
        return None, None

    def _handle_route(self, method):
        # find the app
        app_name, route = self._parse_path()
        if not app_name:
            return

        # configure the handler for this app
        req_hndlr.name = app_name
        req_hndlr.method = method
        req_hndlr.route = route

        # process request data
        content_type_header = self.headers.getheader('content-type')
        if content_type_header:
            content_type, _ = cgi.parse_header(content_type_header)
            if content_type == 'application/json':
                content = self.headers.getheader('content-length')
                req_hndlr.data = \
                    json.loads(self.rfile.read(int(content))) \
                        if content else None

        # execute handler
        try:
            event_hndlr.Raise()
            while event_hndlr.IsPending:
                pass
        except Exception as ex:
            self.send_response(500)
            self.send_header('Content-Type', 'application/txt')
            self.end_headers()
            self.wfile.write('[handle_route] {}'.format(str(ex)))
            return

        # prepare response
        self.send_response(req_hndlr.res_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        if req_hndlr.res_data:
            self.wfile.write(json.dumps(req_hndlr.res_data))
        else:
            self.wfile.write(json.dumps({}))

    def _process_request(self, method):
        try:
            self._handle_route(method=method)
        except Exception as ex:
            self.send_response(500)
            self.send_header('Content-Type', 'application/txt')
            self.end_headers()
            self.wfile.write('[process_request] {}'.format(str(ex)))

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
