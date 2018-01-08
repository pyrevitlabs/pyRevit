"""Saves current selection memory as a Selection Filter."""

import os
import os.path as op
import pickle as pl

from pyrevit.coreutils import timestamp
from pyrevit import revit, DB
from pyrevit import script


proj_info = revit.get_project_info()
datafile = script.get_document_data_file("SelList", "pym")

if op.exists(datafile):
    if proj_info.name:
        filtername = 'SavedSelection_' + proj_info.name + '_' + timestamp()
    else:
        filtername = 'SavedSelection_' + timestamp()

    with open(datafile, 'r') as f:
        cursel = pl.load(f)

    with revit.Transaction('pySaveSelection'):
        selFilter = DB.SelectionFilterElement.Create(revit.doc, filtername)
        for elid in cursel:
            selFilter.AddSingle(DB.ElementId(int(elid)))
