# -*- coding: utf-8 -*-
"""Get a total count and types of In Place Family in the current document.
Also isolate them in a new 3Dview called InPlace Families.

Copyright (c) 2021 Jean-Marc Couffin
https://github.com/jmcouffin
"""

from pyrevit import forms, script
from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_html
from pyrevit.framework import List

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
ISOLATION_VIEW_NAME = "InPlace Families"


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def escape_for_table(text):
    return escape_for_html(text).replace("|", "&#124;")


def collect_inplace_instances():
    instances = (
        DB.FilteredElementCollector(revit.doc)
        .OfClass(DB.FamilyInstance)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return [
        instance
        for instance in instances
        if instance.Symbol
        and instance.Symbol.Family
        and instance.Symbol.Family.IsInPlace
    ]


def report(instances):
    output.print_md("### {}".format(_t("found_count").format(len(instances))))
    output.print_table(
        table_data=[
            [
                output.linkify(instance.Id),
                escape_for_table(instance.Symbol.Family.FamilyCategory.Name),
                escape_for_table(instance.Symbol.Family.Name),
            ]
            for instance in instances
        ],
        columns=[_t("column_element"), _t("column_category"), _t("column_family")],
    )


def isolate_in_new_view(instances):
    element_ids = List[DB.ElementId](instance.Id for instance in instances)
    with revit.TransactionGroup(_t("transaction_name")):
        with revit.Transaction(_t("transaction_reset_isolation")):
            isolation_view = revit.db.create.create_3d_view(ISOLATION_VIEW_NAME)
            isolation_view.DisableTemporaryViewMode(
                DB.TemporaryViewMode.TemporaryHideIsolate
            )
        with revit.Transaction(_t("transaction_isolate")):
            isolation_view.IsolateElementsTemporary(element_ids)
    return isolation_view


output.close_others(all_open_outputs=True)
instances = collect_inplace_instances()
if not instances:
    forms.alert(_t("no_inplace_families"), exitscript=True)

report(instances)
HOST_APP.uidoc.RequestViewChange(isolate_in_new_view(instances))
