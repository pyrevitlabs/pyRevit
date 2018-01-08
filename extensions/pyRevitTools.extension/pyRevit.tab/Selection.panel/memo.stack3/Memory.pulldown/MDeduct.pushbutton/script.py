import os
import os.path as op
import pickle as pl

from pyrevit import revit
from pyrevit import script


__doc__ = 'Deducts selection from memory keeping the rest.\n'\
          'Works like the M- button in a calculator. '\
          'This is a project-dependent memory. Every project has its own '\
          'selection memory saved in %appdata%/pyRevit folder as *.pym files.'


datafile = script.get_document_data_file("SelList", "pym")

selection = revit.get_selection()
selected_ids = {str(elid.IntegerValue) for elid in selection.element_ids}

try:
    f = open(datafile, 'r')
    prevsel = pl.load(f)
    newsel = prevsel.difference(selected_ids)
    f.close()
    f = open(datafile, 'w')
    pl.dump(newsel, f)
    f.close()
except Exception:
    f = open(datafile, 'w')
    pl.dump([], f)
    f.close()
