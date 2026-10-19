"""API-free failure-path regressions for the local Dynamo smoke harness.

Only lightweight doubles are imported; these cases never load Revit or Dynamo.
Real graph execution remains a separate local integration check.
"""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"
ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "pyRevitfile").exists()
)


def _load(path):
    spec = importlib.util.spec_from_file_location("dynamo_smoke_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DynamoSmokeFailureTests(unittest.TestCase):
    """Setup and teardown failures must preserve evidence and owned resources."""

    def setUp(self):
        """Isolate host imports and transaction resources with API-free doubles."""
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.group = Mock()
        self.group.Start.return_value = "Started"
        self.group.GetStatus.return_value = "Started"
        self.group.RollBack.return_value = "RolledBack"
        self.db = SimpleNamespace(
            TransactionGroup=Mock(return_value=self.group),
            TransactionStatus=SimpleNamespace(
                Started="Started", RolledBack="RolledBack"
            ),
        )
        self.app = SimpleNamespace(ActiveUIDocument=SimpleNamespace(Document=object()))
        pyrevit = ModuleType("pyrevit")
        pyrevit.DB, pyrevit.HOST_APP = self.db, SimpleNamespace(uiapp=self.app)
        system = ModuleType("System")
        system.AppDomain, system.Array, system.String = Mock(), {str: list}, str
        reflection = ModuleType("System.Reflection")
        reflection.BindingFlags = SimpleNamespace(Public=1, NonPublic=2, Static=4)
        shared = ModuleType("pyRevitLabs.PyRevit.Runtime.Shared")
        shared.DynamoExecutionOptions = SimpleNamespace
        self.interop = Mock(side_effect=RuntimeError("original Dynamo failure"))
        shared.DynamoRevitInterop = SimpleNamespace(Run=self.interop)
        self.enterContext(
            patch.dict(
                "sys.modules",
                {
                    "clr": SimpleNamespace(AddReference=Mock()),
                    "System": system,
                    "System.Reflection": reflection,
                    "pyrevit": pyrevit,
                    "pyRevitLabs.PyRevit.Runtime.Shared": shared,
                },
            )
        )
        self.module = _load(
            ROOT / "pyrevitlib/pyrevit/unittests/test_dynamo_execution.py"
        )
        self.enterContext(patch.object(self.module, "_model", return_value=None))
        original_mkdtemp = tempfile.mkdtemp
        self.enterContext(
            patch.object(
                self.module.tempfile,
                "mkdtemp",
                side_effect=lambda **kwargs: original_mkdtemp(
                    dir=self.directory, **kwargs
                ),
            )
        )

    def test_lookalike_user_graph_is_rejected_without_mutation(self):
        """Matching test metadata cannot authorize replacing an unsaved graph."""
        workspace = SimpleNamespace(
            Name=self.module._GRAPH_NAME,
            Description="Issue #2992: fresh token proves DesignScript execution.",
            Nodes=[SimpleNamespace(Code='token = "pyrevit-dynamo-user";')],
            HasUnsavedChanges=True,
            FileName="",
        )
        self.module._model.return_value = SimpleNamespace(CurrentWorkspace=workspace)
        with self.assertRaisesRegex(AssertionError, "Close the current Dynamo graph"):
            self.module.assert_dynamo_execution()
        self.assertTrue(workspace.HasUnsavedChanges)
        self.db.TransactionGroup.assert_not_called()
        self.interop.assert_not_called()

    def test_failed_transaction_start_disposes_group_and_removes_graph_directory(self):
        """A setup exception still releases all resources already acquired."""
        self.group.Start.side_effect = RuntimeError("start failed")
        self.group.GetStatus.return_value = "Uninitialized"
        with self.assertRaisesRegex(RuntimeError, "start failed"):
            self.module.assert_dynamo_execution()
        self.group.Dispose.assert_called_once()
        self.group.RollBack.assert_not_called()
        self.assertEqual([], list(Path(self.directory).iterdir()))

    def test_original_failure_survives_rollback_and_disposal_failures(self):
        """Diagnostics retain execution and every teardown failure together."""
        self.group.RollBack.side_effect = RuntimeError("rollback failed")
        self.group.Dispose.side_effect = RuntimeError("dispose failed")
        with self.assertRaises(Exception) as raised:
            self.module.assert_dynamo_execution()
        message = str(raised.exception)
        for expected in (
            "original Dynamo failure",
            "rollback failed",
            "dispose failed",
        ):
            self.assertIn(expected, message)
        self.assertEqual([], list(Path(self.directory).iterdir()))

    def test_temporary_directory_failure_does_not_create_a_transaction(self):
        """A failed first acquisition cannot leave transaction resources behind."""
        self.module.tempfile.mkdtemp.side_effect = OSError("directory failed")
        with self.assertRaisesRegex(OSError, "directory failed"):
            self.module.assert_dynamo_execution()
        self.db.TransactionGroup.assert_not_called()
        self.interop.assert_not_called()

    def test_nonstarted_transaction_status_prevents_dynamo_execution(self):
        """A rejected transaction start fails before opening a graph."""
        self.group.Start.return_value = "Uninitialized"
        self.group.GetStatus.return_value = "Uninitialized"
        with self.assertRaisesRegex(AssertionError, "did not start"):
            self.module.assert_dynamo_execution()
        self.interop.assert_not_called()
        self.group.Dispose.assert_called_once()
        self.assertEqual([], list(Path(self.directory).iterdir()))

    def test_ordinary_execution_failure_rolls_back_and_cleans_up(self):
        """An engine error propagates after rollback and temporary-file removal."""
        with self.assertRaisesRegex(RuntimeError, "original Dynamo failure"):
            self.module.assert_dynamo_execution()
        self.group.RollBack.assert_called_once()
        self.group.Dispose.assert_called_once()
        self.assertEqual([], list(Path(self.directory).iterdir()))


class DynamoJournalEvidenceTests(unittest.TestCase):
    """Retries retain earlier evidence and project files belong to CLI teardown."""

    def setUp(self):
        """Use a private repository and journal environment for evidence checks."""
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.directory)
        self.environment = self.root / "journal-environment"
        self.environment.mkdir()
        self.helper = SimpleNamespace(
            __file__=str(ROOT / "pyrevitlib/pyrevit/unittests/test_dynamo_execution.py")
        )
        self.helper.assert_dynamo_execution = Mock(
            side_effect=[{"token": "cold"}, {"token": "warm"}]
        )
        self.project = Mock()

        def _save_project(path):
            with open(path, "x") as project:
                project.write("disposable model")

        self.project.SaveAs.side_effect = _save_project
        pyrevit = ModuleType("pyrevit")
        pyrevit.DB = SimpleNamespace(UnitSystem=SimpleNamespace(Metric=0))
        pyrevit.EXEC_PARAMS = SimpleNamespace(
            command_data=SimpleNamespace(
                JournalData={"LogFile": str(self.environment / "runner.log")}
            )
        )
        tests = ModuleType("pyrevit.unittests")
        tests.test_dynamo_execution = self.helper
        self.enterContext(
            patch.dict("sys.modules", {"pyrevit": pyrevit, "pyrevit.unittests": tests})
        )
        self.module = _load(ROOT / "dev/tests/revit/run_dynamo.py")
        self.module.__file__ = str(self.root / "dev/tests/revit/run_dynamo.py")
        self.module.__batchexec__ = True
        self.module.__revit__ = SimpleNamespace(
            Application=SimpleNamespace(
                VersionNumber="2025", NewProjectDocument=Mock(return_value=self.project)
            ),
            OpenAndActivateDocument=Mock(),
        )

    def test_retry_preserves_failed_evidence_in_a_distinct_report(self):
        """A successful retry must not replace the preceding failure report."""
        self.helper.assert_dynamo_execution.side_effect = RuntimeError("first failure")
        with self.assertRaisesRegex(RuntimeError, "first failure"):
            self.module.run()
        self.helper.assert_dynamo_execution.side_effect = [
            {"token": "cold"},
            {"token": "warm"},
        ]
        self.module.run()
        reports = [
            json.loads(path.read_text())
            for path in self.root.glob(".test-results/dynamo/**/*.json")
        ]
        self.assertEqual(
            ["failed", "passed"], sorted(report["status"] for report in reports)
        )
        self.assertEqual(2, len({report["run_id"] for report in reports}))

    def test_project_belongs_to_the_runner_purge_directory(self):
        """The CLI can delete the project after Revit releases its file locks."""
        self.module.run()
        model_path = Path(self.project.SaveAs.call_args.args[0])
        self.assertEqual(self.environment, model_path.parent)
        self.assertTrue(model_path.is_file())
        self.project.Close.assert_called_once_with(False)
