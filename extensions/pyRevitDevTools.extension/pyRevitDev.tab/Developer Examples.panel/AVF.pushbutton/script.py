# -*- coding: utf-8 -*-
"""Developer example: pick an element, display a number on it via AVF.

Minimal end-to-end smoke test for pyrevit.revit.avf. Each run adds a value to
one element, or updates it. Orthographic 3D views without a section box also
offer a colored surface instead of a text marker.

Shift-click:
Remove all numbers of this button from the active view.
"""

import math

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit.revit import avf
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

RESULT_NAME = "pyRevitAVF_Demo"
STYLES = {"Text Marker": "marker", "Colored Surface": "colored"}


def parse_number(text):
    """Return *text* as a float, accepting a decimal comma, or None."""
    text = text.strip()
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def ask_style(view):
    if not isinstance(view, DB.View3D) or view.IsPerspective or view.IsSectionBoxActive:
        return "marker"
    choice = forms.CommandSwitchWindow.show(
        list(STYLES), message="Pick an AVF display style:"
    )
    return STYLES.get(choice)


def main():
    view = revit.active_view
    if not view.AllowsAnalysisDisplay():
        forms.alert("The active view cannot display analysis results.", exitscript=True)

    with forms.WarningBar(title="Select an element to label"):
        element = revit.pick_element()
    if not element:
        return

    text = forms.ask_for_string(
        default="42",
        prompt="Value to display on the selected element:",
        title="AVF Demo",
    )
    if text is None:
        return
    value = parse_number(text)
    if value is None:
        forms.alert("'{}' is not a number.".format(text), exitscript=True)

    style = ask_style(view)
    if style is None:
        return

    report = avf.show_values(
        view, {element: value}, name=RESULT_NAME, style=style, keep_others=True
    )
    if report["failed"]:
        forms.alert(
            "Could not display the value: {}".format(
                "; ".join(report["failed"].values())
            ),
            exitscript=True,
        )
    element_id = get_elementid_value(element.Id)
    if style == "colored" and element_id not in report["on_faces"]:
        forms.alert(
            "Revit accepted no face of this element, so its surface stays "
            "unpainted. Run again and pick Text Marker.",
            exitscript=True,
        )
    forms.alert(
        "Displayed value {} on element ID {}.\n"
        "Elements with a value in this view: {}.\n\n"
        "Run again to add one, or pick the same element to change it. "
        "Shift-click removes them all.".format(
            value, element_id, len(report["present"])
        )
    )


if __name__ == "__main__":
    main()
