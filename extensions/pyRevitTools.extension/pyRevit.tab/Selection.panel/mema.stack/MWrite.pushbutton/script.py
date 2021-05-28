import pickle

from pyrevit import script
from pyrevit import revit


datafile = script.get_document_data_file("SelList", "pym")

selection = revit.get_selection()
selected_ids = {str(elid.IntegerValue) for elid in selection.element_ids}

f = open(datafile, 'w')
pickle.dump(selected_ids, f)
f.close()
