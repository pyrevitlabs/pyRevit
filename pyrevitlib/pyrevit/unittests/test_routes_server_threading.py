# -*- coding: utf-8 -*-
"""Tests for the threaded routes server request path.

Requests are served on threads that are never STA while pyRevit directs
stderr to its script output console, a WPF window that can only be created
on Revit's STA UI thread. An exception escaping a serving thread is printed
there and terminates the Revit process.

``ThreadedHttpServer.process_request_thread`` must therefore contain every
failure on the request path, including the per-request cleanup that runs on
an already closed socket after the server has been stopped.

Access logging runs on those same threads, so ``HttpRequestHandler`` must
report every request through ``mlogger`` and never reach stderr either.
"""

TEST_ENVIRONMENT = "Revit"
TEST_LEVEL = "Integration"


import socket
import sys
import threading
import time
import unittest

from pyrevit.routes.server import server
from pyrevit.routes.server import base, handler


class _RecordingLogger(object):
    """Minimal mlogger stand-in that records what would be logged."""

    def __init__(self):
        self.messages = []

    def debug(self, fmt, *args):
        self.messages.append(fmt % args if args else fmt)


class _RecordingStream(object):
    """Minimal stream stand-in that records what would be written."""

    def __init__(self):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)

    def flush(self):
        pass


class _FakeThreadedServer(server.ThreadedHttpServer):
    """ThreadedHttpServer stub that binds no socket.

    Only ``process_request_thread`` and the methods it calls are exercised,
    so ``HTTPServer.__init__`` is deliberately bypassed.
    """

    def __init__(self, finish_error=None, cleanup_error=None, report_error=None):
        # pylint: disable=super-init-not-called
        self.finish_error = finish_error
        self.cleanup_error = cleanup_error
        self.report_error = report_error
        self.finish_calls = []
        self.cleanup_calls = []
        self.reported_errors = []

    def finish_request(self, request, client_address):
        self.finish_calls.append((request, client_address))
        if self.finish_error is not None:
            raise self.finish_error

    def shutdown_request(self, request):
        self.cleanup_calls.append(request)
        if self.cleanup_error is not None:
            raise self.cleanup_error

    def handle_error(self, request, client_address):
        self.reported_errors.append((request, client_address))
        if self.report_error is not None:
            raise self.report_error


class _InheritedCleanupServer(server.ThreadedHttpServer):
    """ThreadedHttpServer stub that keeps the inherited cleanup path."""

    def __init__(self):
        # pylint: disable=super-init-not-called
        self.finish_calls = []

    def finish_request(self, request, client_address):
        self.finish_calls.append((request, client_address))


class _FakeRequestHandler(server.HttpRequestHandler):
    """HttpRequestHandler stub that serves no request.

    ``BaseHTTPRequestHandler.__init__`` reads and answers a request from a
    live socket, so it is deliberately bypassed; only the logging entry points
    are exercised. The attributes the inherited loggers read are set, so the
    stderr assertions below still hold if the override is ever dropped.
    """

    def __init__(self):
        # pylint: disable=super-init-not-called
        self.client_address = ("127.0.0.1", 5000)
        self.requestline = "GET /pyrevit-core/status HTTP/1.1"


class _LoggerPatchedTestCase(unittest.TestCase):
    """Base case that swaps the module logger for a recorder."""

    def setUp(self):
        self.logger = _RecordingLogger()
        self._original_mlogger = server.mlogger
        server.mlogger = self.logger

    def tearDown(self):
        server.mlogger = self._original_mlogger


class ProcessRequestThreadTests(_LoggerPatchedTestCase):
    """Tests for ThreadedHttpServer.process_request_thread."""

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_serves_request_and_runs_cleanup(self):
        """A successful request is served and its socket cleaned up."""
        http_server = _FakeThreadedServer()

        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual([("request", ("127.0.0.1", 5000))], http_server.finish_calls)
        self.assertEqual(["request"], http_server.cleanup_calls)
        self.assertEqual([], http_server.reported_errors)

    # ------------------------------------------------------------------
    # Cleanup on an already closed socket (the reload crash)
    # ------------------------------------------------------------------

    def test_cleanup_failure_on_closed_socket_does_not_escape(self):
        """Cleanup raising on a closed socket must not escape the thread."""
        http_server = _FakeThreadedServer(
            cleanup_error=socket.error("[Errno 9] Bad file descriptor")
        )

        # must not raise
        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual(["request"], http_server.cleanup_calls)

    def test_cleanup_failure_of_any_type_does_not_escape(self):
        """Cleanup failures are contained whatever exception type is raised."""
        for error in (
            socket.error("closed socket"),
            ValueError("socket is closed"),
            RuntimeError("cannot access a disposed object"),
        ):
            http_server = _FakeThreadedServer(cleanup_error=error)

            # must not raise
            http_server.process_request_thread("request", ("127.0.0.1", 5000))

            self.assertEqual(["request"], http_server.cleanup_calls)

    def test_cleanup_failure_is_not_reported_as_a_request_error(self):
        """A served request is not reported as failed when cleanup raises."""
        http_server = _FakeThreadedServer(cleanup_error=socket.error("closed socket"))

        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual([], http_server.reported_errors)

    def test_inherited_cleanup_runs_against_a_closed_socket(self):
        """The inherited cleanup path is safe on a genuinely closed socket."""
        http_server = _InheritedCleanupServer()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.close()

        # must not raise
        http_server.process_request_thread(sock, ("127.0.0.1", 5000))

        self.assertEqual(1, len(http_server.finish_calls))

    # ------------------------------------------------------------------
    # Failures while serving the request
    # ------------------------------------------------------------------

    def test_request_failure_is_reported(self):
        """A request that raises is routed to handle_error."""
        http_server = _FakeThreadedServer(finish_error=ValueError("boom"))

        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual(
            [("request", ("127.0.0.1", 5000))], http_server.reported_errors
        )

    def test_request_failure_still_runs_cleanup(self):
        """Cleanup runs even when serving the request raised."""
        http_server = _FakeThreadedServer(finish_error=ValueError("boom"))

        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual(["request"], http_server.cleanup_calls)

    def test_request_and_cleanup_failures_are_both_contained(self):
        """Nothing escapes when both the request and its cleanup raise."""
        http_server = _FakeThreadedServer(
            finish_error=ValueError("boom"),
            cleanup_error=socket.error("closed socket"),
        )

        # must not raise
        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual(1, len(http_server.reported_errors))
        self.assertEqual(["request"], http_server.cleanup_calls)

    def test_error_reporting_failure_does_not_escape(self):
        """A failure inside handle_error must not escape either."""
        http_server = _FakeThreadedServer(
            finish_error=ValueError("boom"),
            report_error=RuntimeError("logging service is gone"),
        )

        # must not raise
        http_server.process_request_thread("request", ("127.0.0.1", 5000))

        self.assertEqual(["request"], http_server.cleanup_calls)

    # ------------------------------------------------------------------
    # Nothing on the request path may reach stderr
    # ------------------------------------------------------------------

    def test_nothing_is_written_to_stderr(self):
        """Serving and cleanup failures must never reach stderr."""
        http_server = _FakeThreadedServer(
            finish_error=ValueError("boom"),
            cleanup_error=socket.error("closed socket"),
        )
        recorder = _RecordingStream()
        original_stderr = sys.stderr
        sys.stderr = recorder
        try:
            http_server.process_request_thread("request", ("127.0.0.1", 5000))
        finally:
            sys.stderr = original_stderr

        self.assertEqual([], recorder.writes)

    # ------------------------------------------------------------------
    # The guard holds on an actual serving thread
    # ------------------------------------------------------------------

    def test_no_exception_escapes_the_serving_thread(self):
        """Run on a thread as the server does; nothing may escape it."""
        http_server = _FakeThreadedServer(
            finish_error=ValueError("boom"),
            cleanup_error=socket.error("closed socket"),
            report_error=RuntimeError("logging service is gone"),
        )
        escaped = []

        def serve():
            try:
                http_server.process_request_thread("request", ("127.0.0.1", 5000))
            except BaseException as exc:  # pylint: disable=broad-except
                escaped.append(exc)

        thread = threading.Thread(target=serve)
        thread.daemon = True
        thread.start()
        thread.join(5)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], escaped)


class HandleErrorTests(_LoggerPatchedTestCase):
    """Tests for ThreadedHttpServer.handle_error."""

    def test_reports_through_the_logger(self):
        """Request errors are recorded through mlogger, not printed."""
        http_server = _FakeThreadedServer()

        server.ThreadedHttpServer.handle_error(
            http_server, "request", ("127.0.0.1", 5000)
        )

        self.assertEqual(1, len(self.logger.messages))
        self.assertIn("127.0.0.1", self.logger.messages[0])

    def test_does_not_write_to_stderr(self):
        """handle_error must not reach the script output console."""
        http_server = _FakeThreadedServer()
        recorder = _RecordingStream()
        original_stderr = sys.stderr
        sys.stderr = recorder
        try:
            try:
                raise ValueError("boom")
            except ValueError:
                server.ThreadedHttpServer.handle_error(
                    http_server, "request", ("127.0.0.1", 5000)
                )
        finally:
            sys.stderr = original_stderr

        self.assertEqual([], recorder.writes)


class LogMessageTests(_LoggerPatchedTestCase):
    """Tests for HttpRequestHandler.log_message."""

    def test_records_the_message_through_the_logger(self):
        """Request logging is recorded through mlogger, not printed."""
        request_handler = _FakeRequestHandler()

        request_handler.log_message('"%s" %s', "GET /status HTTP/1.1", 200)

        self.assertEqual(1, len(self.logger.messages))
        self.assertIn("Routes request from 127.0.0.1 |", self.logger.messages[0])
        self.assertIn('"GET /status HTTP/1.1" 200', self.logger.messages[0])

    def test_does_not_write_to_stderr(self):
        """log_message must not reach the script output console."""
        request_handler = _FakeRequestHandler()
        recorder = _RecordingStream()
        original_stderr = sys.stderr
        sys.stderr = recorder
        try:
            request_handler.log_message('"%s" %s', "GET /status HTTP/1.1", 200)
        finally:
            sys.stderr = original_stderr

        self.assertEqual([], recorder.writes)

    def test_served_and_rejected_requests_both_stay_off_stderr(self):
        """Every inherited logging entry point goes through the override."""
        request_handler = _FakeRequestHandler()
        recorder = _RecordingStream()
        original_stderr = sys.stderr
        sys.stderr = recorder
        try:
            request_handler.log_request(200, 15)
            request_handler.log_error("code %d, message %s", 400, "Bad request")
        finally:
            sys.stderr = original_stderr

        self.assertEqual([], recorder.writes)
        self.assertEqual(2, len(self.logger.messages))
        self.assertIn("GET /pyrevit-core/status HTTP/1.1", self.logger.messages[0])


class _ApiIdlingEvent(object):
    def __init__(self):
        self.handlers = []

    def __iadd__(self, callback):
        self.handlers.append(callback)
        return self

    def __isub__(self, callback):
        self.handlers.remove(callback)
        return self


class _ApiUiApplication(object):
    def __init__(self):
        self.Idling = _ApiIdlingEvent()


class _CoalescingExternalEvent(object):
    """Coalesce all raises until a separate host thread is allowed to execute."""

    def __init__(self, dispatcher, expected):
        self.dispatcher = dispatcher
        self.expected = expected
        self.raised = threading.Event()
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.count = 0
        self.thread = None
        self.uiapp = _ApiUiApplication()
        self.dispose_calls = 0

    def Raise(self):
        with self.lock:
            self.count += 1
            if self.thread is None:
                self.thread = threading.Thread(target=self._execute)
                self.thread.daemon = True
                self.thread.start()
                result = server.UI.ExternalEventRequest.Accepted
            else:
                result = server.UI.ExternalEventRequest.Pending
            if self.count == self.expected:
                self.raised.set()
            return result

    def _execute(self):
        if self.release.wait(5):
            self.dispatcher.Execute(self.uiapp)
            for callback in list(self.uiapp.Idling.handlers):
                callback(None, None)

    def Dispose(self):
        self.dispose_calls += 1


class _ApiHttpServer(object):
    """Own the dispatcher and external event without opening a socket."""

    def __init__(self, expected):
        self.request_handler = handler.RequestHandler()
        self.external_event = _CoalescingExternalEvent(self.request_handler, expected)
        self.request_handler.external_event = self.external_event


class ApiRequestQueueTests(unittest.TestCase):
    """Each API request owns its completion even when Revit coalesces events."""

    def _concurrent_requests(self, failing=None, count=20, per_item=0):
        http_server = _ApiHttpServer(count)
        calls = []
        responses = {}
        failures = []
        lock = threading.Lock()

        def route(request, uiapp):
            with lock:
                calls.append(request.path)
            if per_item:
                time.sleep(per_item)
            if request.path == failing:
                raise ValueError("isolated handler failure")
            return request.path

        def send(index):
            try:
                request_handler = _FakeRequestHandler()
                request_handler.server = http_server
                request = base.Request(path="/%s" % index)
                response = request_handler._call_host_event_sync(request, route)
                with lock:
                    responses[request.path] = response
            except Exception as error:
                with lock:
                    failures.append(error)

        threads = [
            threading.Thread(target=send, args=(index,)) for index in range(count)
        ]
        for thread in threads:
            thread.daemon = True
            thread.start()
        try:
            self.assertTrue(http_server.external_event.raised.wait(5))
            http_server.external_event.release.set()
            for thread in threads:
                thread.join(5)
                self.assertFalse(thread.is_alive())
            self.assertEqual([], failures)
            self.assertEqual(count, len(calls))
            self.assertEqual(count, len(set(calls)))
            self.assertEqual(count, len(responses))
            for path, response in responses.items():
                if path == failing:
                    self.assertEqual(500, response.status)
                else:
                    self.assertEqual(path, response)
        finally:
            http_server.request_handler.stop()
            http_server.external_event.release.set()
            for thread in threads:
                thread.join(1)
            if http_server.external_event.thread is not None:
                http_server.external_event.thread.join(5)

    def test_concurrent_requests_have_independent_responses(self):
        """One coalesced Execute handles every concurrent request exactly once."""
        self._concurrent_requests()

    def test_handler_failure_does_not_affect_other_requests(self):
        """A failed route cannot stop draining or replace another response."""
        self._concurrent_requests(failing="/7")

    def test_draining_queue_does_not_time_out_late_items(self):
        """A deep queue keeps all eight results while Revit makes progress."""
        original_timeout = server.API_REQUEST_TIMEOUT
        server.API_REQUEST_TIMEOUT = 0.15
        try:
            self._concurrent_requests(count=8, per_item=0.05)
        finally:
            server.API_REQUEST_TIMEOUT = original_timeout

    def test_callback_queue_rejects_over_capacity(self):
        """Callback requests cannot accumulate without bound while Revit is busy."""
        dispatcher = handler.RequestHandler()
        for index in range(handler.MAX_PENDING_REQUESTS):
            item = handler.RequestWorkItem(
                base.Request(
                    path="/%s" % index, data={"callbackUrl": "http://callback/"}
                ),
                lambda request, uiapp: None,
            )
            self.assertIsNone(dispatcher.enqueue(item))
        rejected = handler.RequestWorkItem(
            base.Request(path="/full", data={"callbackUrl": "http://callback/"}),
            lambda request, uiapp: None,
        )
        self.assertEqual(503, dispatcher.enqueue(rejected).status)
        self.assertTrue(rejected.event.is_set())
        self.assertEqual(handler.MAX_PENDING_REQUESTS, len(dispatcher._queue))

    def test_callback_transport_has_a_finite_timeout(self):
        """Callbacks pass a finite socket timeout to the compatibility transport."""
        original = handler.make_request
        calls = []
        handler.make_request = lambda **kwargs: calls.append(kwargs)
        try:
            handler.RequestHandler.make_callback("http://callback/", "response")
            self.assertEqual(handler.CALLBACK_TIMEOUT, calls[0]["timeout"])
            self.assertGreater(calls[0]["timeout"], 0)
        finally:
            handler.make_request = original

    def test_execute_preparation_failure_is_server_error(self):
        """API setup failures are handler faults, not client request timeouts."""
        dispatcher = handler.RequestHandler()
        item = handler.RequestWorkItem(base.Request(), lambda request, uiapp: None)

        def fail(*args, **kwargs):
            raise ValueError("cannot prepare API context")

        dispatcher.prepare_handler_kwargs = fail
        dispatcher.enqueue(item)
        dispatcher.Execute(None)
        self.assertEqual(500, item.response.status)

    def test_timeout_is_http_error_and_late_execute_skips_cancelled_work(self):
        """A timed-out queued request is not executed or returned as HTTP 200."""
        http_server = _ApiHttpServer(1)
        request_handler = _FakeRequestHandler()
        request_handler.server = http_server
        calls = []
        original_timeout = server.API_REQUEST_TIMEOUT
        server.API_REQUEST_TIMEOUT = 0.01
        try:
            response = request_handler._call_host_event_sync(
                base.Request(), lambda request, uiapp: calls.append(request)
            )
            self.assertEqual(
                504, handler.RequestHandler.parse_response(response).status
            )
            http_server.external_event.release.set()
            http_server.external_event.thread.join(5)
            self.assertFalse(http_server.external_event.thread.is_alive())
            self.assertEqual([], calls)
        finally:
            server.API_REQUEST_TIMEOUT = original_timeout
            http_server.request_handler.stop()
            http_server.external_event.release.set()

    def test_callback_failure_does_not_interrupt_queue(self):
        """Callback requests share the queue and a failed callback is contained."""
        dispatcher = handler.RequestHandler()
        calls = []
        callbacks = []

        def route(request, uiapp):
            calls.append(request.path)
            return request.path

        def callback(url, response):
            callbacks.append((url, response))
            raise ValueError("callback unavailable")

        dispatcher.make_callback = callback
        http_server = _ApiHttpServer(2)
        http_server.request_handler = dispatcher
        http_server.external_event.dispatcher = dispatcher
        dispatcher.external_event = http_server.external_event
        request_handler = _FakeRequestHandler()
        request_handler.server = http_server
        first = handler.RequestWorkItem(
            base.Request(path="/callback", data={"callbackUrl": "http://callback/"}),
            route,
        )
        second = handler.RequestWorkItem(base.Request(path="/sync"), route)
        self.assertIsNone(request_handler._call_host_event(first))
        self.assertIsNone(request_handler._call_host_event(second))
        try:
            self.assertTrue(http_server.external_event.raised.wait(5))
            http_server.external_event.release.set()
            self.assertTrue(second.event.wait(5))
            http_server.external_event.thread.join(5)
            self.assertEqual(["/callback", "/sync"], calls)
            self.assertEqual([("http://callback/", "/callback")], callbacks)
            self.assertEqual("/callback", first.response)
            self.assertEqual("/sync", second.response)
        finally:
            dispatcher.stop()
            http_server.external_event.release.set()

    def test_running_request_waits_for_its_actual_result(self):
        """The queue timeout must not reject work already executing in Revit."""
        http_server = _ApiHttpServer(1)
        dispatcher = http_server.request_handler
        entered = threading.Event()
        release = threading.Event()
        cancel_attempted = threading.Event()
        responses = []
        original_timeout = server.API_REQUEST_TIMEOUT
        original_cancel = dispatcher.cancel
        server.API_REQUEST_TIMEOUT = 0.01

        def slow_route(request, uiapp):
            entered.set()
            release.wait(5)
            return "actual response"

        def cancel(item, response, progress_count=None):
            cancelled = original_cancel(item, response, progress_count)
            cancel_attempted.set()
            return cancelled

        def send():
            request_handler = _FakeRequestHandler()
            request_handler.server = http_server
            responses.append(
                request_handler._call_host_event_sync(base.Request(), slow_route)
            )

        dispatcher.cancel = cancel
        http_server.external_event.release.set()
        thread = threading.Thread(target=send)
        thread.daemon = True
        thread.start()
        try:
            self.assertTrue(entered.wait(5))
            self.assertTrue(cancel_attempted.wait(5))
            self.assertTrue(thread.is_alive())
            self.assertEqual([], responses)
            second = handler.RequestWorkItem(
                base.Request(), lambda request, uiapp: "second response"
            )
            self.assertIsNone(dispatcher.enqueue(second))
            release.set()
            self.assertTrue(second.event.wait(5))
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(["actual response"], responses)
            self.assertEqual("second response", second.response)
        finally:
            server.API_REQUEST_TIMEOUT = original_timeout
            dispatcher.stop()
            release.set()
            thread.join(5)
            if http_server.external_event.thread is not None:
                http_server.external_event.thread.join(5)

    def test_fast_callback_error_still_acknowledges_with_no_content(self):
        """A completed callback route never returns its handler response twice."""
        http_server = _ApiHttpServer(1)
        dispatcher = http_server.request_handler
        callbacks = []
        responses = []
        request = base.Request(data={"callbackUrl": "http://callback/"})

        def route(request, uiapp):
            return base.Response(status=409, data="route response")

        def callback(url, response):
            callbacks.append((url, response.status))

        def raise_immediately():
            dispatcher.Execute(http_server.external_event.uiapp)
            return server.UI.ExternalEventRequest.Accepted

        dispatcher.make_callback = callback
        http_server.external_event.Raise = raise_immediately
        request_handler = _FakeRequestHandler()
        request_handler.server = http_server
        request_handler._parse_request_info = lambda: ("api", "/", "")
        request_handler._find_route_handler = lambda *args: (None, route)
        request_handler._prepare_request = lambda *args: request
        request_handler._write_response = responses.append
        try:
            request_handler._handle_route("GET")
            self.assertEqual([204], [response.status for response in responses])
            self.assertEqual([("http://callback/", 409)], callbacks)
        finally:
            dispatcher.stop()

    def test_host_rejections_use_standard_exception_response(self):
        """Denied and timed-out events preserve routes' JSON exception contract."""
        for result, status in (
            (server.UI.ExternalEventRequest.Denied, 503),
            (server.UI.ExternalEventRequest.TimedOut, 504),
        ):
            http_server = _ApiHttpServer(1)
            http_server.external_event.Raise = lambda: result
            request_handler = _FakeRequestHandler()
            request_handler.server = http_server
            item = handler.RequestWorkItem(
                base.Request(path="/rejected"), lambda request, uiapp: None
            )
            rejection = request_handler._call_host_event(item)
            self.assertIsNotNone(rejection)
            self.assertTrue(item.event.wait(0.1))
            parsed = handler.RequestHandler.parse_response(rejection)
            self.assertEqual(status, parsed.status)
            self.assertIn('"exception"', parsed.data)
            self.assertIn("/rejected", parsed.data)
            http_server.request_handler.stop()
