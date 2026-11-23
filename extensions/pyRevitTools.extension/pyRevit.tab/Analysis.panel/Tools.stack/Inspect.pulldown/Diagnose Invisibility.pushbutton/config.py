# -*- coding: utf-8 -*-
"""Shift-click: reveal what is hidden in the active view, colored by reason."""

from pyrevit import forms, revit, script

from invisibility_checks import t
from invisibility_report import show_report, supports_interactive_report
from invisibility_reveal import SUPPORTED_VIEW_TYPES

output = script.get_output()


def main():
    """Open the report in reveal-only mode on the active view."""
    view = revit.active_view
    if not supports_interactive_report(output):
        forms.alert(
            t(
                "reveal_needs_webview2",
                "Reveal hidden needs the WebView2 output window and IronPython.",
            )
        )
        return
    if view is None or view.ViewType not in SUPPORTED_VIEW_TYPES:
        forms.alert(
            t(
                "reveal_unsupported_active",
                "Open a plan, section, elevation or 3D view first.",
            )
        )
        return
    show_report(output, [], [view], reveal=True)


if __name__ == "__main__":
    main()
