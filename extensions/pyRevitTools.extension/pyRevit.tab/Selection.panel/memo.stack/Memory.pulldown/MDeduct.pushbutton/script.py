import os
import os.path as op
import pickle as pl

from pyrevit import revit
from pyrevit import script
from pyrevit.compat import get_value_func


datafile = script.get_document_data_file("SelList", "pym")

selection = revit.get_selection()
value_func = get_value_func()
selected_ids = {str(value_func(elid)) for elid in selection.element_ids}

try:
    f = open(datafile, 'rb')
    prevsel = pl.load(f)
    newsel = prevsel.difference(selected_ids)
    f.close()
    f = open(datafile, 'wb')
    pl.dump(newsel, f)
    f.close()
except Exception:
    f = open(datafile, 'wb')
    pl.dump([], f)
    f.close()
