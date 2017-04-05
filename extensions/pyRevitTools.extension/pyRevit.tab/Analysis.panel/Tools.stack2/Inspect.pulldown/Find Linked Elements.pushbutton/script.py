"""Lists all the elements that are tied to the selected element. For example elements tags or dimensions."""

from scriptutils import this_script
from revitutils import doc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction


if not selection.is_empty:
    t = Transaction(doc, "Search for linked elements")
    t.Start()

    print("Searching for all objects tied to ELEMENT ID: {0}...".format(selection.first.Id))
    linked_elements_list = doc.Delete(selection.first.Id)

    t.RollBack()


    for elId in linked_elements_list:
        el = doc.GetElement(elId)
        if el and elId in selection.element_ids:
            elid_link = this_script.output.linkify(elId)
            print("ID: {0}\t\tTYPE: {1} ( selected object )".format(elid_link, el.GetType().Name))
        elif el:
            elid_link = this_script.output.linkify(elId)
            print("ID: {0}\t\tTYPE: {1}".format(elid_link, el.GetType().Name))
