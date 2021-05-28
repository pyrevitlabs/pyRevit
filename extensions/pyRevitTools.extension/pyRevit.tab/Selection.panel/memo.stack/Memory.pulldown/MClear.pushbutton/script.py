import os
import os.path as op
import pickle as pl

from pyrevit import revit
from pyrevit import script


datafile = script.get_document_data_file("SelList", "pym")

f = open(datafile, 'wb')
pl.dump([], f)
f.close()
