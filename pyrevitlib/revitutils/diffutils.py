from revitutils import doc
from pyrevit.coreutils.console import output_window

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector


def element_hash(rvt_element, include_type=False):
    def param_hash(param):
        repr_str = '{} {}'.format(str(param.Definition.Name).ljust(30), param.AsValueString())
        return hash(repr_str)

    domain_param_exclude_list = ['Workset', 'Edited by', 'Design Option']
    type_param_exclude_list = ['Type', 'Type Name', 'Type Id', 'Family', 'Family Name', 'Family and Type']
    hash_value = 0
    for param in rvt_element.Parameters:
        if param.Definition.Name not in domain_param_exclude_list:
            if include_type:
                hash_value += param_hash(param)
            elif param.Definition.Name not in type_param_exclude_list:
                hash_value += param_hash(param)
    return hash_value


def element_list_hash(element_list, include_type=False):
    hashes = [element_hash(el, include_type) for el in element_list]
    return sum(sorted(hashes))


def compare(element_a, element_b, compare_types=False):
    return element_hash(element_a, compare_types) == element_hash(element_b, compare_types)


def compare_elmnt_sets(elementset_a, elementset_b, compare_types=False):
    return element_list_hash(elementset_a, compare_types) == element_list_hash(elementset_b, compare_types)


def compare_views(view_a, view_b, compare_types=False):
    view_a_elmts = FilteredElementCollector(doc).OwnedByView(view_a.Id).WhereElementIsNotElementType().ToElements()
    view_b_elmts = FilteredElementCollector(doc).OwnedByView(view_b.Id).WhereElementIsNotElementType().ToElements()
    return compare_elmnt_sets(view_a_elmts, view_b_elmts, compare_types)
