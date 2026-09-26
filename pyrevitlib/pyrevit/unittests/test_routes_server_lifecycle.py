# -*- coding: utf-8 -*-
"""Tests for the routes server lifecycle across a session reload.

A reload tears the session down and builds a new one on a worker thread, so
every step exercised here runs off Revit's STA UI thread, where an escaping
exception terminates the host. Two properties matter:

* stopping must not raise, and must release the port whatever else fails - a
  port left bound is a port the reloaded session cannot rebind;
* the registration must be cleared even when the stop failed, otherwise the
  next activation hands the dead server back instead of binding, and the
  reloaded session silently serves no routes at all.

Both were lost in the reload that killed Revit (#3473). Nothing on this path may
write to stderr either, for the reason the request path may not: an exception
printed off a worker thread is what terminated the process.
"""

import sys
import unittest

from pyrevit.coreutils import envvars
from pyrevit.routes import server as routes
from pyrevit.routes.server import server as routes_server
from pyrevit.routes.server import serverinfo


class _RecordingLogger(object):
    """Minimal mlogger stand-in that records what would be logged."""

    def __init__(self):
        self.records = []

    def _record(self, level, fmt, args):
        self.records.append((level, fmt % args if args else fmt))

    def debug(self, fmt, *args):
        self._record("debug", fmt, args)

    def info(self, fmt, *args):
        self._record("info", fmt, args)

    def error(self, fmt, *args, **kwargs):
        self._record("error", fmt, args)

    def has_errors(self):
        return any(level == "error" for level, _ in self.records)


class _RecordingStream(object):
    """Minimal stream stand-in that records what would be written."""

    def __init__(self):
        self.writes = []

    def write(self, payload):
        self.writes.append(payload)

    def flush(self):
        pass


class _DeadThread(object):
    """Thread stand-in for an accept loop that already exited."""

    def is_alive(self):
        return False

    def join(self, timeout=None):
        return None


class _LiveThread(object):
    """Thread stand-in for an accept loop that is still up."""

    def is_alive(self):
        return True

    def join(self, timeout=None):
        return None


class _StubHttpServer(object):
    """ThreadedHttpServer stand-in whose shutdown/close can be made to fail."""

    def __init__(self, shutdown_error=None, close_error=None):
        self.shutdown_error = shutdown_error
        self.close_error = close_error
        self.shutdown_calls = 0
        self.close_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1
        if self.shutdown_error is not None:
            raise self.shutdown_error

    def server_close(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


class RoutesServerStopTests(unittest.TestCase):
    """Tests for RoutesServer.stop, which runs on the session reload thread."""

    def setUp(self):
        """Isolate the server module logger."""
        self.logger = _RecordingLogger()
        self._original_mlogger = routes_server.mlogger
        routes_server.mlogger = self.logger

    def tearDown(self):
        """Restore the server module logger."""
        routes_server.mlogger = self._original_mlogger

    @staticmethod
    def _make_routes_server(http_server=None, server_thread="live"):
        instance = routes_server.RoutesServer.__new__(routes_server.RoutesServer)
        instance.host = "127.0.0.1"
        instance.port = 12345
        instance.server = http_server or _StubHttpServer()
        if server_thread == "live":
            instance.server_thread = _LiveThread()
        elif server_thread == "dead":
            instance.server_thread = _DeadThread()
        else:
            instance.server_thread = None
        return instance

    def test_stop_joins_the_accept_loop_and_closes_the_socket(self):
        """A stop shuts the accept loop down, releases the socket and forgets the thread."""
        instance = self._make_routes_server()

        instance.stop()

        self.assertEqual(1, instance.server.shutdown_calls)
        self.assertEqual(1, instance.server.close_calls)
        self.assertIsNone(instance.server_thread)

    def test_stop_releases_the_port_even_when_shutdown_fails(self):
        """A failed shutdown must still release the listening socket."""
        instance = self._make_routes_server(
            http_server=_StubHttpServer(shutdown_error=OSError("bad file descriptor"))
        )

        # must not raise
        instance.stop()

        self.assertEqual(1, instance.server.close_calls)

    def test_stop_contains_failures_of_either_kind(self):
        """Shutdown and close failures are contained whatever exception type is raised."""
        for error in (
            OSError("bad file descriptor"),
            ValueError("socket is closed"),
            RuntimeError("cannot access a disposed object"),
        ):
            instance = self._make_routes_server(
                http_server=_StubHttpServer(shutdown_error=error, close_error=error)
            )

            # must not raise
            instance.stop()

    def test_stop_does_not_wait_on_a_dead_accept_loop(self):
        """An exited accept loop can never acknowledge, so the stop must skip the wait."""
        instance = self._make_routes_server(server_thread="dead")

        # must not raise, and must not block waiting for a shutdown
        # acknowledgement that a dead loop can never send
        instance.stop()

        self.assertEqual(0, instance.server.shutdown_calls)
        self.assertEqual(1, instance.server.close_calls)

    def test_stop_does_not_wait_on_a_server_that_never_started(self):
        """A server whose accept loop never started must still be releasable."""
        instance = self._make_routes_server(server_thread="never-started")

        # must not raise
        instance.stop()

        self.assertEqual(0, instance.server.shutdown_calls)
        self.assertEqual(1, instance.server.close_calls)

    def test_stop_is_safe_to_call_twice(self):
        """Deactivation may reach an already stopped server."""
        instance = self._make_routes_server()

        instance.stop()
        shutdown_calls = instance.server.shutdown_calls
        # must not raise
        instance.stop()

        self.assertEqual(
            shutdown_calls,
            instance.server.shutdown_calls,
            "a second stop has no accept loop left to shut down",
        )

    def test_stop_does_not_write_to_stderr(self):
        """A failing stop must never reach the script output console."""
        instance = self._make_routes_server(
            http_server=_StubHttpServer(
                shutdown_error=OSError("bad file descriptor"),
                close_error=OSError("bad file descriptor"),
            )
        )
        recorder = _RecordingStream()
        original_stderr = sys.stderr
        sys.stderr = recorder
        try:
            instance.stop()
        finally:
            sys.stderr = original_stderr

        self.assertEqual([], recorder.writes)


class RoutesServerStartTests(unittest.TestCase):
    """Tests for the accept loop that RoutesServer.start owns."""

    def setUp(self):
        """Isolate the server module logger."""
        self.logger = _RecordingLogger()
        self._original_mlogger = routes_server.mlogger
        routes_server.mlogger = self.logger
        self._servers = []

    def tearDown(self):
        """Restore the server module logger."""
        for instance in self._servers:
            instance.stop(timeout=0.5)
        routes_server.mlogger = self._original_mlogger

    def _start_real_server(self):
        instance = routes_server.RoutesServer(host="127.0.0.1", port=0)
        self._servers.append(instance)
        return instance

    def test_a_live_server_runs_exactly_one_accept_loop(self):
        """A second start must not put a second accept loop on the same socket."""
        instance = self._start_real_server()

        first_thread = instance.server_thread
        instance.start()

        self.assertIs(first_thread, instance.server_thread)
        self.assertTrue(instance.is_running)

    def test_a_stopped_server_reports_itself_as_not_running(self):
        """A stopped server no longer reports a live accept loop."""
        instance = self._start_real_server()

        instance.stop()

        self.assertFalse(instance.is_running)

    def test_stop_releases_the_port_for_the_next_session(self):
        """The next session can bind the port the stopped server had."""
        instance = self._start_real_server()
        port = instance.server.server_address[1]

        instance.stop()

        replacement = routes_server.RoutesServer(host="127.0.0.1", port=port)
        self._servers.append(replacement)
        self.assertEqual(port, replacement.server.server_address[1])

    def test_request_threads_are_not_joined_on_close(self):
        """A request in flight during a reload must not hold the host."""
        # A request in flight when the session reloads must not hold the host:
        # server_close() runs on whichever thread collects the server.
        self.assertTrue(routes_server.ThreadedHttpServer.daemon_threads)
        self.assertFalse(routes_server.ThreadedHttpServer.block_on_close)


class _EnvVarStore(object):
    """Stand-in for the session env var holding the active routes server."""

    def __init__(self):
        self.values = {}

    def get(self, name):
        return self.values.get(name)

    def set(self, name, value):
        if value is None:
            self.values.pop(name, None)
        else:
            self.values[name] = value


class _StubRoutesServer(object):
    """RoutesServer stand-in whose stop can be made to fail."""

    def __init__(self, stop_error=None):
        self.stop_error = stop_error
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1
        if self.stop_error is not None:
            raise self.stop_error

    def __str__(self):
        return "<stub routes server>"


class _LifecycleTestCase(unittest.TestCase):
    """Base case that isolates the session env var and the serverinfo registry."""

    def setUp(self):
        """Swap in the recording logger, env var store and registry stubs."""
        self.logger = _RecordingLogger()
        self._original_mlogger = routes.mlogger
        routes.mlogger = self.logger
        self.env_vars = _EnvVarStore()
        self.unregister_calls = []
        self._original_get = envvars.get_pyrevit_env_var
        self._original_set = envvars.set_pyrevit_env_var
        self._original_register = serverinfo.register
        self._original_unregister = serverinfo.unregister
        envvars.get_pyrevit_env_var = self.env_vars.get
        envvars.set_pyrevit_env_var = self.env_vars.set
        serverinfo.unregister = self._count_unregister

    def tearDown(self):
        """Restore the session env var access and the serverinfo registry."""
        routes.mlogger = self._original_mlogger
        envvars.get_pyrevit_env_var = self._original_get
        envvars.set_pyrevit_env_var = self._original_set
        serverinfo.register = self._original_register
        serverinfo.unregister = self._original_unregister

    def _count_unregister(self):
        self.unregister_calls.append(True)

    def _activate(self, stub_server):
        self.env_vars.set(envvars.ROUTES_SERVER, stub_server)


class DeactivateServerTests(_LifecycleTestCase):
    """Tests for routes.deactivate_server, the reload's teardown step."""

    def test_deactivation_stops_and_deregisters_the_server(self):
        """Deactivation stops the server and drops its registration."""
        stub_server = _StubRoutesServer()
        self._activate(stub_server)

        routes.deactivate_server()

        self.assertEqual(1, stub_server.stop_calls)
        self.assertIsNone(self.env_vars.get(envvars.ROUTES_SERVER))
        self.assertEqual(1, len(self.unregister_calls))

    def test_deactivation_clears_registration_even_when_stop_fails(self):
        """A dead server must not stay registered: the next activation would skip binding."""
        self._activate(_StubRoutesServer(stop_error=RuntimeError("socket is closed")))

        # must not raise
        routes.deactivate_server()

        self.assertIsNone(self.env_vars.get(envvars.ROUTES_SERVER))
        self.assertEqual(1, len(self.unregister_calls))

    def test_deactivation_survives_a_failing_unregister(self):
        """A failed deregistration still clears the session env var."""
        self._activate(_StubRoutesServer())
        serverinfo.unregister = self._raise_unregister

        # must not raise
        routes.deactivate_server()

        self.assertIsNone(self.env_vars.get(envvars.ROUTES_SERVER))

    @staticmethod
    def _raise_unregister():
        raise OSError("cannot delete the instance data file")

    def test_deactivation_with_no_active_server_does_nothing(self):
        """Deactivating with nothing active touches nothing."""
        routes.deactivate_server()

        self.assertEqual([], self.unregister_calls)

    def test_deactivation_does_not_write_to_stderr(self):
        """A failing deactivation must never reach the script output console."""
        self._activate(_StubRoutesServer(stop_error=RuntimeError("socket is closed")))
        recorder = _RecordingStream()
        original_stderr = sys.stderr
        sys.stderr = recorder
        try:
            routes.deactivate_server()
        finally:
            sys.stderr = original_stderr

        self.assertEqual([], recorder.writes)

    def test_a_failed_stop_is_reported(self):
        """A stop that failed during a reload has to be visible."""
        self._activate(_StubRoutesServer(stop_error=RuntimeError("socket is closed")))

        routes.deactivate_server()

        self.assertTrue(
            self.logger.has_errors(),
            "a stop that failed during a reload has to be visible",
        )


class ActivateServerTests(_LifecycleTestCase):
    """Tests for routes.activate_server, the reload's last step."""

    def test_activation_hands_back_a_server_that_is_already_active(self):
        """Activating twice in one session reuses the running server."""
        stub_server = _StubRoutesServer()
        self._activate(stub_server)

        self.assertIs(stub_server, routes.activate_server())
        self.assertEqual(0, stub_server.stop_calls)

    def test_init_stops_the_active_server_before_activating_again(self):
        """Every session load still stops the previous server."""
        stub_server = _StubRoutesServer()
        self._activate(stub_server)

        routes.init()

        self.assertEqual(1, stub_server.stop_calls)
        self.assertIsNone(self.env_vars.get(envvars.ROUTES_SERVER))

    def test_a_failed_activation_is_reported(self):
        """A server that cannot bind the port is reported."""
        serverinfo.register = self._raise_register

        # must not raise
        self.assertIsNone(routes.activate_server())

        self.assertTrue(self.logger.has_errors())
        self.assertEqual(1, len(self.unregister_calls))

    def test_a_failed_activation_survives_a_failing_unregister(self):
        """A failed activation reports both failures instead of raising the second."""
        serverinfo.register = self._raise_register
        serverinfo.unregister = self._raise_unregister

        # must not raise
        self.assertIsNone(routes.activate_server())

        self.assertTrue(self.logger.has_errors())

    @staticmethod
    def _raise_register():
        raise OSError("cannot bind the routes port")

    @staticmethod
    def _raise_unregister():
        raise OSError("cannot delete the instance data file")
