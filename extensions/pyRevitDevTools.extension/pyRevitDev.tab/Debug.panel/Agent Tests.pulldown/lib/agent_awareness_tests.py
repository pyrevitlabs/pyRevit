"""Change awareness: what the user changed between an agent's calls.

A model request's response carries ``since_last_call`` when the user edited one of
the session's documents, switched views or changed the selection since the previous
request, each named by the document it happened in. The host's own changes are never reported back. Each test first makes
one request so it starts from a clean slate, and leaves the model, view and
selection as it found them.
"""

from System.Collections.Generic import List

from pyrevit import DB

import agent_harness as harness
from agent_harness import TestCase, request

USER_EDIT = "Agent test user edit"


def _catch_up():
    """Make one request, so the next one reports only what happens after it."""
    request("get_context")


def _create_level(document, name=USER_EDIT):
    transaction = DB.Transaction(document, name)
    transaction.Start()
    level = DB.Level.Create(document, 30.0)
    transaction.Commit()
    return level.Id


def _delete(document, element_id):
    transaction = DB.Transaction(document, "Agent test cleanup")
    transaction.Start()
    document.Delete(element_id)
    transaction.Commit()


def _uidoc():
    return harness.session().uiapp.ActiveUIDocument


def _clear_selection():
    _uidoc().Selection.SetElementIds(List[DB.ElementId]())


def _add_other_document():
    """Add the scratch session's other project to the agent session, then go back."""
    scratch = harness.session()
    try:
        scratch.activate(scratch.other_path)
        harness.add_document()
    finally:
        scratch.activate(scratch.project_path)


def _another_view(document, active):
    active_id = harness.id_value(active.Id)
    for view in DB.FilteredElementCollector(document).OfClass(DB.ViewPlan):
        if not view.IsTemplate and harness.id_value(view.Id) != active_id:
            return view
    return None


class AwarenessTests(TestCase):
    """Edits, view switches and selection changes reported on the next request."""

    def tearDown(self):
        """Put back the session every test starts from."""
        harness.restore_session()

    def _summary(self, response):
        self.assertIn("since_last_call", response)
        return response["since_last_call"]

    def test_a_user_edit_is_reported_once(self):
        """An edit between calls rides on the next response, and only that one."""
        scratch = harness.session()
        project = scratch.project
        _catch_up()
        level_id = _create_level(project)
        try:
            [edits] = self._summary(harness.run("result = 1"))["edits"]
            self.assertEqual(harness.key_of(scratch.project_path), edits["document"])
            self.assertEqual(project.Title, edits["document_title"])
            self.assertGreaterEqual(edits["added"], 1)
            self.assertIn(harness.id_value(level_id), edits["added_ids"])
            self.assertIn(USER_EDIT, edits["operations"])
            self.assertNotIn("since_last_call", request("get_context"))
        finally:
            _delete(project, level_id)
            _catch_up()

    def test_a_rolled_back_edit_is_not_reported(self):
        """A transaction the user rolls back leaves nothing to report."""
        project = harness.session().project
        _catch_up()
        transaction = DB.Transaction(project, USER_EDIT)
        transaction.Start()
        DB.Level.Create(project, 30.0)
        transaction.RollBack()
        self.assertNotIn("since_last_call", request("get_context"))

    def test_a_rolled_back_transaction_group_cancels_its_edits(self):
        """An element committed inside a group the user then rolls back isn't reported."""
        project = harness.session().project
        _catch_up()
        group = DB.TransactionGroup(project, "Agent test group")
        group.Start()
        level_id = _create_level(project)
        group.RollBack()
        summary = request("get_context").get("since_last_call") or {}
        added_ids = [
            element_id
            for edits in summary.get("edits") or []
            for element_id in edits["added_ids"]
        ]
        self.assertNotIn(harness.id_value(level_id), added_ids)

    def test_edits_to_another_document_are_not_reported(self):
        """Only the session's documents are watched."""
        other = harness.session().other
        _catch_up()
        _delete(other, _create_level(other))
        self.assertNotIn("since_last_call", request("get_context"))

    def test_edits_to_two_session_documents_are_reported_apart(self):
        """Each document's edits come under its own key, so their ids never mix."""
        scratch = harness.session()
        _add_other_document()
        _catch_up()
        project_level = _create_level(scratch.project)
        other_level = _create_level(scratch.other)
        try:
            edits = self._summary(request("get_context"))["edits"]
            by_document = dict((entry["document"], entry) for entry in edits)
            project_key = harness.key_of(scratch.project_path)
            other_key = harness.key_of(scratch.other_path)
            self.assertEqual(sorted([project_key, other_key]), sorted(by_document))
            self.assertIn(
                harness.id_value(project_level), by_document[project_key]["added_ids"]
            )
            self.assertIn(
                harness.id_value(other_level), by_document[other_key]["added_ids"]
            )
        finally:
            _delete(scratch.project, project_level)
            _delete(scratch.other, other_level)
            _catch_up()

    def test_switching_to_another_session_document_is_a_view_change(self):
        """The view now active is reported with its document, even if its id matches the last one."""
        scratch = harness.session()
        _add_other_document()
        try:
            scratch.activate(scratch.other_path)
            _catch_up()
        finally:
            scratch.activate(scratch.project_path)
        view = self._summary(request("get_context"))["active_view"]
        self.assertEqual(harness.key_of(scratch.project_path), view["document"])
        self.assertEqual(scratch.project.Title, view["document_title"])
        _catch_up()

    def test_the_hosts_own_changes_are_not_reported_back(self):
        """Show requests and committed runs don't count as the user's changes."""
        walls = harness.session().wall_ids[:1]
        _catch_up()
        request("show", action="select", ids=walls)
        request("show", action="isolate", ids=walls, zoom=False)
        request("show", action="reset")
        harness.run(
            harness.set_comment_script(),
            mode="modify",
            title="Agent test",
            inputs={"id": walls[0], "text": "agent-awareness"},
        )
        self.assertNotIn("since_last_call", request("get_context"))

    def test_switching_views_is_reported(self):
        """A view switch names the view now active."""
        uidoc = _uidoc()
        original = uidoc.ActiveView
        target = _another_view(uidoc.Document, original)
        if target is None:
            self.skipTest("The scratch project has no second plan view.")
        _catch_up()
        try:
            uidoc.ActiveView = target
            view = self._summary(request("get_context"))["active_view"]
            self.assertEqual(
                harness.key_of(harness.session().project_path), view["document"]
            )
            self.assertEqual(harness.id_value(target.Id), view["id"])
            self.assertEqual(target.Name, view["name"])
        finally:
            uidoc.ActiveView = original
            _catch_up()

    def test_a_round_trip_to_another_document_is_not_a_view_change(self):
        """Coming back from a document outside the session to the same view reports nothing."""
        scratch = harness.session()
        _catch_up()
        scratch.activate(scratch.other_path)
        scratch.activate(scratch.project_path)
        self.assertNotIn("since_last_call", request("get_context"))

    def test_a_selection_change_is_reported(self):
        """A changed selection is described with its count and ids."""
        uidoc = _uidoc()
        walls = DB.FilteredElementCollector(uidoc.Document).OfClass(DB.Wall)
        _clear_selection()
        _catch_up()
        try:
            uidoc.Selection.SetElementIds(walls.ToElementIds())
            selection = self._summary(request("get_context"))["selection"]
            expected = sorted(harness.session().wall_ids)
            self.assertEqual(len(expected), selection["count"])
            self.assertEqual(expected, sorted(selection["ids"]))
        finally:
            _clear_selection()
            _catch_up()

    def test_a_new_session_starts_with_nothing_to_report(self):
        """Changes made before a session starts are not reported to it."""
        project = harness.session().project
        level_id = _create_level(project)
        try:
            harness.end_session()
            harness.start_session()
            self.assertNotIn("since_last_call", request("get_context"))
        finally:
            _delete(project, level_id)
            _catch_up()
