import pickle

from pyrevit import script
from pyrevit import revit, DB, HOST_APP
from System import Int64

selection = revit.get_selection()
logger = script.get_logger()
datafile = script.get_document_data_file("SelList", "pym")

try:
    f = open(datafile, "rb")
    current_selection = pickle.load(f)
    f.close()

    element_ids = []
    if HOST_APP.is_newer_than(2025):
        for elid in current_selection:
            element_ids.append(DB.ElementId(Int64(elid)))
    else:
        for elid in current_selection:
            element_ids.append(DB.ElementId(int(elid)))

    selection.set_to(element_ids)
except Exception as e:
    logger.debug("Error loading selection: %s" % e)
    script.exit()
