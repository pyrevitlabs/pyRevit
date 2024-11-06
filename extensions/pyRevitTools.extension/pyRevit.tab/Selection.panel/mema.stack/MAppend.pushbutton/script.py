import pickle

from pyrevit import script
from pyrevit import revit
from pyrevit.compat import get_elementid_value_func


datafile = script.get_document_data_file("SelList", "pym")


selection = revit.get_selection()
get_elementid_value = get_elementid_value_func()
selected_ids = {str(get_elementid_value(elid)) for elid in selection.element_ids}

try:
    f = open(datafile, 'rb')
    prevsel = pickle.load(f)
    new_selection = prevsel.union(selected_ids)
    f.close()
except Exception:
    new_selection = selected_ids

f = open(datafile, 'wb')
pickle.dump(new_selection, f)
f.close()
