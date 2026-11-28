# -*- coding: utf-8 -*-
"""Edit the parameters of a schedule's elements in an Excel-like grid.

A plain click opens the grid for a schedule (the active schedule view, or one
picked from a list). Shift-click starts from scratch: the page lets you choose
categories and parameter columns without any schedule. Edits are staged in the
page and written to the model, as one undo step, when you push them.
"""

from pyrevit import EXEC_PARAMS, forms, revit, script

from attribute_columns import id_value
from attribute_session import AttributeSession, supports_interactive_page
from attribute_strings import t

logger = script.get_logger()
output = script.get_output()

SESSION_KEY = "PYREVIT_ATTRIBUTE_EDITOR_SESSION"


def _start_source(doc):
    if EXEC_PARAMS.config_mode:
        return {"kind": "scratch"}
    active_view = revit.active_view
    if active_view is not None and revit.query.is_schedule(active_view):
        return {"kind": "schedule", "id": id_value(active_view.Id)}
    schedule = forms.select_schedules(
        title=t("ui_pick_schedule_title"),
        button_name=t("ui_pick_schedule_button"),
        multiple=False,
        doc=doc,
    )
    if not schedule:
        script.exit()
    return {"kind": "schedule", "id": id_value(schedule.Id)}


def _replace_previous_session():
    previous = script.get_envvar(SESSION_KEY)
    if previous is None:
        return
    if previous.has_unsent_edits() and not forms.alert(
        t("ui_replace_session").format(previous.pending_edits),
        yes=True,
        no=True,
    ):
        script.exit()
    previous.dispose()


def main():
    """Open the grid page, replacing the one of an earlier run."""
    if not supports_interactive_page(output):
        forms.alert(t("ui_needs_webview2"))
        return
    doc = revit.doc
    start_source = _start_source(doc)
    _replace_previous_session()
    session = AttributeSession(output, doc, start_source)
    if session.show():
        script.set_envvar(SESSION_KEY, session)
    else:
        forms.alert(t("ui_needs_webview2"))


if __name__ == "__main__":
    main()
