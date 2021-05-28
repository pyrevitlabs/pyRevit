from pyrevit import revit, DB
from pyrevit import script


selection = revit.get_selection()
logger = script.get_logger()


filtered_elements = []
for el in selection:
    try:
        host = el.Host
        if isinstance(host, DB.RevitLinkInstance):
            filtered_elements.append(el.Id)
    except Exception as err:
        logger.debug('{} | {}'.format(el.Id, err))
        continue

selection.set_to(filtered_elements)
