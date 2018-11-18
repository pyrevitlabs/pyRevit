import re

from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import reverse_dict, get_str_hash
from pyrevit import DB


logger = get_logger(__name__)


type_param_exclude_list = ['Type', 'Type Name', 'Type Id', 'Family',
                           'Family Name', 'Family and Type']

domain_param_exclude_list = ['Workset', 'Edited by', 'Design Option',
                             'Drawn By', 'Level', 'Comments',
                             'Copyright', 'Image']

custom_attrs = {DB.TextNote: ['LeaderCount', 'LeaderLeftAttachment',
                              'LeaderRightAttachment', 'Text'],
                DB.Dimension: ['Above', 'Below', 'Prefix', 'Suffix',
                               'ValueOverride', 'AreSegmentsEqual',
                               'NumberOfSegments']}


class DiffResults:
    def __init__(self):
        self.processed_params = set()
        self.rvt_element_types = set()
        self.diff_elements = []


def cleanup_repr_str(repr_str):
    repr_str = repr_str.strip('\n,\r')
    return re.sub(' +', ' ', repr_str)


def element_hash(rvt_element, include_type=False, diff_results=None):

    def param_hash(param):
        repr_str = '{} {}'.format(unicode(param.Definition.Name).ljust(30),
                                  param.AsValueString())
        if diff_results:
            diff_results.processed_params.add(param.Definition.Name)
        return get_str_hash(cleanup_repr_str(repr_str))

    def attribute_hash(el, attribute):
        try:
            repr_str = unicode(getattr(el, attribute))
        except Exception as hash_err:
            logger.debug('Error reading attribute: '
                         '{} form element {} with id: {} | {}'
                         .format(attribute, el, el.Id, hash_err))
            return ''

        if diff_results:
            diff_results.processed_params.add(attribute)

        return get_str_hash(cleanup_repr_str(repr_str))

    sorted_params = sorted(rvt_element.Parameters,
                           key=lambda x: x.Definition.Name)
    if diff_results:
        diff_results.rvt_element_types.add(type(rvt_element))

    hash_value = ''
    for parameter in sorted_params:
        if parameter.Definition.Name not in domain_param_exclude_list:
            if include_type:
                hash_value += param_hash(parameter)
            elif parameter.Definition.Name not in type_param_exclude_list:
                hash_value += param_hash(parameter)

    if type(rvt_element) in custom_attrs:
        for el_attr in custom_attrs[type(rvt_element)]:
            hash_value += attribute_hash(rvt_element, el_attr)

    return get_str_hash(hash_value)


def element_hash_dict(element_list, include_type=False, diff_results=None):
    return {el.Id.IntegerValue: element_hash(el, include_type, diff_results)
            for el in element_list}


def compare(element_a, element_b, compare_types=False, diff_results=None):
    return element_hash(element_a,
                        compare_types,
                        diff_results) == element_hash(element_b,
                                                      compare_types,
                                                      diff_results)


def compare_elmnt_sets(elementset_a, elementset_b,
                       compare_types=False, diff_results=None):
    dict_a = element_hash_dict(elementset_a, compare_types, diff_results)
    hash_list_a = sorted(dict_a.values())

    dict_b = element_hash_dict(elementset_b, compare_types, diff_results)
    hash_list_b = sorted(dict_b.values())

    if hash_list_a == hash_list_b:
        return True

    elif diff_results:
        rdict_a = reverse_dict(dict_a)
        rdict_b = reverse_dict(dict_b)
        for el_hash in set(hash_list_a) ^ set(hash_list_b):
            if el_hash in rdict_a:
                for el_id in rdict_a[el_hash]:
                    diff_results.diff_elements.append(DB.ElementId(el_id))

            if el_hash in rdict_b:
                for el_id in rdict_b[el_hash]:
                    diff_results.diff_elements.append(DB.ElementId(el_id))

    return False


def compare_views(doc, view_a, view_b, compare_types=False, diff_results=None):
    view_a_elmts = DB.FilteredElementCollector(doc)\
                     .OwnedByView(view_a.Id)\
                     .WhereElementIsNotElementType()\
                     .ToElements()
    view_b_elmts = DB.FilteredElementCollector(doc)\
                     .OwnedByView(view_b.Id)\
                     .WhereElementIsNotElementType()\
                     .ToElements()

    # pick the detail elements only
    det_elmts_a = [el for el in view_a_elmts if el.ViewSpecific]
    det_elmts_b = [el for el in view_b_elmts if el.ViewSpecific]

    # compare and return result
    return compare_elmnt_sets(det_elmts_a,
                              det_elmts_b,
                              compare_types,
                              diff_results)
