# -*- coding: utf-8 -*-
"""Purge line styles, line patterns, fill patterns and shared parameters that nothing uses."""

from collections import OrderedDict

from pyrevit import forms, script
from pyrevit import revit
from pyrevit.coreutils import escape_for_html

import purge_probe


logger = script.get_logger()
output = script.get_output()

ALL_GROUP = "All"


class _KindOption(forms.TemplateListItem):
    def __init__(self, kind, candidates):
        super(_KindOption, self).__init__(kind, checked=True)
        self.count = len(candidates)

    @property
    def name(self):
        return "{} ({})".format(self.item, self.count)


class _CandidateOption(forms.TemplateListItem):
    def __init__(self, candidate):
        super(_CandidateOption, self).__init__(candidate, checked=True)

    @property
    def name(self):
        if self.item.detail:
            return "{} - {}".format(self.item.name, self.item.detail)
        return self.item.name


def _pick_kinds(candidates_by_kind):
    options = [_KindOption(kind, items) for kind, items in candidates_by_kind if items]
    picked = forms.SelectFromList.show(
        options,
        title="Deep Purge",
        width=420,
        height=360,
        button_name="Check for Unused",
        multiselect=True,
    )
    return picked or []


def _check_for_unused(doc, candidates):
    with forms.ProgressBar(
        title="Checking {value} of {max_value}", cancellable=True
    ) as progress_bar:
        unused = purge_probe.find_unused(doc, candidates, progress_bar=progress_bar)
        return unused, progress_bar.cancelled


def _pick_unused(unused):
    options = [_CandidateOption(x) for x in unused]
    groups = OrderedDict([(ALL_GROUP, options)])
    for option in options:
        groups.setdefault(option.item.kind, []).append(option)
    picked = forms.SelectFromList.show(
        groups,
        title="Deep Purge: {} unused".format(len(unused)),
        width=560,
        button_name="Purge Selected",
        multiselect=True,
        group_selector_title="Type",
        default_group=ALL_GROUP,
        sort_groups="unsorted",
    )
    return picked or []


def _table_cell(text):
    return escape_for_html(text).replace("|", "\\|")


def _report(purged, failed):
    output.print_md("## Deep Purge")
    if purged:
        output.print_table(
            [[x.kind, _table_cell(x.name), _table_cell(x.detail)] for x in purged],
            columns=["Type", "Name", "Detail"],
            title="Purged {}".format(_count(len(purged), "item")),
        )
    if failed:
        output.print_table(
            [[x.kind, _table_cell(x.name), _table_cell(error)] for x, error in failed],
            columns=["Type", "Name", "Error"],
            title="Could not purge {}".format(_count(len(failed), "item")),
        )
    for candidate, error in failed:
        logger.warning(
            "Could not purge %s %s: %s", candidate.kind, candidate.name, error
        )


def _count(number, noun):
    return "{} {}{}".format(number, noun, "" if number == 1 else "s")


def _flatten(candidates_by_kind):
    return [candidate for _, items in candidates_by_kind for candidate in items]


def _offer_another_pass(purged_count):
    return forms.alert(
        "Purged {}.".format(_count(purged_count, "item")),
        sub_msg="Removing line styles can leave line patterns unused. Check again?",
        yes=True,
        no=True,
    )


def _cancelled_message(total_purged):
    if not total_purged:
        return "Nothing was purged."
    return "The {} purged earlier stay purged.".format(_count(total_purged, "item"))


def main():
    """Check, pick and purge, repeating while the user wants another pass.

    A purge can leave other items unused (a line pattern only a deleted line
    style used), so each pass collects and checks the candidates again.
    """
    doc = revit.doc
    candidates_by_kind = purge_probe.collect_candidates(doc)
    if not _flatten(candidates_by_kind):
        forms.alert(
            "Nothing to check.",
            sub_msg="This model has no user-defined line styles, patterns "
            "or unbound shared parameters.",
            exitscript=True,
        )

    kinds = _pick_kinds(candidates_by_kind)
    if not kinds:
        script.exit()

    candidates = _flatten(x for x in candidates_by_kind if x[0] in kinds)
    total_purged = 0
    while True:
        unused, cancelled = _check_for_unused(doc, candidates)
        if cancelled:
            forms.alert(
                "Check cancelled.",
                sub_msg=_cancelled_message(total_purged),
                exitscript=True,
            )
        if not unused:
            forms.alert(
                "Nothing to purge.",
                sub_msg="All {} checked are in use.".format(
                    _count(len(candidates), "item")
                ),
                exitscript=True,
            )

        picked = _pick_unused(unused)
        if not picked:
            script.exit()

        purged, failed = purge_probe.purge(doc, picked)
        _report(purged, failed)
        total_purged += len(purged)
        if not purged or not _offer_another_pass(len(purged)):
            break
        candidates = _flatten(purge_probe.collect_candidates(doc, kinds=kinds))


main()
