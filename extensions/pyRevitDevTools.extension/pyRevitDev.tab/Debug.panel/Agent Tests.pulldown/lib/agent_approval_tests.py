"""The ``ask`` policy's approval prompt, answered through Revit's dialog event.

If Revit doesn't raise ``DialogBoxShowing`` for the prompt, it stays on screen;
click the button named in its title to let the test finish.
"""

from contextlib import contextmanager
from unittest import TestCase

from pyrevit import HOST_APP, UI

import agent_harness as harness

KEEP = 1001
DISCARD = 1002


@contextmanager
def _answer_prompt(result):
    answered = []

    def handler(sender, args):
        if (
            isinstance(args, UI.Events.TaskDialogShowingEventArgs)
            and "agent" in (args.Message or "").lower()
        ):
            args.OverrideResult(result)
            answered.append(args.Message)

    HOST_APP.uiapp.DialogBoxShowing += handler
    try:
        yield answered
    finally:
        HOST_APP.uiapp.DialogBoxShowing -= handler


def _wall():
    return harness.session().wall_ids[0]


class ApprovalTests(TestCase):
    """Keep and Discard on the approval prompt."""

    def test_keep_commits_the_change(self):
        """Keep on the approval prompt commits the change."""
        with harness.policy("ask"), _answer_prompt(KEEP) as answered:
            response = harness.run(
                harness.set_comment_script(),
                mode="modify",
                title="Agent test: click KEEP",
                inputs={"id": _wall(), "text": "agent-kept"},
            )
        self.assertEqual("committed", response["decision"], answered)
        self.assertEqual("agent-kept", harness.comment(_wall()))

    def test_discard_rolls_the_change_back(self):
        """Discard on the approval prompt rolls the change back."""
        before = harness.comment(_wall())
        with harness.policy("ask"), _answer_prompt(DISCARD) as answered:
            response = harness.run(
                harness.set_comment_script(),
                mode="modify",
                title="Agent test: click DISCARD",
                inputs={"id": _wall(), "text": "agent-discarded"},
            )
        self.assertEqual("rejected", response["status"], answered)
        self.assertEqual(before, harness.comment(_wall()))
