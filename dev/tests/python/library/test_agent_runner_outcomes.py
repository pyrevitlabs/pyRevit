"""Host-free tests of the outcomes the agent runner reports (issue #3921)."""

import builtins
import sys
import time
import types
import unittest
from unittest import mock

from test_agent_runner_lines import _load_runner

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
        with mock.patch.object(self.runner, "_set_async_exc_function", lambda: None):
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
            mock.patch.object(self.runner, "_set_async_exc_function", lambda: None),
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

    def test_sys_exit_with_unicode_message_keeps_the_text(self):
        """A non-ASCII exit message is reported as text."""
        errors, _ = self._run("import sys\nsys.exit(u'\\u5c42')\n")
        self.assertEqual([("SystemExit", "The script exited: \u5c42")], errors)

    def test_sys_exit_with_a_code_reports_the_code(self):
        """A numeric exit code keeps its message."""
        errors, _ = self._run("import sys\nsys.exit(3)\n")
        self.assertEqual([("SystemExit", "The script exited with code 3")], errors)

    def test_bytes_results_are_text(self):
        """A bytes result is decoded, not serialized as a list of integers."""
        errors, results = self._run("result = [b'abc', bytearray(b'de')]\n")
        self.assertEqual([], errors)
        self.assertEqual(['["abc", "de"]'], results)


class AgentRunnerUnresolvedRollbackTests(unittest.TestCase):
    """A rollback Revit doesn't finish is reported, never counted as done (issue #4088)."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def _run(self, source, rollback):
        runner = self.runner

        class OpenTransaction(runner.DB.Transaction):
            def __init__(self, name):
                self.name = name
                self.started = False

            def Start(self):
                self.started = True

            def GetName(self):
                return self.name

            def HasStarted(self):
                return self.started

            def HasEnded(self):
                return False

            def RollBack(self):
                return rollback()

        errors = []
        context = types.SimpleNamespace(
            Source="from rollback_doubles import OpenTransaction\n" + source,
            Workspace=None,
            TimeoutSeconds=5,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=lambda *args: None,
            SetOutput=lambda *args: None,
            SetError=lambda *args: errors.append(args[:2]),
        )
        doubles = types.ModuleType("rollback_doubles")
        doubles.OpenTransaction = OpenTransaction
        with mock.patch.dict(sys.modules, {"rollback_doubles": doubles}):
            runner.run(context)
        return errors

    def test_a_pending_rollback_fails_the_run_with_its_status(self):
        """``Pending`` from RollBack() is not a rollback."""
        errors = self._run(
            "t = OpenTransaction('wall')\nt.Start()\n",
            lambda: self.runner.DB.TransactionStatus.Pending,
        )
        self.assertEqual(["transaction_rollback_failed"], [e[0] for e in errors])
        self.assertIn("Transaction", errors[-1][1])
        self.assertIn("'wall' returned Pending", errors[-1][1])

    def test_a_rollback_that_raises_is_reported_with_its_error(self):
        """An exception from RollBack() is reported instead of swallowed."""

        def refuse():
            raise RuntimeError("group still open")

        errors = self._run("t = OpenTransaction('wall')\nt.Start()\n", refuse)
        self.assertEqual(["transaction_rollback_failed"], [e[0] for e in errors])
        self.assertIn("'wall' raised group still open", errors[-1][1])

    def test_a_completed_rollback_still_reports_a_transaction_left_open(self):
        """A ``RolledBack`` status keeps the existing outcome."""
        errors = self._run(
            "t = OpenTransaction('wall')\nt.Start()\n",
            lambda: self.runner.DB.TransactionStatus.RolledBack,
        )
        self.assertEqual([("transaction_left_open",)], [e[:1] for e in errors])

    def test_an_unresolved_rollback_after_a_script_error_keeps_that_error(self):
        """The earlier failure stays in the message of the rollback error."""
        errors = []
        context_errors = {}

        def set_error(kind, message, trace):
            errors.append((kind, message))
            context_errors.update(ErrorType=kind, ErrorMessage=message)

        runner = self.runner

        class OpenTransaction(runner.DB.Transaction):
            def Start(self):
                self.started = True

            def HasStarted(self):
                return True

            def HasEnded(self):
                return False

            def RollBack(self):
                return runner.DB.TransactionStatus.Pending

        class Context(types.SimpleNamespace):
            def __getattr__(self, name):
                if name in context_errors:
                    return context_errors[name]
                raise AttributeError(name)

        context = Context(
            Source=(
                "from rollback_doubles import OpenTransaction\n"
                "t = OpenTransaction()\nt.Start()\nraise ValueError('boom')\n"
            ),
            Workspace=None,
            TimeoutSeconds=5,
            InputsJson="{}",
            UIApp=types.SimpleNamespace(ActiveUIDocument=None, Application=None),
            SetEngine=lambda *args: None,
            SetResult=lambda *args: None,
            SetOutput=lambda *args: None,
            SetError=set_error,
        )
        doubles = types.ModuleType("rollback_doubles")
        doubles.OpenTransaction = OpenTransaction
        with mock.patch.dict(sys.modules, {"rollback_doubles": doubles}):
            runner.run(context)
        self.assertEqual(
            ["ValueError", "transaction_rollback_failed"], [e[0] for e in errors]
        )
        self.assertIn("returned Pending", errors[-1][1])
        self.assertIn("ValueError: boom", errors[-1][1])


if __name__ == "__main__":
    unittest.main()
