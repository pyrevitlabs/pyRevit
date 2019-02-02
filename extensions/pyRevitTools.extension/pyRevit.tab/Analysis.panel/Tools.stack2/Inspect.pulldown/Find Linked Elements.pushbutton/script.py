#pylint: disable=import-error,invalid-name
from pyrevit import script
from pyrevit import revit, DB


__context__ = 'selection'
__helpurl__ = '{{docpath}}4IlvCkoOolw'
__doc__ = "Lists all the elements that are tied to the selected element."\
          " For example elements tags or dimensions."


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
            print("ID: {}\t\tTYPE: {} ( selected object )"
                  .format(elid_link, el.GetType().Name))
        elif el:
            elid_link = output.linkify(elId)
            if isinstance(el, DB.FamilyInstance):
                family_name = revit.query.get_family_name(el)
                symbol_name = revit.query.get_symbol_name(el)
                print("ID: {}\t\tTYPE: {} ({}) --> {}:{}"
                      .format(elid_link,
                              el.GetType().Name,
                              el.Category.Name,
                              family_name,
                              symbol_name))
            else:
                print("ID: {}\t\tTYPE: {}"
                      .format(elid_link, el.GetType().Name))
