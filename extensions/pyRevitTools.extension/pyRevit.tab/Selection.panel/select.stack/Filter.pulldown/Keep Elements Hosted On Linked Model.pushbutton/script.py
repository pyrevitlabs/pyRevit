from pyrevit import revit, DB
from pyrevit import script


__context__ = 'Selection'
__doc__ = 'Looks into the current selection elements and '\
          'keeps the ones hosted on a linked model surface.'


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
