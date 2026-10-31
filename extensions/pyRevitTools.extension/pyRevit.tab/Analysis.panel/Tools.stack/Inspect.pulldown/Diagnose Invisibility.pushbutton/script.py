# -*- coding: utf-8 -*-
"""Diagnose why the selected/picked element(s) are not visible in chosen views.

With the WebView2 output renderer on IronPython the result is an interactive
report with one-click fixes and a 3D preview (``invisibility_report``).
Otherwise a plain per-element report is printed. The checks themselves live
in ``invisibility_checks``.
"""

from pyrevit import forms, revit, script
from pyrevit.compat import IRONPY, get_elementid_value_func

from invisibility_checks import collect_visible_ids, diagnose_invisibility, t
from invisibility_report import format_element_label, show_report

logger = script.get_logger()
output = script.get_output()

get_elementid_value = get_elementid_value_func()

_WEBVIEW2_ENGINE = "WebView2/Chromium"


def _get_target_elements():
    """Current selection if non-empty, otherwise prompt to pick element(s).

    Returns [] if nothing is selected and the pick is cancelled.
    """
    selection = revit.get_selection()
    if selection and len(selection) > 0:
        return list(selection.elements)
    return revit.pick_elements(
        message=t("pick_prompt", "Select element(s) to diagnose")
    )


def _supports_interactive_report():
    try:
        return IRONPY and output.renderer_engine == _WEBVIEW2_ENGINE
    except Exception:
        return False


def _print_plain_report(elements, views):
    output.print_md("## {}".format(t("report_title", "Visibility Diagnosis")))
    visible_count = 0
    hidden_count = 0
    for view in views:
        visible_ids = collect_visible_ids(view)
        output.print_md(output.linkify(view.Id, title=view.Name))
        for element in elements:
            try:
                link = output.linkify(element.Id, title=format_element_label(element))
                reasons, _ = diagnose_invisibility(element, view, visible_ids)
                if not reasons:
                    visible_count += 1
                    output.print_md(
                        "**{}** {}".format(
                            link, t("status_visible", "Visible in this view.")
                        )
                    )
                    continue
                hidden_count += 1
                output.print_md(
                    "**{}** {}".format(
                        link, t("status_hidden", "NOT visible in this view:")
                    )
                )
                for reason in reasons:
                    output.print_md("- {}".format(reason))
            except Exception as ex:
                logger.exception(
                    "Error diagnosing element {}".format(
                        get_elementid_value(element.Id)
                    )
                )
                output.print_md(
                    "- {} `{}`: {}".format(
                        t("status_error", "Error diagnosing element"),
                        get_elementid_value(element.Id),
                        ex,
                    )
                )
        output.insert_divider()
    output.print_md(
        t("summary_line", "{} visible, {} not visible.").format(
            visible_count, hidden_count
        )
    )


def main():
    """Collect targets and views, then show the interactive or plain report."""
    elements = _get_target_elements()
    if not elements:
        forms.alert(t("no_elements_error", "No elements selected or picked."))
        return

    views = forms.select_views(
        title=t("select_view_title", "Select View"),
        button_name=t("select_view_button", "Diagnose in this View"),
    )
    if not views:
        forms.alert(t("no_view_error", "No view selected."))
        return

    if _supports_interactive_report():
        show_report(output, elements, views)
    else:
        _print_plain_report(elements, views)


if __name__ == "__main__":
    main()
