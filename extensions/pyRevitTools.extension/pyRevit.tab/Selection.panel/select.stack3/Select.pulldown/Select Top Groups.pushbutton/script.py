__doc__ = """Selects group instances, which contain selected elements. 
By default excludes not grouped elements from selection.

Shift+Click: include not grouped elements"""
__context__ = 'Selection'

from pyrevit import revit, script

selection = revit.get_selection()
logger = script.get_logger()

def get_higher_group(doc, element):
    logger.debug("get_higher_group: Process id %d" % element.Id.IntegerValue)
    if element.GroupId.IntegerValue != -1:
        logger.debug("get_higher_group: element is grouped. GroupId=%d" % element.GroupId.IntegerValue)
        group = doc.GetElement(element.GroupId)
        logger.debug("get_higher_group: groupd=%s" % str(group))
        return get_higher_group(doc, group)
    else:
        logger.debug("get_higher_group: element not grouped")
        return element

if __name__ == '__main__':
    sel = selection.elements
    doc = revit.doc

    ids_to_select = set()
    elements_to_select = []

    for e in sel:
        if e.GroupId.IntegerValue != -1: # leave only groupped elements
            higher_group = get_higher_group(doc, e)
            ids_to_select.add(higher_group.Id)
        else:
            if __shiftclick__:
                elements_to_select.append(e.Id)

    elements_to_select += map(lambda e_id: doc.GetElement(e_id), ids_to_select)
    selection.set_to(elements_to_select)
