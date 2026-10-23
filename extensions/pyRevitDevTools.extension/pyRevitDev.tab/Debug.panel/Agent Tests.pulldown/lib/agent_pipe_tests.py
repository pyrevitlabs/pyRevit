"""The host's named pipe, used the way an external client uses it.

A command runs on Revit's main thread, so the pipe can answer only what the pipe
thread serves itself (ping, lookup_api) and errors. Requests that need the main
thread time out as revit_busy while a command runs, which is also checked here.
"""

import json
import os.path as op
import threading
import time

from System.Diagnostics import Process
from System.IO import StreamReader, StreamWriter
from System.IO.Pipes import NamedPipeClientStream, PipeDirection
from System.Text import UTF8Encoding

from pyrevit import HOST_APP

import agent_harness as harness
from agent_harness import TestCase


ANSWER_TIMEOUT_S = 15


def _exchange(line, timeout_ms=5000):
    outcome = {}

    def talk():
        pipe = NamedPipeClientStream(".", harness.pipe_name(), PipeDirection.InOut)
        try:
            pipe.Connect(timeout_ms)
            encoding = UTF8Encoding(False)
            writer = StreamWriter(pipe, encoding)
            writer.AutoFlush = True
            writer.NewLine = "\n"
            reader = StreamReader(pipe, encoding)
            writer.WriteLine(line)
            answer = reader.ReadLine()
            outcome["answer"] = None if answer is None else json.loads(str(answer))
        except Exception as error:
            outcome["error"] = error
        finally:
            pipe.Dispose()

    worker = threading.Thread(target=talk)
    worker.daemon = True
    worker.start()
    worker.join(ANSWER_TIMEOUT_S)
    if worker.is_alive():
        raise AssertionError(
            "The pipe gave no answer within {} seconds.".format(ANSWER_TIMEOUT_S)
        )
    if "error" in outcome:
        raise outcome["error"]
    return outcome["answer"]


def _call(method, request_id=1, **params):
    return _exchange(
        json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
    )


class PipeTests(TestCase):
    """Requests sent through the real named pipe."""

    def setUp(self):
        """Skip every test when the host did not start its pipe."""
        if not harness.host_running():
            self.skipTest(
                "The agent host is disabled; run 'pyrevit configs agent enable' "
                "and reload pyRevit."
            )

    def test_ping_identifies_this_revit_process(self):
        """The ping request answers with this process, this pipe and this Revit year."""
        result = _call("ping")["result"]
        self.assertTrue(result["pong"])
        self.assertEqual(Process.GetCurrentProcess().Id, result["pid"])
        self.assertEqual(harness.pipe_name(), result["pipe"])
        self.assertEqual(str(HOST_APP.version), result["revit_version"])

    def test_the_host_is_registered_for_clients(self):
        """The host writes the registration file the CLI uses to find it."""
        pid = Process.GetCurrentProcess().Id
        path = op.join(harness.agent_dir(), "instances", "{}.json".format(pid))
        self.assertTrue(op.exists(path), path)
        with open(path) as handle:
            registration = json.load(handle)
        self.assertEqual(pid, registration["pid"])
        self.assertEqual(harness.pipe_name(), registration["pipe"])
        self.assertEqual(str(HOST_APP.version), registration["revit_version"])
        self.assertTrue(registration["started"])

    def test_lookup_is_answered_by_the_pipe_thread(self):
        """lookup_api needs no main thread, so it works while a command runs."""
        result = _call("lookup_api", name="Wall")["result"]
        self.assertTrue(result["found"])
        self.assertEqual("Autodesk.Revit.DB.Wall", result["full_name"])

    def test_session_status_is_answered_by_the_pipe_thread(self):
        """Session status needs no main thread, so a client can read it while a command runs."""
        result = _call("session_status")["result"]
        self.assertEqual("active", result["state"])
        self.assertEqual(harness.session().project.Title, result["document"])

    def test_the_pipe_can_not_start_or_resume_a_session(self):
        """Only Revit grants a session: no pipe request starts or resumes one."""
        for method in ("start_session", "resume_session"):
            answer = _call(method)
            self.assertEqual("method_not_found", answer["error"]["data"]["type"])

    def test_an_unknown_method_is_a_method_not_found_error(self):
        """An unknown method keeps the request id and names its error type."""
        answer = _call("no_such_method", request_id=41)
        self.assertEqual(41, answer["id"])
        self.assertEqual(-32000, answer["error"]["code"])
        self.assertEqual("method_not_found", answer["error"]["data"]["type"])

    def test_malformed_json_is_a_parse_error_and_the_host_keeps_serving(self):
        """A garbage line gets a parse error, and the next client is still served."""
        answer = _exchange("{ this is not json")
        self.assertEqual(-32700, answer["error"]["code"])
        self.assertEqual("parse_error", answer["error"]["data"]["type"])
        self.assertIsNone(answer["id"])
        self.assertTrue(_call("ping")["result"]["pong"])

    def test_requests_on_separate_connections_each_get_their_own_answer(self):
        """The pipe serves one connection after another, answering each with its id."""
        for request_id in (5, 6, 7):
            self.assertEqual(request_id, _call("ping", request_id=request_id)["id"])

    def test_requests_that_need_the_main_thread_are_busy_while_a_command_runs(self):
        """get_context can't start while this command holds Revit's main thread."""
        started = time.time()
        answer = _call("get_context", start_timeout_s=1)
        elapsed = time.time() - started
        self.assertEqual("revit_busy", answer["error"]["data"]["type"])
        self.assertIn("did not become idle within 1s", answer["error"]["message"])
        self.assertGreater(elapsed, 0.8)
        self.assertLess(elapsed, 15)

    def test_a_bad_start_timeout_is_rejected_on_the_pipe(self):
        """start_timeout_s is validated before the request waits for Revit."""
        for value in (0, -1, 3601):
            answer = _call("get_context", start_timeout_s=value)
            self.assertEqual("invalid_params", answer["error"]["data"]["type"], value)
