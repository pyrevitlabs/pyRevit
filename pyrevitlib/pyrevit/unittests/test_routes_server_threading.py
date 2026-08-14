# -*- coding: utf-8 -*-
"""Tests for the threaded routes server request path.

Requests are served on threads that are never STA while pyRevit directs
stderr to its script output console, a WPF window that can only be created
on Revit's STA UI thread. An exception escaping a serving thread is printed
there and terminates the Revit process.

``ThreadedHttpServer.process_request_thread`` must therefore contain every
failure on the request path, including the per-request cleanup that runs on
an already closed socket after the server has been stopped.
"""

import socket
import sys
import threading
import unittest

from pyrevit.routes.server import server


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
