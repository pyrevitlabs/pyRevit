import pickle

from pyrevit import script
from pyrevit import revit


datafile = script.get_document_data_file("SelList", "pym")


selection = revit.get_selection()
selected_ids = {str(elid.IntegerValue) for elid in selection.element_ids}

try:
    f = open(datafile, 'r')
    prevsel = pickle.load(f)
    new_selection = prevsel.union(selected_ids)
    f.close()
except Exception:
    new_selection = selected_ids

f = open(datafile, 'w')
pickle.dump(new_selection, f)
f.close()
