# -*- coding: utf-8 -*-
"""List all families and their sizes."""
import os.path as op
import math
from pyrevit import revit, forms, script, DB

__title__ = 'Lists Family Sizes'
__authors__ = ['Frederic Beaupere', 'Alex Melnikov']
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'

FIELDS = ["Size", "Name", "Category", "Creator"]

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_unit = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    size = round(size_bytes / p, 2)
    return "{}{}".format(size, size_unit[i])


def print_totals(families):
    total_size = sum([fam_item.get("Size") or 0 for fam_item in families])
    print("%d families, found total size: %s\n\n" % (
        len(families), convert_size(total_size)))


def print_sorted(families, sort_by):
    # sort list of fields
    fields_rest = list(FIELDS)
    fields_rest.pop(FIELDS.index(sort_by))
    fields_sorted = [sort_by] + fields_rest

    if sort_by not in ["Creator", "Category"]: # do not group by name and size
        print("; ".join(fields_sorted))
        families_grouped = {"": sorted(families, key=\
            lambda fam_item: fam_item.get(sort_by))}

    else:
        print(";".join(fields_rest))
        # convert to grouped dict
        families_grouped = {}
        for fam_item in sorted(families, key=\
                lambda fam_item: fam_item.get(fields_rest[0])):
            sort_by_value = fam_item[sort_by]
            fam_item_reduced = dict(fam_item)
            fam_item_reduced.pop(sort_by)
            if sort_by_value not in families_grouped:
                families_grouped[sort_by_value] = []
            families_grouped[sort_by_value].append(fam_item_reduced)

    for group_value in sorted(families_grouped.keys()):
        print(50 * "-")
        print("%s: %s" % (sort_by, group_value))
        for fam_item in families_grouped[group_value]:
            family_row = []

            for field in fields_sorted:
                value = fam_item.get(field)
                if value is None:
                    continue
                if field == "Size":
                    value = convert_size(value) if value > 0 else "N/A"
                family_row.append(value)
            print("; ".join(family_row))
        print_totals(families_grouped[group_value])

# main logic
# ask use to choose sort option
sort_by = forms.CommandSwitchWindow.show(FIELDS,
     message='Sorting options:',
)
if not sort_by:
    script.exit()

all_fams = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.Family)\
             .ToElements()

all_family_items = []
with forms.ProgressBar(title=__title__, cancellable=True) as pb:
    i = 0
    for fam in all_fams:
        with revit.ErrorSwallower() as swallower:
            if fam.IsEditable:
                fam_doc = revit.doc.EditFamily(fam)
                fam_path = fam_doc.PathName
                fam_size = 0
                fam_category = fam.FamilyCategory.Name if fam.FamilyCategory \
                    else "N/A"
                fam_creator = \
                    DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                                  fam.Id).Creator
                if fam_path:
                    if op.exists(fam_path):
                        fam_size = op.getsize(fam_path)
                all_family_items.append({"Size": fam_size,
                                         "Creator": fam_creator,
                                         "Category": fam_category,
                                         "Name": fam.Name})
        if pb.cancelled:
            break
        else:
            pb.update_progress(i, len(all_fams))
        i += 1


# print results
print("Families overview:")
print_sorted(all_family_items, sort_by)
print_totals(all_family_items)

