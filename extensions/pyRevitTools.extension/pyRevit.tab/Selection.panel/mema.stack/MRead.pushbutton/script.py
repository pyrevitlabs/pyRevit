import pickle

from pyrevit.framework import List
from pyrevit import script
from pyrevit import revit, DB


__helpurl__ = '{{docpath}}pAM-ARIXXLw'
__doc__ = 'Read selection from memory.\n'\
          'Works like the MR button in a calculator. '\
          'This is a project-dependent memory. Every project has its own '\
          'selection memory saved in %appdata%/pyRevit folder as *.pym files.'

selection = revit.get_selection()

datafile = script.get_document_data_file("SelList", "pym")


try:
    f = open(datafile, 'r')
    current_selection = pickle.load(f)
    f.close()

    element_ids = []
    for elid in current_selection:
        element_ids.append(DB.ElementId(int(elid)))

    selection.set_to(element_ids)
except Exception:
    pass
