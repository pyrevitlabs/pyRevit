'''
rpshttpserver.py - a web server example that runs inside Autodesk Revit

this example shows how to create an http REST API to Autodesk Revit.
'''
import traceback

from System import AsyncCallback
from System.Net import HttpListener, HttpListenerException, HttpListenerContext
from System.Threading import Thread, ThreadStart
from System.Text import Encoding

from Autodesk.Revit.UI import ExternalEvent, IExternalEventHandler

def main():
    try:
        contexts = ContextQueue()
        eventHandler = RpsEventHandler(contexts)
        externalEvent = ExternalEvent.Create(eventHandler)
        server = RpsServer(externalEvent=externalEvent, contexts=contexts)
        serverThread = Thread(ThreadStart(server.serve_forever))
        serverThread.Start()

        def closing(s, a):
            server.stop()
            return
        __window__.FormClosing += closing

    except:
        import traceback
        traceback.print_exc()


class ContextQueue(object):
    def __init__(self):
        from System.Collections.Concurrent import ConcurrentQueue
        self.contexts = ConcurrentQueue[HttpListenerContext]()

    def __len__(self):
        return len(self.contexts)

    def append(self, c):
        self.contexts.Enqueue(c)

    def pop(self):
        success, context = self.contexts.TryDequeue()
        if success:
            return context
        else:
            raise Exception("can't pop an empty ContextQueue!")


class RpsEventHandler(IExternalEventHandler):
    def __init__(self, contexts):
        self.contexts = contexts
        self.handlers = {
            'schedules': get_schedules
            # add other handlers here
        }

    def Execute(self, uiApplication):
        print 'inside RpsEventHandler'
        try:
            while self.contexts:
                context = self.contexts.pop()
                request = context.Request
                parts = request.RawUrl.split('/')[1:]
                handler = parts[0]  # FIXME: add error checking here!
                args = parts[1:]
                try:
                    rc, ct, data = self.handlers[handler](args, uiApplication)
                except:
                    rc = 404
                    ct = 'text/plain'
                    data = traceback.format_exc()
                if rc == 302:
                    context.Response.Redirect('/'.join(request.RawUrl.split('/')[:2]) + '/' + data)
                else:
                    response = context.Response
                    response.ContentType = ct
                    response.StatusCode = rc
                    buffer = Encoding.UTF8.GetBytes(data)
                    response.ContentLength64 = buffer.Length
                    output = response.OutputStream
                    output.Write(buffer, 0, buffer.Length)
                    output.Close()
        except:
            traceback.print_exc()

def get_schedules(args, uiApplication):
    '''add code to get a specific schedule by name here'''
    print 'inside get_schedules...'
    from Autodesk.Revit.DB import ViewSchedule
    from Autodesk.Revit.DB import FilteredElementCollector
    from Autodesk.Revit.DB import ViewScheduleExportOptions
    import tempfile, os, urllib

    doc = uiApplication.ActiveUIDocument.Document
    collector = FilteredElementCollector(doc).OfClass(ViewSchedule)
    schedules = {vs.Name: vs for vs in list(collector)}

    if len(args):
        # export a single schedule
        schedule_name = urllib.unquote(args[0])
        if not schedule_name.lower().endswith('.csv'):
            return 302, None, schedule_name + '.csv'
        schedule_name = schedule_name[:-4]
        if not schedule_name in schedules.keys():
            return 404, 'text/plain', 'Schedule not found: %s' % schedule_name
        schedule = schedules[schedule_name]
        fd, fpath = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        dname, fname = os.path.split(fpath)
        opt = ViewScheduleExportOptions()
        opt.FieldDelimiter = ', '
        schedule.Export(dname, fname, opt)
        with open(fpath, 'r') as csv:
            result = csv.read()
        os.unlink(fpath)
        return 200, 'text/csv', result
    else:
        return 200, 'text/plain', '\n'.join(schedules.keys())


class RpsServer(object):
    def __init__(self, externalEvent, contexts, port=8080):
        self.port = port
        self.externalEvent = externalEvent
        self.contexts = contexts

    def serve_forever(self):
        try:
            self.running = True
            self.listener = HttpListener()
            prefix = 'http://localhost:%i/' % self.port
            self.listener.Prefixes.Add(prefix)
            try:
                print 'starting listener', prefix
                self.listener.Start()
                print 'started listener'
            except HttpListenerException as ex:
                print 'HttpListenerException:', ex
                return
            waiting = False
            while self.running:
                if not waiting:
                    context = self.listener.BeginGetContext(
                        AsyncCallback(self.handleRequest),
                        self.listener)
                waiting = not context.AsyncWaitHandle.WaitOne(100)
        except:
            traceback.print_exc()

    def stop(self):
        print 'stop()'
        self.running = False
        self.listener.Stop()
        self.listener.Close()

    def handleRequest(self, result):
        '''
        pass the request to the RevitEventHandler
        '''
        try:
            listener = result.AsyncState
            if not listener.IsListening:
                return
            try:
                context = listener.EndGetContext(result)
            except:
                # Catch the exception when the thread has been aborted
                self.stop()
                return
            self.contexts.append(context)
            self.externalEvent.Raise()
            print 'raised external event'
        except:
            traceback.print_exc()

if __name__ == '__main__':
    main()

