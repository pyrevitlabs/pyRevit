# -*- coding: utf-8 -*-
"""
Families Quickcheck - non-exhaustive quickcheck to detect corrupt Revit
families. Last family id before corruption error is most likely the suspect.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__title__ = 'Families Quickcheck'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Families Quickcheck - '\
          'non-exhaustive quickcheck to detect corrupt families.'

import Autodesk
from Autodesk.Revit.DB import FilteredElementCollector as Fec
from Autodesk.Revit.DB import Family
from System.Diagnostics import Stopwatch
from rpw import doc

stopwatch = Stopwatch()
stopwatch.Start()

all_families = Fec(doc).OfClass(Family).ToElements()
checked_families = 0

for fam in all_families:
    if fam.IsEditable:
        checked_families += 1
        print("--{}-----".format(str(checked_families).zfill(4)))
        print("attempt to open family: {}".format(fam.Name))
        fam_doc = doc.EditFamily(fam)
        print("{} seems ok.".format(fam.Name))

print("\nquickchecked: {0} families\n{1} run in: ".format(checked_families, __title__))

stopwatch.Stop()
timespan = stopwatch.Elapsed
print(timespan)
