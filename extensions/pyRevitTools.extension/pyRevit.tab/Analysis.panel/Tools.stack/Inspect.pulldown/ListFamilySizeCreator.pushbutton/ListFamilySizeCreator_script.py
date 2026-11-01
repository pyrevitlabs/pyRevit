# -*- coding: utf-8 -*-
"""List all families and their sizes."""

import math
import os
import tempfile
from collections import defaultdict

from pyrevit import forms, script
from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit.compat import safe_strtype
from pyrevit.coreutils import applocales, escape_for_output

logger = script.get_logger()
output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
FIELDS = ["Size", "Name", "Category", "Creator", "Count"]
NUMERIC_FIELDS = ["Size", "Count"]
GROUPING_FIELDS = ["Creator", "Category"]
SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
TEMP_DIR = os.path.join(tempfile.gettempdir(), "pyRevit_ListFamilySizes")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def field_label(field):
    return _t("field_{}".format(field.lower()))


def convert_size(size_bytes):
    if not size_bytes:
        return _t("not_available")
    unit_index = int(math.floor(math.log(size_bytes, 1024)))
    size = round(size_bytes / math.pow(1024, unit_index), 2)
    return "{}{}".format(size, SIZE_UNITS[unit_index])


def count_instances_per_family():
    instance_counts = defaultdict(int)
    instances = DB.FilteredElementCollector(revit.doc).OfClass(DB.FamilyInstance)
    for instance in instances:
        symbol = getattr(instance, "Symbol", None)
        if symbol:
            instance_counts[symbol.Family.Name] += 1
    return instance_counts


def measure_family(family, opened_titles, instance_counts):
    """Open the family for editing and return its file size and metadata.

    A family that is not saved anywhere yet is saved to a temporary file to learn
    its size, and closed and deleted again unless the user had it open already.

    Returns:
        dict: The row for the family, or None when it cannot be opened for editing.
    """
    try:
        family_doc = revit.doc.EditFamily(family)
    except Exception as ex:
        logger.warning(
            "Skipping family '%s': could not open for edit: %s", family.Name, ex
        )
        return None
    was_open = family_doc.Title in opened_titles
    family_path = family_doc.PathName
    try:
        if not was_open and (not family_path or not os.path.exists(family_path)):
            family_path = os.path.join(TEMP_DIR, family_doc.Title)
            save_options = DB.SaveAsOptions()
            save_options.OverwriteExistingFile = True
            family_doc.SaveAs(family_path, save_options)
        has_file = bool(family_path) and os.path.exists(family_path)
        return {
            "Size": os.path.getsize(family_path) if has_file else 0,
            "Creator": DB.WorksharingUtils.GetWorksharingTooltipInfo(
                revit.doc, family.Id
            ).Creator,
            "Category": (
                family.FamilyCategory.Name
                if family.FamilyCategory
                else _t("not_available")
            ),
            "Name": family.Name,
            "Count": instance_counts.get(family.Name, 0),
        }
    finally:
        if not was_open:
            family_doc.Close(False)
            is_temporary = family_path and family_path.lower().startswith(
                TEMP_DIR.lower()
            )
            if is_temporary and os.path.exists(family_path):
                os.remove(family_path)


def collect_family_items():
    if not os.path.exists(TEMP_DIR):
        os.mkdir(TEMP_DIR)
    families = list(DB.FilteredElementCollector(revit.doc).OfClass(DB.Family))
    opened_titles = [
        document.Title
        for document in HOST_APP.uiapp.Application.Documents
        if document.IsFamilyDocument
    ]
    instance_counts = count_instances_per_family()
    items = []
    with forms.ProgressBar(title=_t("progress_title"), cancellable=True) as progress:
        for index, family in enumerate(families):
            with revit.ErrorSwallower():
                if family.IsEditable:
                    item = measure_family(family, opened_titles, instance_counts)
                    if item:
                        items.append(item)
            if progress.cancelled:
                break
            progress.update_progress(index, len(families))
    return items


def sort_items(items, field):
    if field in NUMERIC_FIELDS:
        return sorted(items, key=lambda item: item.get(field) or 0, reverse=True)
    return sorted(items, key=lambda item: item.get(field) or "")


def format_cell(item, field):
    value = item.get(field)
    if value is None or value == "":
        return _t("not_available")
    if field == "Size":
        return convert_size(value)
    return escape_for_output(safe_strtype(value))


def print_totals(items):
    total_size = sum(item.get("Size") or 0 for item in items)
    output.print_md(
        "**{}**".format(
            _t("families_total").format(len(items), convert_size(total_size))
        )
    )


def group_items(items, group_by, sort_by):
    groups = defaultdict(list)
    for item in sort_items(items, sort_by):
        groups[item[group_by]].append(item)
    return groups


def print_sorted(items, group_by):
    other_fields = [field for field in FIELDS if field != group_by]
    columns = [group_by] + other_fields
    if group_by in GROUPING_FIELDS:
        sort_by = other_fields[0]
        output.print_md("## {}".format(_t("group_by").format(field_label(group_by))))
        output.print_md("## {}".format(_t("sort_by").format(field_label(sort_by))))
        groups = group_items(items, group_by, sort_by)
    else:
        output.print_md("**{}**".format(_t("sort_by").format(field_label(group_by))))
        groups = {"": sort_items(items, group_by)}

    for group_value in sorted(groups):
        if group_by in GROUPING_FIELDS:
            output.print_md("---")
            output.print_md(
                "## {}: {}".format(
                    field_label(group_by),
                    escape_for_output(group_value or _t("not_available")),
                )
            )
        output.print_table(
            table_data=[
                [format_cell(item, field) for field in columns]
                for item in groups[group_value]
            ],
            columns=[field_label(field) for field in columns],
        )
        print_totals(groups[group_value])


def main():
    selected_label = forms.CommandSwitchWindow.show(
        [field_label(field) for field in FIELDS], message=_t("sort_options")
    )
    if not selected_label:
        script.exit()
    sort_field = next(field for field in FIELDS if field_label(field) == selected_label)
    print_sorted(collect_family_items(), sort_field)


if __name__ == "__main__":
    main()
