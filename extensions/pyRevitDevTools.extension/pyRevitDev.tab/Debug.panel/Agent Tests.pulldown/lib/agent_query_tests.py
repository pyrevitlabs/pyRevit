"""Agent query runs on both engines: results, errors, timeouts, workspaces and records."""

import json
import os
import os.path as op
from unittest import TestCase

import agent_harness as harness
from agent_harness import ENGINES, run


def _script_lines(response):
    traceback = (response.get("error") or {}).get("traceback") or ""
    return [line.strip() for line in traceback.splitlines() if "<agent-script>" in line]


class ResultTests(TestCase):
    """How run results and printed output come back."""

    def test_results_serialize_revit_objects_and_capture_prints(self):
        """Results serialize XYZ, elements and ids, and prints are captured."""
        for engine in ENGINES:
            response = run(
                "print('hello ' + inputs['who'])\n"
                "wall = DB.FilteredElementCollector(doc).OfClass(DB.Wall).FirstElement()\n"
                "result = {'doubled': inputs['n'] * 2, 'point': DB.XYZ(1, 2, 3),"
                " 'wall': wall, 'id': wall.Id, 'items': [1, 'a', None]}\n",
                engine=engine,
                inputs={"n": 21, "who": "agent"},
            )
            self.assertEqual("ok", response["status"], engine)
            self.assertEqual(engine, response["engine"]["implementation"])
            self.assertIn("hello agent", response["output"], engine)
            result = response["result"]
            self.assertEqual(42, result["doubled"], engine)
            self.assertEqual([1.0, 2.0, 3.0], result["point"], engine)
            self.assertEqual(result["wall"]["id"], result["id"], engine)
            self.assertEqual([1, "a", None], result["items"], engine)


class ErrorTests(TestCase):
    """How script errors are reported."""

    def test_runtime_errors_point_at_the_script_line(self):
        """A runtime error's traceback names the failing script line."""
        for engine in ENGINES:
            response = run("a = 1\nb = 2\nc = undefined_name", engine=engine)
            self.assertEqual("NameError", response["error"]["type"], engine)
            self.assertTrue(
                any("line 3" in line for line in _script_lines(response)), engine
            )

    def test_syntax_errors_are_reported(self):
        """A syntax error is reported as SyntaxError."""
        for engine in ENGINES:
            response = run("a = 1\nb = (\n", engine=engine)
            self.assertEqual("SyntaxError", response["error"]["type"], engine)


class TimeoutTests(TestCase):
    """The run timeout."""

    def test_timeout_stops_a_script_that_catches_everything(self):
        """The timeout stops a loop even when it catches every exception."""
        for engine in ENGINES:
            response = run(
                "while True:\n    try:\n        pass\n    except:\n        pass\n",
                engine=engine,
                timeout=3,
            )
            self.assertEqual("timeout", response["error"]["type"], engine)


class ModelGuardTests(TestCase):
    """Query runs must leave the model unchanged."""

    def test_query_that_changes_the_model_is_rolled_back(self):
        """A query that writes fails with query_modified_model and leaves the model as it was."""
        wall = harness.session().wall_ids[0]
        before = harness.comment(wall)
        response = run(
            harness.set_comment_script(),
            inputs={"id": wall, "text": "agent-query-write"},
        )
        self.assertEqual("query_modified_model", response["error"]["type"])
        self.assertEqual(before, harness.comment(wall))


class WorkspaceTests(TestCase):
    """The workspace folder put on sys.path for a run."""

    def test_workspace_modules_are_fresh_across_runs_and_folders(self):
        """A workspace module is re-imported every run and never leaks into another workspace."""
        root = harness.session().folder
        first = op.join(root, "workspace-a")
        second = op.join(root, "workspace-b")
        harness.write_module(first, "agent_helper", "VALUE = 'a1'\n")
        harness.write_module(second, "agent_helper", "VALUE = 'b1'\n")
        script = "import agent_helper\nresult = agent_helper.VALUE"
        for engine in ENGINES:
            self.assertEqual(
                "a1", run(script, engine=engine, workspace=first)["result"], engine
            )
            harness.write_module(first, "agent_helper", "VALUE = 'a2'\n")
            self.assertEqual(
                "a2", run(script, engine=engine, workspace=first)["result"], engine
            )
            self.assertEqual(
                "b1", run(script, engine=engine, workspace=second)["result"], engine
            )
            harness.write_module(first, "agent_helper", "VALUE = 'a1'\n")


class RecordTests(TestCase):
    """Output limits and the run record written to disk."""

    def test_long_output_is_truncated_and_recorded_on_disk(self):
        """Long output is truncated in the response and the run record is written to disk."""
        response = run(
            "for i in range(4000):\n    print('output line %d' % i)\nresult = 'done'"
        )
        self.assertTrue(response["output_truncated"])
        self.assertTrue(op.isdir(response["run_dir"]))
        with open(op.join(response["run_dir"], "request.json")) as handle:
            self.assertEqual("query", json.load(handle)["mode"])
        self.assertTrue(
            any(name.startswith("response") for name in os.listdir(response["run_dir"]))
        )
