"""Verify installed Dynamo executes fresh DesignScript without changing a model.

Important:
    This hosted test starts Dynamo and opens a temporary graph. It refuses to
    replace an existing user workspace. Revit and Dynamo are required; never run
    this module in CI. A successful command return alone is not execution proof.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import traceback
import unittest
import uuid

import clr
from System import AppDomain, Array, String
from System.Reflection import BindingFlags

from pyrevit import DB, HOST_APP

TEST_ENVIRONMENT = "Revit"
TEST_LEVEL = "Integration"
_GRAPH_NAME = "pyRevit Dynamo execution smoke test"


def _model():
    for assembly in AppDomain.CurrentDomain.GetAssemblies():
        model_owner = assembly.GetType("Dynamo.Applications.DynamoRevit", False)
        if model_owner is not None:
            model_property = model_owner.GetProperty(
                "RevitDynamoModel",
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static,
            )
            if model_property is not None:
                return model_property.GetValue(None, None)
    return None


def _graph(token, node_id):
    return {
        "Uuid": str(uuid.uuid4()),
        "IsCustomNode": False,
        "Description": "Issue #2992: fresh token proves DesignScript execution.",
        "Name": _GRAPH_NAME,
        "ElementResolver": {"ResolutionMap": {}},
        "Nodes": [
            {
                "ConcreteType": "Dynamo.Graph.Nodes.CodeBlockNodeModel, DynamoCore",
                "Id": node_id,
                "NodeType": "CodeBlockNode",
                "Inputs": [],
                "Outputs": [
                    {
                        "Id": uuid.uuid4().hex,
                        "Name": "token",
                        "Description": "Unique execution token",
                        "UsingDefaultValue": False,
                        "Level": 2,
                        "UseLevels": False,
                        "KeepListStructure": False,
                    }
                ],
                "Replication": "Disabled",
                "Code": 'token = "{}";'.format(token),
            }
        ],
        "Connectors": [],
        "Dependencies": [],
        "NodeLibraryDependencies": [],
        "Bindings": [],
        "View": {
            "Dynamo": {
                "Version": "2.0.0.0",
                "RunType": "Automatic",
                "HasRunWithoutCrash": True,
                "RunPeriod": "1000",
                "ScaleFactor": 1.0,
            },
            "NodeViews": [],
            "Annotations": [],
            "X": 0,
            "Y": 0,
            "Zoom": 1,
        },
    }


def _cleanup(group, directory, graph_path):
    failures = []
    try:
        model = _model()
        workspace = model.CurrentWorkspace if model is not None else None
        if (
            workspace is not None
            and graph_path is not None
            and os.path.normcase(str(workspace.FileName))
            == os.path.normcase(graph_path)
        ):
            workspace.Clear()
            workspace.FileName = ""
            workspace.HasUnsavedChanges = False
    except Exception:
        failures.append(traceback.format_exc())
    if group is not None:
        try:
            if group.GetStatus() == DB.TransactionStatus.Started:
                if group.RollBack() != DB.TransactionStatus.RolledBack:
                    raise AssertionError("Dynamo test changes were not rolled back.")
        except Exception:
            failures.append(traceback.format_exc())
        try:
            group.Dispose()
        except Exception:
            failures.append(traceback.format_exc())
    if directory is not None:
        shutil.rmtree(directory, ignore_errors=True)
    return failures


def assert_dynamo_execution(ui_application=None):
    """Start Dynamo and require an evaluated, unique graph-output token.

    Args:
        ui_application (Autodesk.Revit.UI.UIApplication): Active app; defaults to
            the hosted pyRevit app.

    Returns:
        evidence (dict): Actual versions and execution evidence for a local matrix.

    Raises:
        AssertionError: No document, unsafe workspace, failed startup or wrong output.

    Important:
        Requires an active project. An always-rolled-back transaction group also
        removes Dynamo's startup preview materials. The graph has no Python nodes
        or package dependencies.
    """
    ui_application = ui_application or HOST_APP.uiapp
    if ui_application.ActiveUIDocument is None:
        raise AssertionError("Open a disposable project before testing Dynamo.")
    current_model = _model()
    if current_model is not None:
        workspace = current_model.CurrentWorkspace
        if workspace is not None and (
            workspace.HasUnsavedChanges or workspace.FileName or list(workspace.Nodes)
        ):
            raise AssertionError("Close the current Dynamo graph before this test.")

    clr.AddReference("pyRevitLabs.PyRevit.Runtime.Shared")
    from pyRevitLabs.PyRevit.Runtime.Shared import (
        DynamoExecutionOptions,
        DynamoRevitInterop,
    )

    token = "pyrevit-dynamo-" + uuid.uuid4().hex
    node_id = uuid.uuid4().hex
    started = time.time()
    directory = None
    graph_path = None
    group = None
    try:
        directory = tempfile.mkdtemp(prefix="pyrevit-dynamo-smoke-")
        graph_path = os.path.join(directory, "script.dyn")
        group = DB.TransactionGroup(
            ui_application.ActiveUIDocument.Document, _GRAPH_NAME
        )
        if group.Start() != DB.TransactionStatus.Started:
            raise AssertionError("Dynamo test transaction group did not start.")
        with open(graph_path, "w") as graph_file:
            json.dump(_graph(token, node_id), graph_file)
        options = DynamoExecutionOptions()
        options.GraphPath = graph_path
        options.Automate = True
        options.ExecuteGraph = True
        options.ShowUI = False
        options.ReuseOpenGraph = False
        outcome = DynamoRevitInterop.Run(options, ui_application, Array[String]([]))
        if not outcome.Succeeded:
            raise AssertionError("{}\n{}".format(outcome.Message, outcome.Details))
        model = _model()
        if model is None:
            raise AssertionError("Dynamo accepted the command but did not start.")
        workspace = model.CurrentWorkspace
        if os.path.normcase(str(workspace.FileName)) != os.path.normcase(graph_path):
            raise AssertionError("Dynamo did not open the requested graph.")
        nodes = [node for node in workspace.Nodes if node.GUID.ToString("N") == node_id]
        if len(nodes) != 1:
            raise AssertionError("The expected DesignScript node was not loaded.")
        identifier = nodes[0].GetAstIdentifierForOutputIndex(0).Name
        mirror = model.EngineController.GetMirror(identifier)
        actual = str(mirror.GetData().Data) if mirror is not None else None
        if actual != token:
            raise AssertionError(
                "Graph output {!r} did not match {!r}.".format(actual, token)
            )
        dynamo = next(
            assembly
            for assembly in AppDomain.CurrentDomain.GetAssemblies()
            if assembly.GetName().Name == "DynamoCore"
        )
        return {
            "revit": str(ui_application.Application.VersionNumber),
            "revit_build": str(ui_application.Application.VersionBuild),
            "dynamo": str(dynamo.GetName().Version),
            "token": token,
            "actual": actual,
            "model_state": str(getattr(model, "State", "Output verified")),
            "elapsed_seconds": round(time.time() - started, 3),
        }
    finally:
        execution_failure = traceback.format_exc() if sys.exc_info()[0] else None
        cleanup_failures = _cleanup(group, directory, graph_path)
        if cleanup_failures:
            details = "Cleanup failures:\n" + "\n".join(cleanup_failures)
            if execution_failure:
                details = (
                    "Dynamo execution failure:\n" + execution_failure + "\n" + details
                )
            raise AssertionError(details)


class DynamoExecutionTests(unittest.TestCase):
    """Require actual graph evaluation from the installed Dynamo runtime."""

    def test_fresh_designscript_token_is_evaluated(self):
        """A command status cannot substitute for the fresh graph's output."""
        evidence = assert_dynamo_execution()
        self.assertEqual(evidence["token"], evidence["actual"])
