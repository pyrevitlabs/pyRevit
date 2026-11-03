"""Administrator pins in the machine config over the agent settings and the host.

The pins come from a scratch machine config swapped in by ``agent_harness.admin_pins``
through the internal path seam of ``AgentAdminPolicy``, so the real ``%ProgramData%``
config is never touched, and a lock deployed on the test machine can't change the results.
The seam is in-memory: these tests need the settings code and the agent host to share
one loaded ``pyRevitLabs.Configurations.Ini`` assembly, which is the case in a normal
Revit session. A test that fails on a precondition means the assembly is loaded twice.
"""

from pyrevit.labs import PyRevit

import agent_harness as harness
from agent_harness import AgentRequestError, TestCase, admin_pins, request

CONFIGS = PyRevit.PyRevitConfigs
CONSTS = PyRevit.PyRevitConsts



class SettingsLockTests(TestCase):
    """How a pin changes what the settings read and what they accept."""

    def setUp(self):
        """Remember the user's settings."""
        self.enabled = CONFIGS.GetAgentEnabled()
        self.policy = CONFIGS.GetAgentPolicy()
        self.engine = CONFIGS.GetAgentEngine()
        self.skills = CONFIGS.GetAgentUserSkillsEnabled()

    def tearDown(self):
        """Put the user's settings back."""
        CONFIGS.SetAgentEnabled(self.enabled)
        CONFIGS.SetAgentPolicy(self.policy)
        CONFIGS.SetAgentEngine(self.engine)
        CONFIGS.SetAgentUserSkillsEnabled(self.skills)

    def test_pinned_values_win_over_the_user_config_and_stop_when_unpinned(self):
        """Each pinned setting reads as the pin, and the user's value returns after."""
        CONFIGS.SetAgentEnabled(True)
        CONFIGS.SetAgentEngine("cpython")
        CONFIGS.SetAgentUserSkillsEnabled(True)
        with admin_pins(enabled="false", engine="ironpython", user_skills="false"):
            self.assertTrue(CONFIGS.IsAgentKeyManaged(CONSTS.ConfigsAgentEnabledKey))
            self.assertFalse(CONFIGS.GetAgentEnabled())
            self.assertEqual("ironpython", CONFIGS.GetAgentEngine())
            self.assertFalse(CONFIGS.GetAgentUserSkillsEnabled())
        self.assertFalse(CONFIGS.IsAgentKeyManaged(CONSTS.ConfigsAgentEnabledKey))
        self.assertTrue(CONFIGS.GetAgentEnabled())
        self.assertEqual("cpython", CONFIGS.GetAgentEngine())
        self.assertTrue(CONFIGS.GetAgentUserSkillsEnabled())

    def test_setters_refuse_a_pinned_key_and_leave_the_user_value_alone(self):
        """Changing a pinned setting raises and does not touch the user's config."""
        CONFIGS.SetAgentEnabled(True)
        with admin_pins(enabled="false", engine="ironpython", user_skills="false"):
            with self.assertRaises(Exception):
                CONFIGS.SetAgentEnabled(True)
            with self.assertRaises(Exception):
                CONFIGS.SetAgentEngine("cpython")
            with self.assertRaises(Exception):
                CONFIGS.SetAgentUserSkillsEnabled(True)
        self.assertTrue(CONFIGS.GetAgentEnabled())
        self.assertEqual(self.engine, CONFIGS.GetAgentEngine())

    def test_a_policy_pin_is_a_ceiling_users_may_go_below(self):
        """A pinned policy caps a looser user policy and still accepts a stricter one."""
        CONFIGS.SetAgentPolicy("auto")
        with admin_pins(policy="ask"):
            self.assertEqual("ask", CONFIGS.GetAgentPolicyCeiling())
            self.assertEqual("ask", CONFIGS.GetAgentPolicy())
            with self.assertRaises(Exception):
                CONFIGS.SetAgentPolicy("auto")
            CONFIGS.SetAgentPolicy("readonly")
            self.assertEqual("readonly", CONFIGS.GetAgentPolicy())
        CONFIGS.SetAgentPolicy("auto")
        self.assertIsNone(CONFIGS.GetAgentPolicyCeiling())
        self.assertEqual("auto", CONFIGS.GetAgentPolicy())

    def test_a_malformed_pin_fails_closed(self):
        """A pin that is not a valid value reads as the strictest one."""
        CONFIGS.SetAgentEnabled(True)
        CONFIGS.SetAgentPolicy("auto")
        with admin_pins(enabled="maybe", policy="whatever"):
            self.assertFalse(CONFIGS.GetAgentEnabled())
            self.assertEqual("readonly", CONFIGS.GetAgentPolicy())


class HostLockTests(TestCase):
    """How a pin changes what the running host answers."""

    def test_a_host_pinned_off_refuses_requests_but_still_answers_ping(self):
        """Every request except ping fails with disabled_by_admin while the pin holds."""
        with admin_pins(enabled="false"):
            self.assertTrue(request("ping")["pong"])
            with self.assertRaises(AgentRequestError) as raised:
                request("get_context")
            self.assertEqual("disabled_by_admin", raised.exception.code)
            with self.assertRaises(AgentRequestError) as raised:
                harness.run("result = 1")
            self.assertEqual("disabled_by_admin", raised.exception.code)
        self.assertIn("document", request("get_context"))

    def test_a_host_pinned_on_does_not_refuse(self):
        """Pinning enabled to true does not trigger the refusal."""
        with admin_pins(enabled="true"):
            self.assertIn("document", request("get_context"))

    def test_context_reports_whether_the_policy_is_managed(self):
        """get_context names the capped policy and that an administrator set it."""
        self.assertFalse(request("get_context")["agent"]["policy_managed"])
        with admin_pins(policy="ask"):
            agent = request("get_context")["agent"]
        self.assertTrue(agent["policy_managed"])
        self.assertEqual("ask", agent["policy"])

    def test_a_readonly_ceiling_refuses_modify_runs_and_names_the_administrator(self):
        """With the policy capped at readonly a modify run is refused as admin-set."""
        with admin_pins(policy="readonly"):
            with self.assertRaises(AgentRequestError) as raised:
                harness.run("result = 1", mode="modify")
        self.assertEqual("policy_readonly", raised.exception.code)
        self.assertIn("administrator", raised.exception.message)
