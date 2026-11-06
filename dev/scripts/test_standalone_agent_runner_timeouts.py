"""Host-free tests for script shapes that tried to escape the run timeout (issue #3919)."""

import contextlib
import faulthandler
import sys
import time
import types
import unittest
from unittest import mock

from test_standalone_agent_runner_lines import _load_runner

HANG_LIMIT_SECONDS = 300


def setUpModule():
    """Fail the run with stack dumps instead of hanging CI if an escape returns."""
    faulthandler.dump_traceback_later(HANG_LIMIT_SECONDS, exit=True)


def tearDownModule():
    """Cancel the hang guard once every test here finished."""
    faulthandler.cancel_dump_traceback_later()


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"

ESCAPES = {
    "library_bare_except": (
        "import swallowing_library\nwhile True:\n    swallowing_library.read_fields()\n"
    ),
    "settrace_none_then_function_loop": (
        "import sys\n"
        "label = 'Transaction'\n"
        "sys.settrace(None)\n"
        "def spin():\n"
        "    while True:\n"
        "        pass\n"
        "spin()\n"
    ),
    "builtins_base_exception": (
        "try:\n"
        "    import builtins\n"
        "except ImportError:\n"
        "    import __builtin__ as builtins\n"
        "while True:\n"
        "    try:\n"
        "        while True:\n"
        "            pass\n"
        "    except builtins.BaseException:\n"
        "        pass\n"
    ),
    "tuple_call_handler": (
        "while True:\n"
        "    try:\n"
        "        while True:\n"
        "            pass\n"
        "    except tuple([BaseException]):\n"
        "        pass\n"
    ),
    "finally_loop": (
        "def work():\n"
        "    while True:\n"
        "        pass\n"
        "try:\n"
        "    work()\n"
        "finally:\n"
        "    while True:\n"
        "        pass\n"
    ),
}


def _swallowing_library():
    library = types.ModuleType("swallowing_library")

    def read_fields():
        try:
            for _ in range(1000):
                pass
        except:  # noqa: E722
            pass

    library.read_fields = read_fields
    return library


class AgentRunnerTimeoutEscapeTests(unittest.TestCase):
    """Every listed shape fails with ``timeout`` instead of running forever."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def _run(self, source, timeout_s=0.2):
        errors = []
        context = types.SimpleNamespace(
            Source=source,
            Workspace=None,
            TimeoutSeconds=timeout_s,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=lambda *args: None,
            SetOutput=lambda *args: None,
            SetError=lambda *args: errors.append(args[0]),
        )
        previous_trace = sys.gettrace()
        try:
            with (
                mock.patch.object(self.runner, "_WATCHDOG_ESCALATE_SECONDS", 0.2),
                mock.patch.dict(
                    sys.modules, {"swallowing_library": _swallowing_library()}
                ),
            ):
                self.runner.run(context)
        finally:
            sys.settrace(previous_trace)
        return errors

    def _assert_stopped(self, without_injection):
        for name, source in sorted(ESCAPES.items()):
            with self.subTest(shape=name):
                injection = (
                    mock.patch.object(
                        self.runner, "_set_async_exc_function", return_value=None
                    )
                    if without_injection
                    else contextlib.nullcontext()
                )
                with injection:
                    started = time.time()
                    errors = self._run(source)
                self.assertEqual(["timeout"], errors)
                self.assertLess(time.time() - started, 5)

    def test_escapes_stop_with_the_watchdog_injecting(self):
        """CPython: injection plus loop guards stop every shape."""
        self._assert_stopped(without_injection=False)

    def test_escapes_stop_with_loop_guards_alone(self):
        """IronPython has no injection; the loop headers alone stop every shape."""
        self._assert_stopped(without_injection=True)

    def test_endless_result_stops_while_it_is_serialized(self):
        """The watchdog still covers script code that runs while ``result`` is serialized."""
        source = "exec('def endless():\\n    while True:\\n        yield 1')\nresult = endless()\n"
        revit_types = types.SimpleNamespace(
            ElementId=type("ElementId", (), {}),
            Element=type("Element", (), {}),
            XYZ=type("XYZ", (), {}),
        )
        started = time.time()
        with mock.patch.object(self.runner, "DB", revit_types):
            self.assertEqual(["timeout"], self._run(source))
        self.assertLess(time.time() - started, 5)


class AgentRunnerNarrowingTests(unittest.TestCase):
    """Handler narrowing covers attribute spellings and fails closed."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def test_attribute_base_exception_is_narrowed(self):
        """``except builtins.BaseException`` no longer catches the timeout."""
        source = (
            "import builtins\n"
            "try:\n"
            "    raise error\n"
            "except builtins.BaseException:\n"
            "    result = 'caught'\n"
        )
        code, problem, _ = self.runner._compile_source(source)
        self.assertIsNone(problem)
        namespace = {"error": ValueError()}
        exec(code, namespace)
        self.assertEqual("caught", namespace["result"])
        with self.assertRaises(self.runner.RunTimedOut):
            exec(code, {"error": self.runner.RunTimedOut()})

    def test_unmatched_handler_header_raises(self):
        """A handler position the tokenizer never meets is an error, not a no-op."""
        source = "try:\n    pass\nexcept:\n    pass\n"
        handlers = [types.SimpleNamespace(lineno=9, col_offset=0)]
        with self.assertRaises(ValueError):
            self.runner._narrow_source_handlers(source, handlers)

    def test_unmatched_handler_header_compiles_the_narrowed_ast(self):
        """Fail closed: the fallback still keeps the timeout uncaught."""
        source = "try:\n    raise error\nexcept:\n    result = 'caught'\n"
        narrow = self.runner._narrow_source_handlers
        with mock.patch.object(
            self.runner,
            "_narrow_source_handlers",
            side_effect=lambda text, handlers: narrow(
                text, [types.SimpleNamespace(lineno=9, col_offset=0)]
            ),
        ):
            code, problem, _ = self.runner._compile_source(source)
        self.assertIn("ValueError", problem)
        self.assertIn("compiled the narrowed AST instead", problem)
        with self.assertRaises(self.runner.RunTimedOut):
            exec(code, {"error": self.runner.RunTimedOut()})


@unittest.skipUnless(
    sys.implementation.name == "cpython", "Only CPython injects into the thread"
)
class AgentRunnerWatchdogStopTests(unittest.TestCase):
    """Nothing reaches the script thread once the script has finished."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def test_no_injection_after_the_script_finished_but_before_stop(self):
        """The watchdog and the escalation go quiet as soon as the script ends."""
        runner = self.runner
        state = {"timed_out": False, "finished": False}
        with mock.patch.object(runner, "_WATCHDOG_ESCALATE_SECONDS", 0.0):
            stop = runner._start_watchdog(0.05, state)
            try:
                try:
                    while True:
                        time.sleep(0.01)
                except runner.RunTimedOut:
                    pass
                state["finished"] = True
                ended = time.time() + 1.0
                spins = 0
                while time.time() < ended:
                    spins += 1
            finally:
                stop()
        self.assertTrue(state["timed_out"])
        self.assertGreater(spins, 0)
        if hasattr(sys, "monitoring"):
            for tool_id in runner._ESCALATION_TOOL_IDS:
                self.assertIsNone(sys.monitoring.get_tool(tool_id))

    def test_a_timeout_landing_during_shutdown_still_stops_the_watchdog(self):
        """A pending injection that hits the stop call is retried, not escaped."""
        runner = self.runner
        calls = []

        def stop_hit_once():
            calls.append(state["finished"])
            if len(calls) == 1:
                raise runner.RunTimedOut(1)

        state = {"timed_out": True, "finished": False, "stop_watchdog": stop_hit_once}
        runner._finish_and_stop_watchdog(state)

        self.assertEqual([True, True], calls)
        self.assertTrue(state["finished"])

    def test_a_timeout_landing_during_startup_still_stops_the_watchdog(self):
        """An injection before the script starts can't leave the watchdog running."""
        runner = self.runner
        start_watchdog = runner._start_watchdog
        stops = []

        def recorded(timeout_s, state):
            stops.append(start_watchdog(timeout_s, state))

        def started_then_hit(timeout_s, state):
            recorded(timeout_s, state)
            raise runner.RunTimedOut(timeout_s)

        def tracer_hit(*args):
            raise runner.RunTimedOut(args[0])

        landings = {
            "after_start_returns": {"_start_watchdog": started_then_hit},
            "while_installing_the_tracer": {
                "_start_watchdog": recorded,
                "_execution_tracer": tracer_hit,
            },
        }
        for name, patches in sorted(landings.items()):
            with self.subTest(landing=name):
                del stops[:]
                errors = []
                context = types.SimpleNamespace(
                    Source="result = eval('1')\n",
                    Workspace=None,
                    TimeoutSeconds=0.1,
                    InputsJson="{}",
                    UIApp=types.SimpleNamespace(
                        ActiveUIDocument=None, Application=None
                    ),
                    SetEngine=lambda *args: None,
                    SetResult=lambda *args: None,
                    SetOutput=lambda *args: None,
                    SetError=lambda *args: errors.append(args[0]),
                )
                previous_trace = sys.gettrace()
                injected = False
                try:
                    with contextlib.ExitStack() as stack:
                        for target, replacement in patches.items():
                            stack.enter_context(
                                mock.patch.object(
                                    runner, target, side_effect=replacement
                                )
                            )
                        runner.run(context)
                    ended = time.time() + 0.6
                    try:
                        while time.time() < ended:
                            pass
                    except runner.RunTimedOut:
                        injected = True
                finally:
                    sys.settrace(previous_trace)
                    for stop in stops:
                        stop()
                self.assertEqual(["timeout"], errors)
                self.assertEqual(1, len(stops))
                self.assertFalse(injected)


if __name__ == "__main__":
    unittest.main()
