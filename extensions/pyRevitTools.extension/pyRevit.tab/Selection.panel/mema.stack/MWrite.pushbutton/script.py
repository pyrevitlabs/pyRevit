import pickle

from pyrevit import script
from pyrevit import revit
from pyrevit.compat import get_value_func


datafile = script.get_document_data_file("SelList", "pym")

selection = revit.get_selection()
value_func = get_value_func()
selected_ids = {str(value_func(elid)) for elid in selection.element_ids}

f = open(datafile, 'wb')
pickle.dump(selected_ids, f)
f.close()
