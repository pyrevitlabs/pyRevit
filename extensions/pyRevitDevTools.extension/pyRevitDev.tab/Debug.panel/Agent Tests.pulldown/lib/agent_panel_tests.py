"""The agent panel as Revit hosts it.

The pane is registered when Revit starts, shown by the ribbon button, and
closing it ends the session. The panel's view model is covered by unit tests;
these tests check what only Revit can show.
"""

from System import Array, Object

from pyrevit import HOST_APP, UI
from pyrevit.coreutils import assmutils
from pyrevit.runtime import RUNTIME_ASSM

import agent_harness as harness
from agent_harness import TestCase

PANEL = assmutils.find_type_by_name(
    RUNTIME_ASSM, "PyRevitLabs.PyRevit.Runtime.Agent.AgentPanel"
)


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

    def test_closing_the_pane_ends_the_session(self):
        """Hiding the pane ends the session, and the host says why."""
        self.assertTrue(UI.DockablePane.PaneIsRegistered(_pane_id()))
        _show()
        _pane().Hide()
        status = harness.session_status()
        self.assertEqual("inactive", status["state"])
        self.assertEqual("panel_closed", status["last_ended"]["reason"])
