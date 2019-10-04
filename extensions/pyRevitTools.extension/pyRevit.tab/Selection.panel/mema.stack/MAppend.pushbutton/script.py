import pickle

from pyrevit import script
from pyrevit import revit


__context__ = 'Selection'
__helpurl__ = '{{docpath}}pAM-ARIXXLw'
__doc__ = 'Append current selection to memory.\n'\
          'Works like the M+ button in a calculator. '\
          'This is a project-dependent memory. Every project has its own '\
          'selection memory saved in %appdata%/pyRevit folder as *.pym files.'


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
