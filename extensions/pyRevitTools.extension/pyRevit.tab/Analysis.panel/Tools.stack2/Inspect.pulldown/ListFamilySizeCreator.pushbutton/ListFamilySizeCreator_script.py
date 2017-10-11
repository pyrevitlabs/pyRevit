# -*- coding: utf-8 -*-
"""
Lists Families and their sizes grouped by creator.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__title__ = 'Lists Families and their sizes grouped by creator'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Lists Families and their sizes grouped by creator.'

import os.path as op
import math
from collections import defaultdict
import Autodesk
from Autodesk.Revit.DB import FilteredElementCollector as Fec
from Autodesk.Revit.DB import WorksharingUtils
from revitutils import doc


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_unit = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    size = round(size_bytes / p, 2)
    return "{}{}".format(size, size_unit[i])


all_fams = Fec(doc).OfClass(Autodesk.Revit.DB.Family).ToElements()
fams_creator = defaultdict(list)

for fam in all_fams:
    if fam.IsEditable:
        fam_doc = doc.EditFamily(fam)
        fam_path = fam_doc.PathName
        fam_size = "N/A"
        fam_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, fam.Id).Creator
        if fam_path:
            if op.exists(fam_path):
                fam_size = convert_size(op.getsize(fam_path))
        fams_creator[fam_creator].append(fam_size + " ; " + fam.Name)

print("Families overview:")
for creator in fams_creator:
    print(50*"-")
    print("{} created {} families:".format(creator,
                                           len(fams_creator[creator])))
    for fam in fams_creator[creator]:
        print(fam)
