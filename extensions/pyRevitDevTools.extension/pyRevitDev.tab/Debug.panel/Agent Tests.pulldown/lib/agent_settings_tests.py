"""The agent settings: valid values, rejected values, and unknown stored values.

These tests change the real pyRevit config and put every value back afterwards.
"""

import os.path as op

import System

from pyrevit.labs import PyRevit

import agent_harness as harness
from agent_harness import TestCase

CONFIGS = PyRevit.PyRevitConfigs


def _store_raw(key, value):
    CONFIGS.GetConfigFile().SetSectionKeyValue[System.String]("agent", key, value)


class SettingsTests(TestCase):
    """Reading and writing [agent] policy, engine and enabled."""

    def setUp(self):
        """Remember the current settings."""
        self.policy = CONFIGS.GetAgentPolicy()
        self.engine = CONFIGS.GetAgentEngine()
        self.enabled = CONFIGS.GetAgentEnabled()

    def tearDown(self):
        """Put the remembered settings back."""
        CONFIGS.SetAgentPolicy(self.policy)
        CONFIGS.SetAgentEngine(self.engine)
        CONFIGS.SetAgentEnabled(self.enabled)

    def test_every_valid_policy_and_engine_round_trips(self):
        """A policy or engine that is set is the one read back."""
        for policy in ("readonly", "ask", "auto"):
            CONFIGS.SetAgentPolicy(policy)
            self.assertEqual(policy, CONFIGS.GetAgentPolicy())
        for engine in ("ironpython", "cpython"):
            CONFIGS.SetAgentEngine(engine)
            self.assertEqual(engine, CONFIGS.GetAgentEngine())

    def test_the_enabled_flag_round_trips(self):
        """The host flag reads back what was written."""
        CONFIGS.SetAgentEnabled(not self.enabled)
        self.assertEqual(not self.enabled, CONFIGS.GetAgentEnabled())
        CONFIGS.SetAgentEnabled(self.enabled)
        self.assertEqual(self.enabled, CONFIGS.GetAgentEnabled())

    def test_invalid_values_are_rejected_and_change_nothing(self):
        """A policy or engine that doesn't exist raises and leaves the setting alone."""
        with self.assertRaises(Exception):
            CONFIGS.SetAgentPolicy("bogus")
        with self.assertRaises(Exception):
            CONFIGS.SetAgentEngine("lua")
        self.assertEqual(self.policy, CONFIGS.GetAgentPolicy())
        self.assertEqual(self.engine, CONFIGS.GetAgentEngine())

    def test_an_unknown_stored_policy_reads_as_ask_never_looser(self):
        """A typo in the config file can't loosen the policy."""
        _store_raw("policy", "bogus")
        self.assertEqual("ask", CONFIGS.GetAgentPolicy())
        _store_raw("policy", "")
        self.assertEqual("ask", CONFIGS.GetAgentPolicy())

    def test_stored_policies_and_engines_ignore_case(self):
        """AUTO, ReadOnly and CPYTHON are read as the lowercase values."""
        _store_raw("policy", "AUTO")
        self.assertEqual("auto", CONFIGS.GetAgentPolicy())
        _store_raw("policy", "ReadOnly")
        self.assertEqual("readonly", CONFIGS.GetAgentPolicy())
        _store_raw("engine", "CPYTHON")
        self.assertEqual("cpython", CONFIGS.GetAgentEngine())

    def test_an_unknown_stored_engine_reads_as_ironpython(self):
        """An engine name that isn't known falls back to IronPython."""
        _store_raw("engine", "lua")
        self.assertEqual("ironpython", CONFIGS.GetAgentEngine())

    def test_the_cli_prints_the_stored_values(self):
        """The commands pyrevit configs agent policy and engine print what is stored."""
        if not op.exists(harness.CLI):
            self.skipTest("bin/pyrevit.exe is not built.")
        CONFIGS.SetAgentPolicy("readonly")
        CONFIGS.SetAgentEngine("cpython")
        self.assertIn("readonly", harness.run_cli("configs", "agent", "policy"))
        self.assertIn("cpython", harness.run_cli("configs", "agent", "engine"))
