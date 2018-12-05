# -*- coding: utf-8 -*-
import os
import os.path as op
import sys
import pickle

from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()

datafile = script.get_document_data_file("SelList", "pym")
index_datafile = script.get_document_data_file("SelListPrevNextIndex", "pym")


selection = revit.get_selection()


def iterate(mode, step_size=1):
    if op.exists(index_datafile):
        with open(index_datafile, 'r') as f:
            idx = pickle.load(f)

        if mode == '-':
            idx = idx - step_size
        else:
            idx = idx + step_size
    else:
        idx = 0

    try:
        with open(datafile, 'r') as df:
            cursel = pickle.load(df)

        if idx < 0:
            idx = abs(idx / len(cursel)) * len(cursel) + idx
        elif idx >= len(cursel):
            idx = idx - abs(idx / len(cursel)) * len(cursel)

        selection.set_to([DB.ElementId(int(list(cursel)[idx]))])

        with open(index_datafile, 'w') as f:
            pickle.dump(idx, f)

    except Exception as io_err:
        logger.error('Error read/write to: {} | {}'.format(datafile, io_err))
