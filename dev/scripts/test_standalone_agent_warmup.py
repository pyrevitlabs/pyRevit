"""Host-free tests for the agent runner's warm-up (issue #3911)."""

import sys
import types
import unittest
from unittest import mock

from test_standalone_agent_runner_lines import _load_runner


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
    """``warm_up`` runs the paths a cold first run pays for, and nothing else."""

    @classmethod
    def setUpClass(cls):
        """Load the shared runner against isolated host doubles."""
        cls.runner = _load_runner()

    def setUp(self):
        """Give the runner the Revit types the warm-up uses."""
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

    def _spy(self, *names):
        spies = {}
        for name in names:
            patcher = mock.patch.object(
                self.runner, name, wraps=getattr(self.runner, name)
            )
            spies[name] = patcher.start()
            self.addCleanup(patcher.stop)
        return spies

    def test_compiles_serializes_and_scans_for_transactions(self):
        """The compile, result and rollback phases of a guarded run all get exercised."""
        spies = self._spy(
            "_record_transaction_starts",
            "_compile_source",
            "_guard_loop_headers",
            "_to_jsonable",
            "_roll_back_open_transactions",
            "_transaction_rank",
        )

        self.runner.warm_up()

        for name, spy in spies.items():
            self.assertTrue(spy.called, name + " was not exercised")
        _, guard_loops = spies["_compile_source"].call_args.args
        self.assertTrue(guard_loops)

    def test_does_nothing_a_cold_run_would_not_need(self):
        """No run, no exec, no watchdog, no tracer: the main thread is held only as long as needed."""
        spies = self._spy("run", "_start_watchdog", "_execution_tracer")
        trace = sys.gettrace()

        with mock.patch.object(sys, "settrace") as settrace:
            self.runner.warm_up()

        for name, spy in spies.items():
            self.assertFalse(spy.called, name + " was called")
        settrace.assert_not_called()
        self.assertIs(trace, sys.gettrace())

    def test_clears_the_transaction_type_caches_like_a_run(self):
        """Cached types would keep the warm-up's values alive across runs."""
        self.runner.warm_up()

        self.assertEqual({}, self.runner._TRANSACTION_RANKS)
        self.assertEqual(set(), self.runner._UNTRACKED_TYPES)
        self.assertEqual(set(), self.runner._TRACKED_TYPES)

    def test_a_source_it_cannot_rewrite_raises(self):
        """The host logs a non-zero exit instead of silently skipping the warm-up."""
        with mock.patch.object(
            self.runner,
            "_compile_source",
            return_value=(None, "tokenize failed", False),
        ):
            with self.assertRaises(RuntimeError) as raised:
                self.runner.warm_up()

        self.assertIn("tokenize failed", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
