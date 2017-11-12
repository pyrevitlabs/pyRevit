import threading
import argparse
import re
import cgi
import json
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn
from functools import wraps

from pyrevit import framework
from pyrevit import revit, DB, UI


def select(appui, elements_list):
    ells = [DB.ElementId(x) for x in elements_list]
    appui.ActiveUIDocument.Selection.SetElementIds(framework.List[DB.ElementId](ells))


def messagebox(appui, data):
    UI.TaskDialog.Show('http server', 'some message')


class HTTPExternalEventHandler(UI.IExternalEventHandler):
    target_view = None
    data = None
    view_funcs = {'select': select,
                  'msgbox': messagebox}

    def Execute(self, appui):
        f = self.view_funcs.get(self.target_view)
        if f:
            f(appui, self.data)

    def GetName(self):
        return "HTTPExternalEventHandler"


evt = HTTPExternalEventHandler()
exevent = UI.ExternalEvent.Create(evt)


class HTTPRequestHandler(BaseHTTPRequestHandler):
  def do_POST(self):
    if None != re.search('/api/v1/select/*', self.path):
      ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
      if ctype == 'application/json':
        length = int(self.headers.getheader('content-length'))
        data = json.loads(self.rfile.read(length))
        try:
            evt.target_view = 'select'
            evt.data = data['elements']
            exevent.Raise()
        except Exception as e:
            msg = str(e)
      else:
        data = {}
      self.send_response(200)
      self.send_header('Content-Type', 'application/txt')
      self.end_headers()
      self.wfile.write(msg)
    elif None != re.search('/api/v1/message/*', self.path):
      evt.target_view = 'msgbox'
      exevent.Raise()
      self.send_response(200)
      self.end_headers()
    else:
      self.send_response(403)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
    return

  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write('{"name":"ehsan"}')
    return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  allow_reuse_address = True

  def shutdown(self):
    self.socket.close()
    HTTPServer.shutdown(self)

class SimpleHttpServer():
  def __init__(self, ip, port):
    self.server = ThreadedHTTPServer((ip,port), HTTPRequestHandler)

  def start(self):
    self.server_thread = threading.Thread(target=self.server.serve_forever)
    self.server_thread.daemon = True
    self.server_thread.start()

  def waitForThread(self):
    self.server_thread.join()

  def stop(self):
    self.server.shutdown()
    self.waitForThread()


def start():
    SimpleHttpServer('', 48884).start()
    #server.waitForThread()


def route(target_url):
    def wrap(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapped_f
    return wrap
