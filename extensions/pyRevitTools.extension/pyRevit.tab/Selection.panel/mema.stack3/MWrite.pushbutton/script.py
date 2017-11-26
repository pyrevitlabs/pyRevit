import pickle

from pyrevit import script
from pyrevit import revit


__context__ = 'Selection'
__helpurl__ = 'https://www.youtube.com/watch?v=pAM-ARIXXLw'
__doc__ = 'Clear memory and Append current selection. Works like the'\
          ' M+ button in a calculator. This is a project-dependent'\
          ' (Revit *.rvt) memory. Every project has its own memory saved in'\
          ' user temp folder as *.pym files.'


datafile = script.get_document_data_file("SelList", "pym")

selection = revit.get_selection()
selected_ids = {str(elid.IntegerValue) for elid in selection.element_ids}

f = open(datafile, 'w')
pickle.dump(selected_ids, f)
f.close()
