# -*- coding: utf-8 -*-
"""Hosted tests for the ribbon ids the loader registers for pyRevit's own panels.

Run from Revit via the DevTools "Ribbon Control Id Tests" button (zero-doc
context). The module is Integration level, so "Run All Tests" skips it. They
assert that the control id of every command in the pyRevit tab resolves to the
ribbon item Revit registered, whatever the pyRevit ``user_locale``: panels are
created under their folder name and only display the localized title (#4035).
"""

import unittest

TEST_ENVIRONMENT = "Revit"
TEST_LEVEL = "Integration"

PYREVIT_TAB_PREFIX = "CustomCtrl_%CustomCtrl_%pyRevit%"


def _pyrevit_tab_commands():
    from pyrevit.loader import sessionmgr

    return [
        command
        for command in sessionmgr.find_all_commands(cache=False)
        if command.control_id and command.control_id.startswith(PYREVIT_TAB_PREFIX)
    ]


def _ribbon_item_ids():
    from pyrevit.api import AdWindows

    item_ids = set()

    def collect(item):
        item_id = getattr(item, "Id", None)
        if item_id:
            item_ids.add(item_id)
        for child in list(getattr(item, "Items", None) or []):
            collect(child)

    for tab in AdWindows.ComponentManager.Ribbon.Tabs:
        for panel in tab.Panels:
            for item in list(panel.Source.Items):
                collect(item)
    return item_ids


class ControlIdTests(unittest.TestCase):
    """Command control ids equal the ids of the ribbon items Revit registered."""

    def test_pyrevit_tab_commands_are_loaded(self):
        """The pyRevit tab contributes commands, so the checks below are not vacuous."""
        self.assertTrue(_pyrevit_tab_commands())

    def test_control_id_matches_a_ribbon_item(self):
        """Every pyRevit tab command's control id is the id of a ribbon item."""
        ribbon_item_ids = _ribbon_item_ids()
        missing = sorted(
            command.control_id
            for command in _pyrevit_tab_commands()
            if command.control_id not in ribbon_item_ids
        )
        self.assertEqual([], missing[:10], "{} unmatched".format(len(missing)))

    def test_control_id_resolves_to_a_command_id(self):
        """Every pyRevit tab command's control id resolves through LookupCommandId."""
        from pyrevit.api import UI

        missing = sorted(
            command.control_id
            for command in _pyrevit_tab_commands()
            if UI.RevitCommandId.LookupCommandId(command.control_id) is None
        )
        self.assertEqual([], missing[:10], "{} unresolved".format(len(missing)))


if __name__ == "__main__":
    unittest.main()
