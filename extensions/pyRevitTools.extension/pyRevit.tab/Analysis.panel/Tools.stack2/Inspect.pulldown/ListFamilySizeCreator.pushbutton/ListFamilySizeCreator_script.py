# -*- coding: utf-8 -*-
"""List all families and their sizes."""
import os.path as op
import math
from collections import defaultdict

from pyrevit import revit, DB

__title__ = 'Lists Family Sizes'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_unit = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    size = round(size_bytes / p, 2)
    return "{}{}".format(size, size_unit[i])


all_fams = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.Family)\
             .ToElements()

fams_creator = defaultdict(list)

for fam in all_fams:
    if fam.IsEditable:
        fam_doc = revit.doc.EditFamily(fam)
        fam_path = fam_doc.PathName
        fam_size = "0"
        fam_creator = \
            DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                          fam.Id).Creator
        if fam_path:
            if op.exists(fam_path):
                fam_size = str(op.getsize(fam_path))
        fams_creator[fam_creator].append(fam_size + "; " + fam.Name)

print("Families overview:")
for creator in fams_creator:
    print(50*"-")
    print("{} created:".format(creator))
    sum_size_created = 0
    for fam in fams_creator[creator]:
        size_prefix = int(fam.split(";")[0])
        fam_name = fam.split(";")[1]
        sum_size_created += int(size_prefix)
        if size_prefix == 0:
            size_prefix = " N/A "
        else:
            size_prefix = convert_size(size_prefix)
        print(size_prefix, fam_name)
    print("{1} families, found total size: {0}"
          .format(convert_size(sum_size_created),
                  len(fams_creator[creator])))
