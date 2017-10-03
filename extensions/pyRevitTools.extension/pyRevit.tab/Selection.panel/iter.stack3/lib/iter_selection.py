# -*- coding: utf-8 -*-
from Autodesk.Revit.DB import ElementId
from System.Collections.Generic import List

import os
import sys
import pickle as pl

from scriptutils import this_script, logger
from revitutils import uidoc, doc

datafile = this_script.get_document_data_file(0, "pym", command_name="SelList")
datafile_i = this_script.get_document_data_file(0, "pym", command_name="Iter")

def iterate(mode, step_size=1):
    # if (index == 0 and len(list(uidoc.Selection.GetElementIds())) == 1):
    #     eId = list(uidoc.Selection.GetElementIds())[0]
    # else:
    # getting last id
    if os.path.isfile(datafile_i):
        f = open(datafile_i, 'r')
        cur_i = pl.load(f)
        f.close()

        if (mode == '-'):
            i = cur_i - step_size
        else:
            i = cur_i + step_size
    else:
        i = 0

    try:
        f = open(datafile, 'r')
        cursel = pl.load(f)
        f.close()
        _i = i
        if (i < 0):
            i = abs(i / len(cursel)) * len(cursel) + i
        elif (i >= len(cursel)):
            i = i - abs(i / len(cursel)) * len(cursel)

        eId = ElementId(int(list(cursel)[i]))
        uidoc.Selection.SetElementIds(List[ElementId]([eId]))

        f = open(datafile_i, 'w')
        pl.dump(i, f)
        f.close()

    except:
        e = 'Can not find selection file:\n{0}\n\nFirstly save selection using MWrite'.format(datafile)
        logger.warning(e)
