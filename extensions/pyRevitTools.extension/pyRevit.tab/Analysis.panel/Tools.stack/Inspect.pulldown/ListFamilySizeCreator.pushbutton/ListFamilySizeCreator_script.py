# -*- coding: utf-8 -*-
"""List all families and their sizes."""
import os
import math
import tempfile
from pyrevit import revit, forms, script, DB, HOST_APP

__title__ = 'Lists Family Sizes'
__authors__ = ['Frederic Beaupere', 'Alex Melnikov']
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'

FIELDS = ["Size", "Name", "Category", "Creator"]
# temporary path for saving families
temp_dir = os.path.join(tempfile.gettempdir(), "pyRevit_ListFamilySizes")
if not os.path.exists(temp_dir):
    os.mkdir(temp_dir)
save_as_options = DB.SaveAsOptions()
save_as_options.OverwriteExistingFile = True

def convert_size(size_bytes):
    if not size_bytes:
        return "N/A"
    size_unit = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    size = round(size_bytes / p, 2)
    return "{}{}".format(size, size_unit[i])


def print_totals(families):
    total_size = sum([fam_item.get("Size") or 0 for fam_item in families])
    print("%d families, found total size: %s\n\n" % (
        len(families), convert_size(total_size)))


def print_sorted(families, group_by):
    # group by provided field, use the next field in the list to sort by
    fields_rest = list(FIELDS)
    fields_rest.pop(FIELDS.index(group_by))
    sort_by = fields_rest[0]
    fields_sorted = [group_by] + fields_rest

    if group_by not in ["Creator", "Category"]: # do not group by name and size
        print("Sort by: %s" % group_by)
        print("; ".join(fields_sorted))
        families_grouped = {"": sorted(families, key=\
            lambda fam_item: fam_item.get(group_by),
                                       reverse=group_by=="Size")}
    else:
        print("Group by: %s" % group_by)
        print("Sort by: %s" % sort_by)
        print(";".join(fields_rest))
        # convert to grouped dict
        families_grouped = {}
        # reverse if sorted by Size
        for fam_item in sorted(families, key=\
                lambda fam_item: fam_item.get(sort_by),
                               reverse=sort_by=="Size"):
            group_by_value = fam_item[group_by]
            fam_item_reduced = dict(fam_item)
            fam_item_reduced.pop(group_by)
            if group_by_value not in families_grouped:
                families_grouped[group_by_value] = []
            families_grouped[group_by_value].append(fam_item_reduced)

    for group_value in sorted(families_grouped.keys()):
        print(50 * "-")
        print("%s: %s" % (group_by, group_value))
        for fam_item in families_grouped[group_value]:
            family_row = []
            for field in fields_sorted:
                value = fam_item.get(field)
                if value is None:
                    continue
                if field == "Size":
                    value = convert_size(value)
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
opened_families = [od.Title for od in HOST_APP.uiapp.Application.Documents
                   if od.IsFamilyDocument]
with forms.ProgressBar(title=__title__, cancellable=True) as pb:
    i = 0

    for fam in all_fams:
        with revit.ErrorSwallower() as swallower:
            if fam.IsEditable:
                fam_doc = revit.doc.EditFamily(fam)
                fam_path = fam_doc.PathName
                # if the family path does not exists, save it temporary
                #  only if the wasn't opened when the script was started
                if fam_doc.Title not in opened_families and (
                        not fam_path or not os.path.exists(fam_path)):
                    # edit family
                    fam_doc = revit.doc.EditFamily(fam)
                    # save with temporary path, to know family size
                    fam_path = os.path.join(temp_dir, fam_doc.Title)
                    fam_doc.SaveAs(fam_path, save_as_options)

                fam_size = 0
                fam_category = fam.FamilyCategory.Name if fam.FamilyCategory \
                    else "N/A"
                fam_creator = \
                    DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                                  fam.Id).Creator
                if fam_path and os.path.exists(fam_path):
                    fam_size = os.path.getsize(fam_path)
                all_family_items.append({"Size": fam_size,
                                         "Creator": fam_creator,
                                         "Category": fam_category,
                                         "Name": fam.Name})
                # if the family wasn't opened before, close it
                if fam_doc.Title not in opened_families:
                    fam_doc.Close(False)
                    # remove temporary family
                    if fam_path.lower().startswith(temp_dir.lower()):
                        os.remove(fam_path)
        if pb.cancelled:
            break
        else:
            pb.update_progress(i, len(all_fams))
        i += 1


# print results
print("Families overview:")
print_sorted(all_family_items, sort_by)
print_totals(all_family_items)

