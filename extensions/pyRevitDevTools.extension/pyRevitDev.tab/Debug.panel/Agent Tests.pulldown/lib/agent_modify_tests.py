"""Agent modify runs: decisions, change sets, rollback and the run guard's blocks."""

import os
import os.path as op
import shutil

from pyrevit.labs import PyRevit

import agent_harness as harness
from agent_harness import AgentRequestError, TestCase, run


def _modify(script, dry_run=False, **kwargs):
    return run(
        script, mode="dry_run" if dry_run else "modify", title="Agent test", **kwargs
    )


def _wall():
    return harness.session().wall_ids[0]


class DecisionTests(TestCase):
    """Whether a modify run is committed or rolled back, by mode and policy."""

    def test_dry_run_reports_the_change_and_rolls_it_back(self):
        """A dry run reports the modified element and leaves the model unchanged."""
        before = harness.comment(_wall())
        response = _modify(
            harness.set_comment_script(),
            dry_run=True,
            inputs={"id": _wall(), "text": "agent-dry"},
        )
        self.assertEqual("rolled_back", response["decision"])
        self.assertEqual(1, response["changes"]["modified_count"])
        self.assertEqual(before, harness.comment(_wall()))

    def test_auto_policy_commits_the_change(self):
        """Under policy auto a modify run is committed."""
        response = _modify(
            harness.set_comment_script(), inputs={"id": _wall(), "text": "agent-auto"}
        )
        self.assertEqual("committed", response["decision"])
        self.assertEqual("agent-auto", harness.comment(_wall()))

    def test_change_set_records_added_and_deleted_elements(self):
        """The change set counts an added and then a deleted element."""
        added = _modify(
            "t = DB.Transaction(doc, 'add level')\nt.Start()\n"
            "level = DB.Level.Create(doc, 987.0)\nt.Commit()\nresult = level.Id.Value if hasattr(level.Id, 'Value') else level.Id.IntegerValue\n"
        )
        self.assertEqual(1, added["changes"]["added_count"])
        deleted = _modify(
            "t = DB.Transaction(doc, 'delete level')\nt.Start()\n"
            "doc.Delete(DB.ElementId(inputs['id']))\nt.Commit()\n",
            inputs={"id": added["result"]},
        )
        self.assertEqual(1, deleted["changes"]["deleted_count"])

    def test_readonly_policy_refuses_modify_runs_but_allows_dry_runs(self):
        """Policy readonly refuses a modify run and still allows a dry run."""
        before = harness.comment(_wall())
        with harness.policy("readonly"):
            with self.assertRaises(AgentRequestError) as raised:
                _modify(
                    harness.set_comment_script(),
                    inputs={"id": _wall(), "text": "agent-readonly"},
                )
            dry = _modify(
                harness.set_comment_script(),
                dry_run=True,
                inputs={"id": _wall(), "text": "agent-readonly"},
            )
        self.assertEqual("policy_readonly", raised.exception.code)
        self.assertEqual("ok", dry["status"])
        self.assertEqual(before, harness.comment(_wall()))


class PolicyTests(TestCase):
    """How the policy at the start and at the end of a run decides it."""

    def test_a_modify_run_with_nothing_to_change_reports_no_changes(self):
        """A modify run that changes nothing is reported as no_changes."""
        response = _modify("result = 'nothing to do'")
        self.assertEqual("ok", response["status"])
        self.assertEqual("no_changes", response["decision"])

    def test_auto_policy_reports_that_nobody_was_asked(self):
        """A committed run under policy auto says its approval was auto."""
        response = _modify(
            harness.set_comment_script(),
            inputs={"id": _wall(), "text": "agent-approval"},
        )
        self.assertEqual("committed", response["decision"])
        self.assertEqual("auto", response["approval"])

    def test_a_policy_switched_to_readonly_during_the_run_rolls_it_back(self):
        """The policy is read again before committing, so a run can't outlive a stricter policy."""
        before = harness.comment(_wall())
        try:
            response = _modify(
                "from pyrevit.labs import PyRevit\n"
                "PyRevit.PyRevitConfigs.SetAgentPolicy('readonly')\n"
                + harness.set_comment_script(),
                inputs={"id": _wall(), "text": "agent-too-late"},
            )
        finally:
            PyRevit.PyRevitConfigs.SetAgentPolicy("auto")
        self.assertEqual("rejected", response["status"])
        self.assertEqual("policy_readonly", response["error"]["type"])
        self.assertEqual("rolled_back", response["decision"])
        self.assertEqual(before, harness.comment(_wall()))

    def test_a_policy_changed_outside_revit_applies_to_the_next_request(self):
        """The command pyrevit configs agent policy takes effect without reloading pyRevit."""
        if not op.exists(harness.CLI):
            self.skipTest("bin/pyrevit.exe is not built.")
        before = harness.comment(_wall())
        try:
            harness.run_cli("configs", "agent", "policy", "readonly")
            with self.assertRaises(AgentRequestError) as raised:
                _modify(
                    harness.set_comment_script(),
                    inputs={"id": _wall(), "text": "agent-outside"},
                )
            unchanged = harness.comment(_wall())
        finally:
            harness.run_cli("configs", "agent", "policy", "auto")
        self.assertEqual("policy_readonly", raised.exception.code)
        self.assertEqual(before, unchanged)
        restored = _modify(
            harness.set_comment_script(),
            inputs={"id": _wall(), "text": "agent-restored"},
        )
        self.assertEqual("committed", restored["decision"])


class RollbackTests(TestCase):
    """Runs that fail must leave the model as it was."""

    def test_error_after_a_committed_transaction_rolls_back_the_run(self):
        """An error after a committed transaction rolls the whole run back."""
        before = harness.comment(_wall())
        response = _modify(
            harness.set_comment_script() + "raise ValueError('boom')\n",
            inputs={"id": _wall(), "text": "agent-half"},
        )
        self.assertEqual("error", response["status"])
        self.assertEqual(before, harness.comment(_wall()))

    def test_transaction_left_open_is_rolled_back_without_crashing(self):
        """A transaction the script leaves open is rolled back and reported, and Revit keeps working."""
        before = harness.comment(_wall())
        response = _modify(
            "t = DB.Transaction(doc, 'left open')\nt.Start()\n"
            "doc.GetElement(DB.ElementId(inputs['id'])).get_Parameter({}).Set('agent-open')\n".format(
                harness.COMMENTS
            ),
            inputs={"id": _wall()},
        )
        self.assertEqual("transaction_left_open", response["error"]["type"])
        self.assertEqual(before, harness.comment(_wall()))
        self.assertFalse(harness.session().project.IsModifiable)

    def test_function_local_transaction_is_rolled_back_after_an_error(self):
        """An error cannot orphan a transaction that only a helper function can reach."""
        before = harness.comment(_wall())
        response = _modify(
            "def change():\n"
            "    transaction = DB.Transaction(doc, 'helper transaction')\n"
            "    transaction.Start()\n"
            "    doc.GetElement(DB.ElementId(inputs['id'])).get_Parameter({}).Set('agent-local')\n"
            "    raise ValueError('boom')\n"
            "change()\n".format(harness.COMMENTS),
            inputs={"id": _wall()},
        )
        self.assertEqual("ValueError", response["error"]["type"])
        self.assertEqual(before, harness.comment(_wall()))
        self.assertFalse(harness.session().project.IsModifiable)

    def test_nonzero_system_exit_rolls_back_a_modify_run(self):
        """A failing explicit exit rolls the guarded run back."""
        before = harness.comment(_wall())
        response = _modify(
            harness.set_comment_script() + "raise SystemExit(1)\n",
            inputs={"id": _wall(), "text": "agent-exit"},
        )
        self.assertEqual("SystemExit", response["error"]["type"])
        self.assertEqual(before, harness.comment(_wall()))

    def test_timeout_rolls_back_a_modify_run(self):
        """A modify run past its timeout is stopped and rolled back."""
        response = _modify("while True:\n    pass\n", timeout=3)
        self.assertEqual("timeout", response["error"]["type"])


class BlockTests(TestCase):
    """Operations the run guard blocks or reports."""

    def tearDown(self):
        """Resume the session a run that changed another document paused."""
        harness.restore_session()

    def test_save_as_of_the_active_document_writes_no_file(self):
        """Save As of the active document writes no file."""
        target = op.join(harness.session().folder, "save-as.rvt")
        response = _modify(
            "options = DB.SaveAsOptions()\noptions.OverwriteExistingFile = True\ndoc.SaveAs(inputs['path'], options)\n",
            inputs={"path": target},
        )
        self.assertNotEqual("ok", response["status"])
        self.assertFalse(op.exists(target))

    def test_file_export_is_blocked(self):
        """A DWG export is blocked and writes nothing."""
        folder = op.join(harness.session().folder, "export")
        os.makedirs(folder)
        response = _modify(
            "from System.Collections.Generic import List\nviews = List[DB.ElementId]()\n"
            "views.Add(doc.ActiveView.Id)\ndoc.Export(inputs['folder'], 'agent', views, DB.DWGExportOptions())\n",
            inputs={"folder": folder},
        )
        self.assertIn(
            "file_export", [entry["operation"] for entry in response["blocked"]]
        )
        self.assertEqual([], os.listdir(folder))

    def test_document_opened_in_the_background_cannot_be_saved_and_is_closed(self):
        """A document the run opens can't be saved, and it is closed after the run."""
        copy = op.join(harness.session().folder, "background.rvt")
        shutil.copyfile(harness.session().other_path, copy)
        stamp = os.path.getmtime(copy)
        response = _modify(
            "other = app.OpenDocumentFile(inputs['path'])\n"
            "t = DB.Transaction(other, 'touch')\nt.Start()\nDB.Level.Create(other, 50.0)\nt.Commit()\nother.Save()\n",
            inputs={"path": copy},
        )
        self.assertIn("save", [entry["operation"] for entry in response["blocked"]])
        self.assertEqual(stamp, os.path.getmtime(copy))
        harness.restore_session()
        titles = [
            document["title"]
            for document in harness.request("get_context")["open_documents"]
        ]
        self.assertNotIn("background", titles)

    def test_document_created_by_a_run_cannot_be_saved(self):
        """A document the run creates can't be saved."""
        target = op.join(harness.session().folder, "created.rvt")
        response = _modify(
            "created = app.NewProjectDocument(DB.UnitSystem.Metric)\n"
            "options = DB.SaveAsOptions()\noptions.OverwriteExistingFile = True\n"
            "created.SaveAs(inputs['path'], options)\n",
            inputs={"path": target},
        )
        self.assertIn("save_as", [entry["operation"] for entry in response["blocked"]])
        self.assertFalse(op.exists(target))

    def test_change_to_another_open_document_fails_rolls_back_and_pauses(self):
        """Changing another open document fails the run, rolls that document back and pauses the session."""
        title = harness.session().other_title
        levels = "result = DB.FilteredElementCollector([d for d in app.Documents if d.Title == inputs['title']][0]).OfClass(DB.Level).GetElementCount()"
        before = harness.run(levels, inputs={"title": title})["result"]
        response = _modify(
            "other = [d for d in app.Documents if d.Title == inputs['title']][0]\n"
            "t = DB.Transaction(other, 'touch other')\nt.Start()\nDB.Level.Create(other, 50.0)\nt.Commit()\n",
            inputs={"title": title},
        )
        self.assertEqual("other_document_modified", response["error"]["type"])
        outcome = response["changes"]["other_documents"][0]
        self.assertEqual(title, outcome["document"])
        self.assertTrue(outcome["rolled_back"])
        with self.assertRaises(AgentRequestError) as raised:
            harness.request("get_context")
        self.assertEqual("paused_by_host", raised.exception.code)
        self.assertIn(title, raised.exception.message)
        self.assertIn(title, harness.session_status()["paused_reason"])
        harness.resume_session()
        self.assertEqual(before, harness.run(levels, inputs={"title": title})["result"])

    def test_warnings_are_reported(self):
        """Revit warnings raised during a run are reported as failures."""
        response = _modify(
            "level = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()\n"
            "line = DB.Line.CreateBound(DB.XYZ(500, 500, 0), DB.XYZ(520, 500, 0))\n"
            "t = DB.Transaction(doc, 'walls')\nt.Start()\n"
            "DB.Wall.Create(doc, line, level.Id, False)\nDB.Wall.Create(doc, line, level.Id, False)\nt.Commit()\n",
            dry_run=True,
        )
        self.assertIn(
            "Warning", [failure["severity"] for failure in response["failures"]]
        )
