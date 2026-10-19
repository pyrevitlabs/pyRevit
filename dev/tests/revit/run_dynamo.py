"""Journal entry point for #2992 validation in a disposable Revit process.

Run with ``pyrevit run <absolute-script-path> --revit=<year> --purge``. The journal owns
the process and exits it afterward. Reports remain under .test-results/dynamo;
this script must never be executed in an existing user session.
"""

import hashlib
import json
import os
import traceback
import uuid

from pyrevit import DB, EXEC_PARAMS
from pyrevit.unittests import test_dynamo_execution


def run():
    """Check cold/warm Dynamo execution in a new project and persist the result.

    Raises:
        RuntimeError: Not running through the journal batch runner.
        AssertionError: Startup or either unique graph token fails validation.
    """
    try:
        batch_mode = __batchexec__
    except NameError:
        batch_mode = False
    if not batch_mode:
        raise RuntimeError("Use pyrevit run in a disposable journal session.")
    uiapp = __revit__
    year = str(uiapp.Application.VersionNumber)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    run_id = uuid.uuid4().hex
    reports = os.path.join(root, ".test-results", "dynamo", year, run_id)
    os.makedirs(reports)
    report_path = os.path.join(reports, "result.json")
    report = {"revit": year, "run_id": run_id, "status": "started"}
    with open(report_path, "w") as report_file:
        json.dump(report, report_file, indent=2)
    try:
        directory = os.path.dirname(
            str(EXEC_PARAMS.command_data.JournalData["LogFile"])
        )
        model_path = os.path.join(directory, "DynamoValidation.rvt")
        project = uiapp.Application.NewProjectDocument(DB.UnitSystem.Metric)
        project.SaveAs(model_path)
        project.Close(False)
        uiapp.OpenAndActivateDocument(model_path)
        report["cold"] = test_dynamo_execution.assert_dynamo_execution(uiapp)
        report["warm"] = test_dynamo_execution.assert_dynamo_execution(uiapp)
        if report["cold"]["token"] == report["warm"]["token"]:
            raise AssertionError("The repeat run reused its execution token.")
        source_path = test_dynamo_execution.__file__.replace(".pyc", ".py")
        with open(source_path, "rb") as source:
            report["source_sha256"] = hashlib.sha256(source.read()).hexdigest()
        report["status"] = "passed"
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        with open(report_path, "w") as report_file:
            json.dump(report, report_file, indent=2)


if __name__ == "__main__":
    run()
