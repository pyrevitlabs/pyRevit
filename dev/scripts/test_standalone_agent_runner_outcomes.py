"""Host-free tests of the outcomes the agent runner reports (issue #3921)."""

import builtins
import time
import types
import unittest
from unittest import mock

from test_standalone_agent_runner_lines import _load_runner

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


class AgentRunnerOutcomeTests(unittest.TestCase):
    """Every run ends in one reported outcome, never an exception out of run()."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def _run(self, source, timeout_s=5):
        errors = []
        results = []
        context = types.SimpleNamespace(
            Source=source,
            Workspace=None,
            TimeoutSeconds=timeout_s,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=results.append,
            SetOutput=lambda *args: None,
            SetError=lambda *args: errors.append(args[:2]),
        )
        self.runner.run(context)
        return errors, results

    def test_a_run_past_its_timeout_returns_no_result(self):
        """A blocking call that outlives the limit fails the run without its result.

        IronPython can't interrupt the script thread, so the script reaches its
        ``result`` assignment after the deadline; emulate that on CPython.
        """
        with mock.patch.object(self.runner, "_async_exception_setter", lambda: None):
            errors, results = self._run(
                "import time\ntime.sleep(0.3)\nresult = 1\n", 0.05
            )
        self.assertEqual(["timeout"], [error[0] for error in errors])
        self.assertEqual([], results)

    def test_a_result_that_outlives_the_deadline_while_converting_returns_no_result(
        self,
    ):
        """Converting the result counts toward the limit, so it can't keep a late run."""

        def slow_conversion(value):
            time.sleep(0.3)
            return "late"

        with (
            mock.patch.object(self.runner, "_async_exception_setter", lambda: None),
            mock.patch.object(self.runner, "_to_jsonable", slow_conversion),
        ):
            errors, results = self._run("result = object()\n", 0.1)
        self.assertEqual(["timeout"], [error[0] for error in errors])
        self.assertEqual([], results)

    def test_keyboard_interrupt_is_reported_as_a_script_error(self):
        """A BaseException the script raises does not escape run()."""
        errors, results = self._run("raise KeyboardInterrupt()\n")
        self.assertEqual(["KeyboardInterrupt"], [error[0] for error in errors])
        self.assertEqual([], results)

    def test_a_script_raised_timeout_without_a_limit_is_a_script_error(self):
        """RunTimedOut with no timeout set is reported as raised, not as a crash."""
        with mock.patch.object(
            builtins, "RunTimedOut", self.runner.RunTimedOut, create=True
        ):
            errors, _ = self._run("raise RunTimedOut(1)\n", None)
        self.assertEqual(["RunTimedOut"], [error[0] for error in errors])

    def test_a_script_raised_timeout_before_the_deadline_is_a_script_error(self):
        """Only a deadline that passed is a timeout, not the exception type alone."""
        with mock.patch.object(
            builtins, "RunTimedOut", self.runner.RunTimedOut, create=True
        ):
            errors, _ = self._run("raise RunTimedOut(0)\n", 300)
        self.assertEqual(["RunTimedOut"], [error[0] for error in errors])

    def test_an_empty_message_has_no_leading_space_before_the_net_details(self):
        """IronPython's KeyboardInterrupt has no text of its own, only the .NET cause."""
        clr_type = types.SimpleNamespace(
            FullName="Microsoft.Scripting.KeyboardInterruptException",
            Name="KeyboardInterruptException",
        )
        clr_exception = types.SimpleNamespace(
            GetType=lambda: clr_type, Message="KeyboardInterrupt", InnerException=None
        )
        interrupt = KeyboardInterrupt()
        interrupt.clsException = clr_exception
        self.assertEqual(
            (
                "KeyboardInterrupt",
                "[.NET: Microsoft.Scripting.KeyboardInterruptException: "
                "KeyboardInterrupt]",
            ),
            self.runner._describe_error(interrupt),
        )

    def test_sys_exit_with_a_message_reports_the_message(self):
        """sys.exit('msg') is not an exit code."""
        errors, _ = self._run("import sys\nsys.exit('missing level')\n")
        self.assertEqual([("SystemExit", "The script exited: missing level")], errors)

    def test_sys_exit_with_a_code_reports_the_code(self):
        """A numeric exit code keeps its message."""
        errors, _ = self._run("import sys\nsys.exit(3)\n")
        self.assertEqual([("SystemExit", "The script exited with code 3")], errors)

    def test_bytes_results_are_text(self):
        """A bytes result is decoded, not serialized as a list of integers."""
        errors, results = self._run("result = [b'abc', bytearray(b'de')]\n")
        self.assertEqual([], errors)
        self.assertEqual(['["abc", "de"]'], results)


if __name__ == "__main__":
    unittest.main()
