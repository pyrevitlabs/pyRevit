"""Host-free tests for the agent runner's warm-up (issue #3911)."""

import json
import sys
import types
import unittest
from unittest import mock

from test_standalone_agent_runner_lines import _load_runner

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


class _ElementId(object):
    def __init__(self, value):
        self.value = value

    def __int__(self):
        return self.value


_ElementId.InvalidElementId = _ElementId(-1)


class _XYZ(object):
    def __init__(self, x, y, z):
        self.X, self.Y, self.Z = x, y, z


class AgentRunnerWarmUpTests(unittest.TestCase):
    """``warm_up`` goes through the run's code paths without a Revit application."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def setUp(self):
        """Give the runner the Revit types the warm-up script uses."""
        db = types.SimpleNamespace(
            ElementId=_ElementId,
            Element=type("Element", (), {}),
            XYZ=_XYZ,
            SubTransaction=self.runner.DB.SubTransaction,
            Transaction=self.runner.DB.Transaction,
            TransactionGroup=self.runner.DB.TransactionGroup,
        )
        patcher = mock.patch.object(self.runner, "DB", db)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exercises_every_phase_of_a_guarded_run(self):
        """Rewriting, compiling, watchdog, recording, serializing and rollback all run."""
        runner = self.runner
        spies = {
            name: mock.patch.object(runner, name, wraps=getattr(runner, name))
            for name in (
                "_record_transaction_starts",
                "_compile_source",
                "_start_watchdog",
                "_track_transaction",
                "_to_jsonable",
                "_roll_back_open_transactions",
            )
        }
        started = {name: patch.start() for name, patch in spies.items()}
        self.addCleanup(mock.patch.stopall)

        runner.warm_up()

        for name, spy in started.items():
            self.assertTrue(spy.called, name + " was not exercised")
        _, guard_loops = started["_compile_source"].call_args.args
        self.assertTrue(guard_loops)

    def test_serializes_the_result_through_the_runs_converter(self):
        """ElementId, XYZ and set values go through ``_to_jsonable``."""
        results = []
        context = self.runner._WarmUpContext()
        context.SetResult = results.append

        self.runner.run(context)

        self.assertIsNone(context.error)
        self.assertEqual(
            {
                "values": [0, 1, 2],
                "unique": [0, 1, 2],
                "id": -1,
                "point": [1.0, 2.0, 3.0],
            },
            json.loads(results[0]),
        )

    def test_needs_no_revit_application_or_document(self):
        """The stand-in context has no document to read."""
        context = self.runner._WarmUpContext()

        self.assertIsNone(context.UIApp.ActiveUIDocument)
        self.assertIsNone(context.UIApp.Application)
        self.assertIsNone(context.Workspace)

    def test_restores_stdout(self):
        """The warm-up's captured output doesn't leak into the engine's stdout."""
        stdout = sys.stdout

        self.runner.warm_up()

        self.assertIs(stdout, sys.stdout)

    def test_failure_raises_so_the_host_logs_a_non_zero_exit(self):
        """A failing warm-up script surfaces as an exception, not silence."""
        with mock.patch.object(
            self.runner._WarmUpContext, "Source", "raise ValueError('boom')\n"
        ):
            with self.assertRaises(RuntimeError) as raised:
                self.runner.warm_up()

        self.assertIn("boom", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
