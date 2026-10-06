"""The agent panel as Revit hosts it.

The pane is registered when Revit starts, shown by the ribbon button, and
closing it ends the session; its log lists every run once, matching the run
records. The panel's view models are covered by unit tests; these tests check
what only Revit can show.
"""

import json
import os.path as op

from System import Array, Object
from System.Reflection import BindingFlags

from pyrevit import HOST_APP, UI
from pyrevit.coreutils import assmutils
from pyrevit.runtime import RUNTIME_ASSM

import agent_harness as harness
from agent_harness import TestCase

PANEL = assmutils.find_type_by_name(
    RUNTIME_ASSM, "PyRevitLabs.PyRevit.Runtime.Agent.AgentPanel"
)
HOST = assmutils.find_type_by_name(
    RUNTIME_ASSM, "PyRevitLabs.PyRevit.Runtime.Agent.AgentHost"
)


def _member(instance, name):
    return instance.GetType().GetProperty(name).GetValue(instance)


def _logged_runs():
    """Run entries of the agent log, by run id, read through reflection."""
    activity = HOST.GetField("Activity", BindingFlags.NonPublic | BindingFlags.Static)
    runs = {}
    for entry in _member(activity.GetValue(None), "History"):
        details = _member(entry, "Details")
        if details is None:
            continue
        summary = json.loads(str(details))
        runs.setdefault(summary["run_id"], []).append((entry, summary))
    return runs


def _pane_id():
    return UI.DockablePaneId(PANEL.GetField("PaneGuid").GetValue(None))


def _pane():
    return HOST_APP.uiapp.GetDockablePane(_pane_id())


def _show():
    PANEL.GetMethod("Show").Invoke(None, Array[Object]([HOST_APP.uiapp]))


class PanelTests(TestCase):
    """The pane Revit hosts for the agent panel."""

    def tearDown(self):
        """Put back the session every test starts from."""
        harness.restore_session()

    def test_the_panel_resources_are_embedded_in_the_runtime(self):
        """The view and its English strings ship inside the runtime assembly."""
        names = set(str(name) for name in RUNTIME_ASSM.GetManifestResourceNames())
        for resource in ("AgentPanel.View.xaml", "AgentPanel.Strings_en_us.xaml"):
            self.assertIn("PyRevitLabs.PyRevit.Runtime.Agent." + resource, names)

    def test_the_pane_is_registered_when_revit_starts(self):
        """The host registers the pane on its first load, enabled or not."""
        self.assertTrue(UI.DockablePane.PaneIsRegistered(_pane_id()))

    def test_the_ribbon_button_call_shows_the_pane(self):
        """AgentPanel.Show, which the ribbon button calls, shows the pane."""
        self.assertTrue(UI.DockablePane.PaneIsRegistered(_pane_id()))
        _show()
        self.assertTrue(_pane().IsShown())

    def test_the_log_matches_the_run_records_one_for_one(self):
        """Each run appears once in the log, with its title, session and record folder."""
        session_id = harness.session_status()["id"]
        responses = [
            harness.run("result = 1", title="Log check: query", reason="Testing"),
            harness.run("x = 1 / 0", title="Log check: failing query"),
        ]

        runs = _logged_runs()
        for response in responses:
            matches = runs.get(response["run_id"], [])
            self.assertEqual(1, len(matches), response["run_id"])
            entry, summary = matches[0]
            self.assertEqual(response["title"], _member(entry, "Title"))
            self.assertEqual(session_id, _member(entry, "SessionId"))
            self.assertEqual(response["run_dir"], summary["run_dir"])
            with open(op.join(summary["run_dir"], "response.json")) as handle:
                record = json.load(handle)
            self.assertEqual(session_id, record["session_id"])
            self.assertEqual(response["document"], record["document"])
        self.assertEqual(
            "Testing", _member(runs[responses[0]["run_id"]][0][0], "Reason")
        )
        self.assertEqual(
            "ZeroDivisionError", runs[responses[1]["run_id"]][0][1]["error"]["type"]
        )

    def test_closing_the_pane_ends_the_session(self):
        """Hiding the pane ends the session, and the host says why."""
        self.assertTrue(UI.DockablePane.PaneIsRegistered(_pane_id()))
        _show()
        _pane().Hide()
        status = harness.session_status()
        self.assertEqual("inactive", status["state"])
        self.assertEqual("panel_closed", status["last_ended"]["reason"])
