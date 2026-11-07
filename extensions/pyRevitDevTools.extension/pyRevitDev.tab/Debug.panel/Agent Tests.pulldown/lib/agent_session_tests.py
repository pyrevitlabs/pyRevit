"""Agent sessions: the user's consent in Revit, checked on every model request.

``run_suites`` requires sessions and starts one on the scratch project before
the modules run. Every test here restores that session when it ends.
"""

import agent_harness as harness
from agent_harness import AgentRequestError, TestCase

SELF_GRANT_SCRIPT = (
    "from System import Array, Object\n"
    "from pyrevit.coreutils import assmutils\n"
    "from pyrevit.runtime import RUNTIME_ASSM\n"
    "sessions = assmutils.find_type_by_name(\n"
    "    RUNTIME_ASSM, 'PyRevitLabs.PyRevit.Runtime.Agent.AgentSessions')\n"
    "sessions.GetMethod('Pause').Invoke(None, None)\n"
    "result = []\n"
    "for name, args in (('Resume', None), ('SetRequired', Array[Object]([False]))):\n"
    "    try:\n"
    "        sessions.GetMethod(name).Invoke(None, args)\n"
    "        result.append('allowed')\n"
    "    except Exception:\n"
    "        result.append('refused')\n"
)

END_SCRIPT = (
    "from pyrevit.coreutils import assmutils\n"
    "from pyrevit.runtime import RUNTIME_ASSM\n"
    "sessions = assmutils.find_type_by_name(\n"
    "    RUNTIME_ASSM, 'PyRevitLabs.PyRevit.Runtime.Agent.AgentSessions')\n"
    "try:\n"
    "    sessions.GetMethod('End').Invoke(None, None)\n"
    "    result = 'allowed'\n"
    "except Exception:\n"
    "    result = 'refused'\n"
)


class SessionTests(TestCase):
    """Starting, pausing and ending a session, and what each state lets through."""

    def tearDown(self):
        """Put back the session every test starts from."""
        harness.restore_session()

    def test_the_session_is_bound_to_the_active_scratch_project(self):
        """The suite's session is active, required, and names its document."""
        status = harness.session_status()
        self.assertEqual("active", status["state"])
        self.assertTrue(status["required"])
        self.assertEqual(harness.session().project.Title, status["document"])

    def test_ping_and_get_context_report_the_session(self):
        """Clients see the session without asking for it separately."""
        session_id = harness.session_status()["id"]
        self.assertEqual(session_id, harness.request("ping")["session"]["id"])
        context = harness.request("get_context")
        self.assertEqual(session_id, context["agent"]["session"]["id"])

    def test_a_paused_session_refuses_model_requests_until_resumed(self):
        """A pause over the pipe refuses model requests as the agent's, while ping and lookups stay open."""
        harness.request("pause_session")
        with self.assertRaises(AgentRequestError) as raised:
            harness.request("get_context")
        self.assertEqual("paused_by_agent", raised.exception.code)
        self.assertTrue(harness.request("ping")["pong"])
        self.assertTrue(harness.request("lookup_api", name="Wall")["found"])
        harness.resume_session()
        self.assertIsNotNone(harness.request("get_context")["document"])

    def test_without_a_session_model_requests_are_refused(self):
        """Ending the session refuses runs, and the refusal says how to ask again."""
        harness.request("end_session")
        with self.assertRaises(AgentRequestError) as raised:
            harness.run("result = 1")
        self.assertEqual("session_inactive", raised.exception.code)
        self.assertIn("request_session", raised.exception.message)
        last_ended = harness.session_status()["last_ended"]
        self.assertEqual("ended_by_client", last_ended["reason"])

    def test_without_a_session_a_read_only_policy_still_asks_for_one(self):
        """A modify run with no session is refused for the session before the policy."""
        harness.request("end_session")
        with harness.policy("readonly"):
            with self.assertRaises(AgentRequestError) as raised:
                harness.run("result = 1", mode="modify")
        self.assertEqual("session_inactive", raised.exception.code)

    def test_when_sessions_are_optional_requests_pass_without_one(self):
        """With sessions optional and none started, runs work as they did before sessions."""
        harness.end_session()
        harness.require_sessions(False)
        self.assertEqual(1, harness.run("result = 1")["result"])

    def test_a_request_for_another_document_is_refused(self):
        """A run named for, or defaulting to, a document outside the session is refused."""
        scratch = harness.session()
        other_key = harness.key_of(scratch.other_path)
        try:
            scratch.activate(scratch.other_path)
            with self.assertRaises(AgentRequestError) as by_default:
                harness.run("result = 1")
        finally:
            scratch.activate(scratch.project_path)
        with self.assertRaises(AgentRequestError) as by_key:
            harness.run("result = 1", document=other_key)
        for raised in (by_default, by_key):
            self.assertEqual("document_not_in_session", raised.exception.code)
            self.assertIn(scratch.project.Title, raised.exception.message)

    def test_the_sessions_document_works_while_another_is_active(self):
        """Named by key, the session's document runs without being active, with no uidoc."""
        scratch = harness.session()
        project_key = harness.key_of(scratch.project_path)
        try:
            scratch.activate(scratch.other_path)
            context = harness.request("get_context")
            response = harness.run(
                "result = [doc.Title, uidoc is None]", document=project_key
            )
        finally:
            scratch.activate(scratch.project_path)
        self.assertEqual(scratch.other.Title, context["document"]["title"])
        self.assertEqual([scratch.project.Title, True], response["result"])
        self.assertEqual(project_key, response["document_key"])

    def test_a_request_for_a_session_is_kept_until_one_starts(self):
        """request_session records the agent's reason; starting a session clears it."""
        harness.end_session()
        answer = harness.request("request_session", reason="Renumber the doors")
        self.assertTrue(answer["requested"])
        pending = answer["session"]["pending_request"]
        self.assertEqual("Renumber the doors", pending["reason"])
        harness.start_session()
        self.assertIsNone(harness.session_status()["pending_request"])

    def test_a_second_session_can_not_start_while_one_is_active(self):
        """Starting again while a session is active is refused."""
        with self.assertRaises(AgentRequestError) as raised:
            harness.start_session()
        self.assertEqual("session_active", raised.exception.code)

    def test_run_code_can_not_resume_or_unrequire_its_session(self):
        """A run may pause its own session, but can't resume it or make sessions optional."""
        response = harness.run(SELF_GRANT_SCRIPT)
        status = harness.session_status()
        self.assertEqual(["refused", "refused"], response["result"])
        self.assertEqual("paused", status["state"])
        self.assertTrue(status["required"])

    def test_a_moved_session_refuses_the_document_it_left(self):
        """After a move, the old document's key is refused and the move is reported."""
        scratch = harness.session()
        session_id = harness.session_status()["id"]
        left_key = harness.key_of(scratch.project_path)
        scratch.activate(scratch.other_path)
        harness.move_session()
        status = harness.session_status()
        self.assertEqual(session_id, status["id"])
        self.assertEqual(
            [scratch.project.Title, scratch.other.Title], status["documents"]
        )
        with self.assertRaises(AgentRequestError) as raised:
            harness.run("result = 1", document=left_key)
        self.assertEqual("document_not_in_session", raised.exception.code)
        moved = harness.request("get_context")["since_last_call"]["session_moved"]
        self.assertEqual(scratch.project.Title, moved["from"])
        self.assertEqual(scratch.other.Title, moved["to"])
        self.assertEqual(
            scratch.other.Title, harness.run("result = doc.Title")["result"]
        )

    def test_an_unknown_key_is_refused(self):
        """A key no open document has is refused before anything runs."""
        with self.assertRaises(AgentRequestError) as raised:
            harness.run("result = 1", document="doc-0")
        self.assertEqual("unknown_document", raised.exception.code)
        self.assertIn("get_context", raised.exception.message)

    def test_while_sessions_are_optional_agents_can_not_end_the_session(self):
        """Ending it would open every document to agents, so the pipe and run code can't."""
        harness.require_sessions(False)
        with self.assertRaises(AgentRequestError) as raised:
            harness.request("end_session")
        self.assertEqual("session_locked", raised.exception.code)
        self.assertEqual("refused", harness.run(END_SCRIPT)["result"])
        self.assertEqual("active", harness.session_status()["state"])

    def test_moving_to_the_document_the_session_is_on_is_refused(self):
        """The panel decides by title, so the host refuses a move to the same document."""
        with self.assertRaises(AgentRequestError) as raised:
            harness.move_session()
        self.assertEqual("already_bound", raised.exception.code)

    def test_a_moved_session_ends_with_its_new_document_only(self):
        """Closing the document the session left keeps it; closing its new one ends it."""
        scratch = harness.session()
        left_path = scratch.create_extra("agent-test-move-from.rvt")
        moved_path = scratch.create_extra("agent-test-move-to.rvt")
        try:
            scratch.activate(left_path)
            left = scratch.uiapp.ActiveUIDocument.Document
            harness.end_session()
            harness.start_session()
            scratch.activate(moved_path)
            moved = scratch.uiapp.ActiveUIDocument.Document
            harness.move_session()
        finally:
            scratch.activate(scratch.project_path)
        left.Close(False)
        state_after_leaving = harness.session_status()["state"]
        moved.Close(False)
        status = harness.session_status()
        self.assertEqual("active", state_after_leaving)
        self.assertEqual("inactive", status["state"])
        self.assertEqual("document_closed", status["last_ended"]["reason"])

    def test_closing_the_bound_document_ends_the_session(self):
        """A session ends with its document, and the host says why."""
        scratch = harness.session()
        path = scratch.create_extra("agent-test-closing.rvt")
        scratch.activate(path)
        closing = scratch.uiapp.ActiveUIDocument.Document
        try:
            harness.end_session()
            harness.start_session()
        finally:
            scratch.activate(scratch.project_path)
            closing.Close(False)
        status = harness.session_status()
        self.assertEqual("inactive", status["state"])
        self.assertEqual("document_closed", status["last_ended"]["reason"])
