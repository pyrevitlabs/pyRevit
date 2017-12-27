"""Helper functions to query info and elements from Revit."""

import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit import DB


class ModelSharedParam:
    def __init__(self, param_def, param_binding=None):
        self.param_def = param_def
        self.param_binding = param_binding

    def __eq__(self, other):
        if isinstance(self.param_def, DB.ExternalDefinition):
            return self.param_def.GUID == other or self.param_def.Name == other
        else:
            return self.param_def.Name == other


def get_all_elements(doc=None):
    return DB.FilteredElementCollector(doc or HOST_APP.doc)\
             .WhereElementIsNotElementType()\
             .ToElements()


def get_param_value(targetparam):
    if targetparam.StorageType == DB.StorageType.Double:
        value = targetparam.AsDouble()
    elif targetparam.StorageType == DB.StorageType.Integer:
        value = targetparam.AsInteger()
    elif targetparam.StorageType == DB.StorageType.String:
        value = targetparam.AsString()
    elif targetparam.StorageType == DB.StorageType.ElementId:
        value = targetparam.AsElementId()

    return value


def get_value_range(param_name, doc=None):
    values = set()
    for el in get_all_elements(doc):
        targetparam = el.LookupParameter(param_name)
        if targetparam:
            value = get_param_value(targetparam)
            if type(value) == str and not value.isspace():
                values.add(value)
            else:
                values.add(value)
    return values


def get_elements_by_parameter(param_name, param_value, doc=None):
    # does not work in < 2016
    # spid = framework.Guid('24353a46-1313-46a4-a779-d33ffe9353ab')
    # pid = DB.SharedParameterElement.Lookup(revit.doc, spid)
    # pp = DB.ParameterValueProvider(pid)
    # pe = DB.FilterStringEquals()
    # vrule = DB.FilterDoubleRule(pp, pe, scope_id, True)
    # param_filter = DB.ElementParameterFilter(vrule)
    # elements = DB.FilteredElementCollector(revit.doc) \
    #           .WherePasses(param_filter) \
    #           .ToElementIds()

    found_els = []
    for el in get_all_elements(doc):
        targetparam = el.LookupParameter(param_name)
        if param_value == get_param_value(targetparam):
            found_els.append(el)

    return found_els


def find_workset(workset_name_or_list, doc=None, partial=True):
    workset_clctr = \
        DB.FilteredWorksetCollector(doc or HOST_APP.doc).ToWorksets()
    if type(workset_name_or_list) == list:
        for workset in workset_clctr:
            for workset_name in workset_name_or_list:
                if workset_name in workset.Name:
                    return workset

    elif type(workset_name_or_list) == str:
        workset_name = workset_name_or_list

        if partial:
            for workset in workset_clctr:
                if workset_name in workset.Name:
                    return workset
        else:
            for workset in workset_clctr:
                if workset_name == workset.Name:
                    return workset


def model_has_family(family_name, doc=None):
    bip_id = DB.ElementId(DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM)
    param_value_provider = DB.ParameterValueProvider(bip_id)
    value_rule = DB.FilterStringRule(param_value_provider,
                                     DB.FilterStringEquals(),
                                     family_name,
                                     True)
    symbol_name_filter = DB.ElementParameterFilter(value_rule)
    collector = DB.FilteredElementCollector(doc or HOST_APP.doc)\
                  .WherePasses(symbol_name_filter)

    return hasattr(collector, 'Count') and collector.Count > 0


def model_has_workset(workset_name, doc=None):
    return find_workset(workset_name, doc=doc)


def get_model_sharedparams(doc=None):
    doc = doc or HOST_APP.doc
    param_bindings = doc.ParameterBindings
    pb_iterator = param_bindings.ForwardIterator()
    pb_iterator.Reset()

    msp_list = []
    while pb_iterator.MoveNext():
        msp = ModelSharedParam(pb_iterator.Key,
                               param_bindings[pb_iterator.Key])
        msp_list.append(msp)

    return msp_list


def model_has_sharedparam(param_id_or_name, doc=None):
    msp_list = get_model_sharedparams(doc)
    for x in msp_list:
        if x == param_id_or_name:
            return True
    return False


def get_sharedparam_definition_file():
    if HOST_APP.app.SharedParametersFilename:
        return HOST_APP.app.OpenSharedParameterFile()
    else:
        raise PyRevitException('No Shared Parameter file defined.')


def get_defined_sharedparams():
    msp_list = []
    for def_group in get_sharedparam_definition_file().Groups:
        msp_list.extend([ModelSharedParam(x) for x in def_group.Definitions])
    return msp_list
