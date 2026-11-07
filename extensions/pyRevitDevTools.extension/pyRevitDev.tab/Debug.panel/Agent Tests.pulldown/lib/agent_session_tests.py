"""Agent sessions: the user's consent in Revit, checked on every model request.

``run_suites`` makes sessions start in the panel and starts one on the scratch
project before the modules run. Every test here restores that session when it ends.
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
    "for name, args in (('Resume', None), ('SetSessionStart', Array[Object](['auto']))):\n"
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

    def test_the_session_is_on_the_active_scratch_project(self):
        """The suite's session is active, started by the user, and names its document."""
        status = harness.session_status()
        self.assertEqual("active", status["state"])
        self.assertEqual("user", status["start"])
        self.assertFalse(status["automatic"])
        self.assertEqual([harness.session().project.Title], harness.session_titles())

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

    def test_when_sessions_start_automatically_a_request_starts_one_on_every_document(
        self,
    ):
        """The first request starts a session that covers every open document."""
        scratch = harness.session()
        harness.end_session()
        harness.set_session_start("auto")
        other_key = harness.key_of(scratch.other_path)
        response = harness.run("result = doc.Title", document=other_key)
        status = harness.session_status()
        self.assertEqual(scratch.other.Title, response["result"])
        self.assertTrue(status["automatic"])
        self.assertIn(scratch.project.Title, harness.session_titles())
        self.assertIn(scratch.other.Title, harness.session_titles())

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

    def test_run_code_can_not_resume_its_session_or_make_sessions_start_automatically(
        self,
    ):
        """A run may pause its own session, but can't resume it or loosen how sessions start."""
        response = harness.run(SELF_GRANT_SCRIPT)
        status = harness.session_status()
        self.assertEqual(["refused", "refused"], response["result"])
        self.assertEqual("paused", status["state"])
        self.assertEqual("user", status["start"])

    def test_an_added_document_joins_the_session_and_is_reported(self):
        """Adding a document keeps the session and its first document, and the agent hears of it."""
        scratch = harness.session()
        session_id = harness.session_status()["id"]
        project_key = harness.key_of(scratch.project_path)
        other_key = harness.key_of(scratch.other_path)
        try:
            scratch.activate(scratch.other_path)
            harness.add_document()
        finally:
            scratch.activate(scratch.project_path)
        self.assertEqual(session_id, harness.session_status()["id"])
        self.assertEqual(
            [scratch.project.Title, scratch.other.Title], harness.session_titles()
        )
        joined = harness.request("get_context")["since_last_call"]["documents"][
            "joined"
        ]
        self.assertEqual([other_key], [document["key"] for document in joined])
        self.assertEqual(
            scratch.other.Title,
            harness.run("result = doc.Title", document=other_key)["result"],
        )
        self.assertEqual(
            scratch.project.Title,
            harness.run("result = doc.Title", document=project_key)["result"],
        )

    def test_an_unknown_key_is_refused(self):
        """A key no open document has is refused before anything runs."""
        with self.assertRaises(AgentRequestError) as raised:
            harness.run("result = 1", document="doc-0")
        self.assertEqual("unknown_document", raised.exception.code)
        self.assertIn("get_context", raised.exception.message)

    def test_while_sessions_start_automatically_nothing_can_end_the_session(self):
        """Ending it would only let the next request start another, so pause is the stop."""
        harness.set_session_start("auto")
        with self.assertRaises(AgentRequestError) as raised:
            harness.request("end_session")
        self.assertEqual("session_locked", raised.exception.code)
        self.assertEqual("refused", harness.run(END_SCRIPT)["result"])
        self.assertEqual("active", harness.session_status()["state"])

    def test_adding_a_document_already_in_the_session_is_refused(self):
        """The panel decides by title, so the host refuses to add the same document twice."""
        with self.assertRaises(AgentRequestError) as raised:
            harness.add_document()
        self.assertEqual("already_in_session", raised.exception.code)

    def test_a_session_ends_with_its_last_document(self):
        """Closing one of the session's documents keeps it; closing the last ends it."""
        scratch = harness.session()
        first_path = scratch.create_extra("agent-test-first.rvt")
        second_path = scratch.create_extra("agent-test-second.rvt")
        try:
            scratch.activate(first_path)
            first = scratch.uiapp.ActiveUIDocument.Document
            harness.end_session()
            harness.start_session()
            scratch.activate(second_path)
            second = scratch.uiapp.ActiveUIDocument.Document
            harness.add_document()
        finally:
            scratch.activate(scratch.project_path)
        second_title = second.Title
        first.Close(False)
        titles_after_first = harness.session_titles()
        second.Close(False)
        status = harness.session_status()
        self.assertEqual([second_title], titles_after_first)
        self.assertEqual("inactive", status["state"])
        self.assertEqual("document_closed", status["last_ended"]["reason"])

    def test_closing_the_sessions_only_document_ends_the_session(self):
        """A session ends with its only document, and the host says why."""
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
