import pickle

from pyrevit import script
from pyrevit import revit
from pyrevit.compat import get_elementid_from_value_func

selection = revit.get_selection()
logger = script.get_logger()
datafile = script.get_document_data_file("SelList", "pym")
get_elementid_from_value = get_elementid_from_value_func()

try:
    f = open(datafile, "rb")
    current_selection = pickle.load(f)
    f.close()

    element_ids = []
    for elid in current_selection:
        element_ids.append(get_elementid_from_value(elid))

    selection.set_to(element_ids)
except Exception as e:
    logger.debug("Error loading selection: %s" % e)
    script.exit()
