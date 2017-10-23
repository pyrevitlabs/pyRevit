from pyrevit import script
from pyrevit import revit


__doc__ = 'Lists all the elements that are tied to the selected element.'\
          ' For example elements tags or dimensions.'


selection = revit.get_selection()
output = script.get_output()


if not selection.is_empty:
    print("Searching for all objects tied to ELEMENT ID: {0}..."
          .format(selection.first.Id))
    with revit.DryTransaction("Search for linked elements"):
        linked_elements_list = revit.doc.Delete(selection.first.Id)

    for elId in linked_elements_list:
        el = revit.doc.GetElement(elId)
        if el and elId in selection.element_ids:
            elid_link = output.linkify(elId)
            print("ID: {0}\t\tTYPE: {1} ( selected object )"
                  .format(elid_link, el.GetType().Name))
        elif el:
            elid_link = output.linkify(elId)
            print("ID: {0}\t\tTYPE: {1}"
                  .format(elid_link, el.GetType().Name))
