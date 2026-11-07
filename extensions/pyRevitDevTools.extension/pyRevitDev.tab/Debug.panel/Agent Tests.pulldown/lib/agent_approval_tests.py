"""The ``ask`` policy's approval prompt, answered by pressing its button.

The prompt is a native Windows message box, which Revit's dialog event can't
answer, so a helper thread finds the box and presses the button. If it can't
find the box, the prompt stays on screen; press the button named in the run's
title to let the test finish.
"""

from contextlib import contextmanager

from pyrevit import HOST_APP

import agent_harness as harness
from agent_harness import TestCase

APPROVAL_PROMPT = "pyRevit Agent"
TASKDIALOG_KEEP = 1001


@contextmanager
def _approve_every_dialog():
    def handler(sender, args):
        args.OverrideResult(TASKDIALOG_KEEP)

    HOST_APP.uiapp.DialogBoxShowing += handler
    try:
        yield
    finally:
        HOST_APP.uiapp.DialogBoxShowing -= handler


def _wall():
    return harness.session().wall_ids[0]


class ApprovalTests(TestCase):
    """Keep and Discard on the approval prompt."""

    def test_keep_commits_the_change(self):
        """Keep on the approval prompt commits the change."""
        keep = harness.answer_prompts(APPROVAL_PROMPT, harness.YES)
        with harness.policy("ask"), keep as pressed:
            response = harness.run(
                harness.set_comment_script(),
                mode="modify",
                title="Agent test: click YES",
                inputs={"id": _wall(), "text": "agent-kept"},
            )
        self.assertEqual("committed", response["decision"], pressed)
        self.assertEqual("agent-kept", harness.comment(_wall()))

    def test_discard_rolls_the_change_back(self):
        """Discard on the approval prompt rolls the change back."""
        before = harness.comment(_wall())
        discard = harness.answer_prompts(APPROVAL_PROMPT, harness.NO)
        with harness.policy("ask"), discard as pressed:
            response = harness.run(
                harness.set_comment_script(),
                mode="modify",
                title="Agent test: click NO",
                inputs={"id": _wall(), "text": "agent-discarded"},
            )
        self.assertEqual("rejected", response["status"], pressed)
        self.assertEqual(before, harness.comment(_wall()))

    def test_a_dialog_handler_cannot_answer_the_prompt(self):
        """A DialogBoxShowing handler answering Keep doesn't reach the prompt."""
        before = harness.comment(_wall())
        discard = harness.answer_prompts(APPROVAL_PROMPT, harness.NO)
        with harness.policy("ask"), _approve_every_dialog(), discard:
            response = harness.run(
                harness.set_comment_script(),
                mode="modify",
                title="Agent test: click NO",
                inputs={"id": _wall(), "text": "agent-self-approved"},
            )
        self.assertEqual("rejected", response["status"])
        self.assertEqual(before, harness.comment(_wall()))
