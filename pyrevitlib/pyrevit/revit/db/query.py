# -*- coding: utf-8 -*-
"""Helper functions to query info and elements from Revit."""
# pylint: disable=W0703,C0103,too-many-lines
from collections import namedtuple
from os.path import basename, splitext

from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit import HOST_APP, DOCS, PyRevitException
from pyrevit import framework
from pyrevit.compat import PY3, safe_strtype, get_elementid_value_func
from pyrevit import DB
from pyrevit.revit import db
from pyrevit.revit import features

from Autodesk.Revit.DB import Element  # pylint: disable=E0401


mlogger = logger.get_logger(__name__)


GRAPHICAL_VIEWTYPES = [
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.Elevation,
    DB.ViewType.ThreeD,
    DB.ViewType.Schedule,
    DB.ViewType.DrawingSheet,
    DB.ViewType.Report,
    DB.ViewType.DraftingView,
    DB.ViewType.Legend,
    DB.ViewType.EngineeringPlan,
    DB.ViewType.AreaPlan,
    DB.ViewType.Section,
    DB.ViewType.Detail,
    DB.ViewType.CostReport,
    DB.ViewType.LoadsReport,
    DB.ViewType.PresureLossReport,
    DB.ViewType.ColumnSchedule,
    DB.ViewType.PanelSchedule,
    DB.ViewType.Walkthrough,
    DB.ViewType.Rendering,
]


DETAIL_CURVES = (DB.DetailLine, DB.DetailArc, DB.DetailEllipse, DB.DetailNurbSpline)

MODEL_CURVES = (DB.ModelLine, DB.ModelArc, DB.ModelEllipse, DB.ModelNurbSpline)

BUILTINCATEGORIES_VIEW = [
    DB.BuiltInCategory.OST_Views,
    DB.BuiltInCategory.OST_ReferenceViewer,
    DB.BuiltInCategory.OST_Viewers,
]

GridPoint = namedtuple("GridPoint", ["point", "grids"])

SheetRefInfo = namedtuple(
    "SheetRefInfo", ["sheet_num", "sheet_name", "detail_num", "ref_viewid"]
)

ElementHistory = namedtuple("ElementHistory", ["creator", "owner", "last_changed_by"])


def get_name(element, title_on_sheet=False):
    """
    Retrieves the name of a Revit element, with special handling for views.

    Args:
        element (DB.Element): The Revit element whose name is to be retrieved.
        title_on_sheet (bool, optional): If True and the element is a view,
                                         attempts to retrieve the view's title
                                         on the sheet. Defaults to False.

    Returns:
        str: The name of the element. For views, it may return the view's title
             on the sheet if `title_on_sheet` is True and the title is available.
    """
    if isinstance(element, DB.View):
        view_name = None
        if title_on_sheet:
            titleos_param = element.Parameter[DB.BuiltInParameter.VIEW_DESCRIPTION]
            view_name = titleos_param.AsString()
        if view_name:
            return view_name
        else:
            if HOST_APP.is_newer_than("2019", or_equal=True):
                return element.Name
            else:
                return element.ViewName
    if PY3:
        return element.Name
    else:
        return Element.Name.GetValue(element)


def get_type(element):
    """Get element type.

    Args:
        element (DB.Element): source element

    Returns:
        (DB.ElementType): type object of given element
    """
    type_id = element.GetTypeId()
    return element.Document.GetElement(type_id)


def get_symbol_name(element):
    """
    Retrieves the name of the symbol associated with the given Revit element.

    Args:
        element: The Revit element from which to retrieve the symbol name.

    Returns:
        str: The name of the symbol associated with the given element.
    """
    return get_name(element.Symbol)


def get_family_name(element):
    """
    Retrieves the family name of a given Revit element.

    Args:
        element: The Revit element from which to get the family name.
                 It is expected to have a 'Symbol' attribute with a 'Family' property.

    Returns:
        str: The name of the family to which the element belongs.
    """
    return get_name(element.Symbol.Family)


# episode_id and guid explanation
# https://thebuildingcoder.typepad.com/blog/2009/02/uniqueid-dwf-and-ifc-guid.html
def get_episodeid(element):
    """
    Extract episode id from the given Revit element.

    Args:
        element: The Revit element from which to extract the episode id.

    Returns:
        str: The episode id extracted from the element's UniqueId.
    """
    return str(element.UniqueId)[:36]


def get_guid(element):
    """
    Generates a GUID for a given Revit element by performing a bitwise XOR operation
    on parts of the element's UniqueId.

    Args:
        element: The Revit element for which the GUID is to be generated. The element
                 must have a UniqueId attribute.

    Returns:
        str: A string representing the generated GUID.
    """
    uid = str(element.UniqueId)
    last_32_bits = int(uid[28:36], 16)
    element_id = int(uid[37:], 16)
    xor = last_32_bits ^ element_id
    return uid[:28] + "{0:x}".format(xor)


def get_param(element, param_name, default=None):
    """
    Retrieves a parameter from a Revit element by its name.

    Args:
        element (DB.Element): The Revit element from which to retrieve the parameter.
        param_name (str): The name of the parameter to retrieve.
        default: The value to return if the parameter is not found or an error occurs. Defaults to None.

    Returns:
        The parameter if found, otherwise the default value.
    """
    if isinstance(element, DB.Element):
        try:
            return element.LookupParameter(param_name)
        except Exception:
            return default


def get_mark(element):
    """
    Retrieves the 'Mark' parameter value from a given Revit element.

    Args:
        element: The Revit element from which to retrieve the 'Mark' parameter.

    Returns:
        str: The value of the 'Mark' parameter as a string.
    Returns an empty string if the parameter is not found.
    """
    mparam = element.Parameter[DB.BuiltInParameter.ALL_MODEL_MARK]
    return mparam.AsString() if mparam else ""


def get_location(element):
    """Get element location point.


    Args:
        element (DB.Element): source element


    Returns:
        (DB.XYZ): X, Y, Z of location point element
    """
    locp = element.Location.Point
    return (locp.X, locp.Y, locp.Z)


def get_biparam_stringequals_filter(bip_paramvalue_dict):
    """
    Creates a Revit ElementParameterFilter based on a dictionary of built-in parameter (BIP)
    values and their corresponding filter values.

    Args:
        bip_paramvalue_dict (dict): A dictionary where keys are built-in parameter (BIP)
                                    identifiers and values are the corresponding filter values.

    Returns:
        DB.ElementParameterFilter: A filter that can be used to filter Revit elements based
                                   on the specified BIP values.

    Raises:
        PyRevitException: If no filters could be created from the provided dictionary.

    Notes:
        - The function handles different Revit API versions by checking if the host application
          is newer than the 2022 version.
        - For Revit versions newer than 2022, the `FilterStringRule` does not require the
          `caseSensitive` parameter.
    """
    filters = []
    for bip, fvalue in bip_paramvalue_dict.items():
        bip_id = DB.ElementId(bip)
        bip_valueprovider = DB.ParameterValueProvider(bip_id)
        if HOST_APP.is_newer_than(2022):
            bip_valuerule = DB.FilterStringRule(
                bip_valueprovider, DB.FilterStringEquals(), fvalue
            )
        else:
            bip_valuerule = DB.FilterStringRule(
                bip_valueprovider, DB.FilterStringEquals(), fvalue, True
            )
        filters.append(bip_valuerule)

    if filters:
        return DB.ElementParameterFilter(framework.List[DB.FilterRule](filters))
    else:
        raise PyRevitException("Error creating filters.")


def get_all_elements(doc=None):
    """
    Retrieves all elements from the given Revit document.
    This function uses a FilteredElementCollector to collect all elements
    in the provided document, including both element types and instances.

    Args:
        doc (Document, optional): The Revit document to collect elements from.
                                  If not provided, the default document (DOCS.doc) is used.

    Returns:
        List[Element]: A list of all elements in the document.
    """
    return (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .WherePasses(
            DB.LogicalOrFilter(
                DB.ElementIsElementTypeFilter(False),
                DB.ElementIsElementTypeFilter(True),
            )
        )
        .ToElements()
    )


def get_all_elements_in_view(view):
    """
    Retrieves all elements in the specified Revit view.

    Args:
        view (Autodesk.Revit.DB.View): The Revit view from which to collect elements.

    Returns:
        list[Autodesk.Revit.DB.Element]: A list of elements present in the specified view.
    """
    return (
        DB.FilteredElementCollector(view.Document, view.Id)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_param_value(targetparam):
    """
    Retrieves the value of a given Revit parameter.
    Parameters:
    targetparam (DB.Parameter or DB.GlobalParameter): The parameter whose value is to be retrieved.

    Returns:
    value (varies): The value of the parameter. The type of the returned value depends on the storage type of the parameter:
        - Double:
    Returns a float.
        - Integer:
    Returns an int.
        - String:
    Returns a str.
        - ElementId:
    Returns an ElementId.
        If the parameter is a GlobalParameter, returns the value directly from the GlobalParameter.
    """
    value = None
    if isinstance(targetparam, DB.Parameter):
        if targetparam.StorageType == DB.StorageType.Double:
            value = targetparam.AsDouble()
        elif targetparam.StorageType == DB.StorageType.Integer:
            value = targetparam.AsInteger()
        elif targetparam.StorageType == DB.StorageType.String:
            value = targetparam.AsString()
        elif targetparam.StorageType == DB.StorageType.ElementId:
            value = targetparam.AsElementId()
    elif isinstance(targetparam, DB.GlobalParameter):
        return targetparam.GetValue().Value
    return value


def get_value_range(param_name, doc=None):
    """
    Retrieves a set of unique values for a specified parameter from all elements in the given Revit document.

    Args:
        param_name (str): The name of the parameter to retrieve values for.
        doc (Document, optional): The Revit document to search within. If None, the current document is used.

    Returns:
        set: A set of unique values for the specified parameter. The values can be of any type, but are typically strings.
    """
    values = set()
    for element in get_all_elements(doc):
        targetparam = element.LookupParameter(param_name)
        if targetparam:
            value = get_param_value(targetparam)
            if value is not None and safe_strtype(value).lower() != "none":
                if isinstance(value, str) and not value.isspace():
                    values.add(value)
                else:
                    values.add(value)
    return values


def get_elements_by_parameter(param_name, param_value, doc=None, partial=False):
    """
    Retrieves elements from the Revit document that match a given parameter name and value.

    Args:
        param_name (str): The name of the parameter to search for.
        param_value (str or other): The value of the parameter to match.
        doc (Document, optional): The Revit document to search in. If None, the current document is used.
        partial (bool, optional): If True, performs a partial match on string parameter values. Defaults to False.

    Returns:
        list: A list of elements that match the specified parameter name and value.
    """
    found_els = []
    for element in get_all_elements(doc):
        targetparam = element.LookupParameter(param_name)
        if targetparam:
            value = get_param_value(targetparam)
            if (
                partial
                and value is not None
                and isinstance(value, str)
                and param_value in value
            ):
                found_els.append(element)
            elif param_value == value:
                found_els.append(element)
    return found_els


def get_elements_by_param_value(param_name, param_value, inverse=False, doc=None):
    """
    Retrieves elements from the Revit document based on a parameter name and value.

    Args:
        param_name (str): The name of the parameter to filter by.
        param_value (str): The value of the parameter to filter by.
        inverse (bool, optional): If True, inverts the filter to exclude elements with the specified parameter value. Defaults to False.
        doc (Document, optional): The Revit document to search in. If None, uses the default document.

    Returns:
        list: A list of elements that match the parameter name and value.
    """
    doc = doc or DOCS.doc
    param_id = get_project_parameter_id(param_name, doc)
    if param_id:
        pvprov = DB.ParameterValueProvider(param_id)
        pfilter = DB.FilterStringEquals()
        if HOST_APP.is_newer_than(2022):
            vrule = DB.FilterStringRule(pvprov, pfilter, param_value)
        else:
            vrule = DB.FilterStringRule(pvprov, pfilter, param_value, True)
        if inverse:
            vrule = DB.FilterInverseRule(vrule)
        param_filter = DB.ElementParameterFilter(vrule)
        return DB.FilteredElementCollector(doc).WherePasses(param_filter).ToElements()
    else:
        return []


def get_elements_by_categories(element_bicats, elements=None, doc=None):
    """
    Retrieves elements from a Revit document based on specified categories.

    Args:
        element_bicats (list): A list of built-in categories to filter elements by.
        elements (list, optional): A list of elements to filter. If provided, the function will filter these elements.
        doc (DB.Document, optional): The Revit document to collect elements from. If not provided, the active document is used.

    Returns:
        list: A list of elements that belong to the specified categories.
    """
    if elements:
        return [
            x
            for x in elements
            if get_builtincategory(x.Category.Name) in element_bicats
        ]
    cat_filters = [DB.ElementCategoryFilter(x) for x in element_bicats if x]
    elcats_filter = DB.LogicalOrFilter(framework.List[DB.ElementFilter](cat_filters))
    return (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .WherePasses(elcats_filter)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_elements_by_class(element_class, elements=None, doc=None, view_id=None):
    """
    Retrieves elements of a specified class from a Revit document or a given list of elements.

    Args:
        element_class (type): The class type of the elements to retrieve.
        elements (list, optional): A list of elements to filter by the specified class. Defaults to None.
        doc (DB.Document, optional): The Revit document to search within. Defaults to None.
        view_id (DB.ElementId, optional): The ID of the view to restrict the search to. Defaults to None.

    Returns:
        list: A list of elements of the specified class.
    """
    if elements:
        return [x for x in elements if isinstance(x, element_class)]
    if view_id:
        return (
            DB.FilteredElementCollector(doc or DOCS.doc, view_id)
            .OfClass(element_class)
            .WhereElementIsNotElementType()
            .ToElements()
        )
    else:
        return (
            DB.FilteredElementCollector(doc or DOCS.doc)
            .OfClass(element_class)
            .WhereElementIsNotElementType()
            .ToElements()
        )


def get_types_by_class(type_class, types=None, doc=None):
    """
    Retrieves elements of a specified class type from a given list or from the Revit document.

    Args:
        type_class (type): The class type to filter elements by.
        types (list, optional): A list of elements to filter. If not provided, elements will be collected from the Revit document.
        doc (Document, optional): The Revit document to collect elements from if 'types' is not provided. Defaults to the active document.

    Returns:
        list: A list of elements that are instances of the specified class type.
    """
    if types:
        return [x for x in types if isinstance(x, type_class)]
    return DB.FilteredElementCollector(doc or DOCS.doc).OfClass(type_class).ToElements()


def get_family(family_name, doc=None):
    """
    Retrieves all family elements in the Revit document that match the given family name.

    Args:
        family_name (str): The name of the family to search for.
        doc (DB.Document, optional): The Revit document to search in. If not provided, the current document is used.

    Returns:
        list[DB.Element]: A list of family elements that match the given family name.
    """
    families = (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .WherePasses(
            get_biparam_stringequals_filter(
                {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name}
            )
        )
        .WhereElementIsElementType()
        .ToElements()
    )
    return families


def get_family_symbol(family_name, symbol_name, doc=None):
    """
    Retrieves family symbols from a Revit document based on the specified family name and symbol name.

    Args:
        family_name (str): The name of the family to search for.
        symbol_name (str): The name of the symbol within the family to search for.
        doc (DB.Document, optional): The Revit document to search in. If not provided, the default document is used.

    Returns:
        list[DB.Element]: A list of family symbols that match the specified family name and symbol name.
    """
    famsyms = (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .WherePasses(
            get_biparam_stringequals_filter(
                {
                    DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name,
                    DB.BuiltInParameter.SYMBOL_NAME_PARAM: symbol_name,
                }
            )
        )
        .WhereElementIsElementType()
        .ToElements()
    )
    return famsyms


def get_families(doc=None, only_editable=True):
    """
    Retrieves a list of families from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve families from.
                                  If not provided, defaults to DOCS.doc.
        only_editable (bool, optional): If True, only returns families that are editable.
                                        Defaults to True.

    Returns:
        list: A list of Family objects from the document. If only_editable is True,
              only includes families that are editable.
    """
    doc = doc or DOCS.doc
    families = [
        x.Family
        for x in set(
            DB.FilteredElementCollector(doc).WhereElementIsElementType().ToElements()
        )
        if isinstance(x, (DB.FamilySymbol, DB.AnnotationSymbolType))
    ]
    if only_editable:
        return [x for x in families if x.IsEditable]
    return families


def get_noteblock_families(doc=None):
    """
    Retrieves a list of noteblock families from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to query. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        list: A list of noteblock family elements in the document.
    """
    doc = doc or DOCS.doc
    return [
        doc.GetElement(x) for x in DB.ViewSchedule.GetValidFamiliesForNoteBlock(doc)
    ]


def get_elements_by_family(family_name, doc=None):
    """
    Retrieves elements from a Revit document based on the specified family name.

    Args:
        family_name (str): The name of the family to filter elements by.
        doc (DB.Document, optional): The Revit document to search within. If not provided,
                                     the default document (DOCS.doc) will be used.

    Returns:
        list[DB.Element]: A list of elements that belong to the specified family.
    """
    famsyms = (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .WherePasses(
            get_biparam_stringequals_filter(
                {DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name}
            )
        )
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return famsyms


def get_elements_by_familytype(family_name, symbol_name, doc=None):
    """
    Retrieves elements from a Revit document based on the specified family and symbol names.

    Args:
        family_name (str): The name of the family to filter elements by.
        symbol_name (str): The name of the symbol (type) to filter elements by.
        doc (DB.Document, optional): The Revit document to search in. If not provided, the current document is used.

    Returns:
        list[DB.Element]: A list of elements that match the specified family and symbol names.
    """
    syms = (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .WherePasses(
            get_biparam_stringequals_filter(
                {
                    DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM: family_name,
                    DB.BuiltInParameter.SYMBOL_NAME_PARAM: symbol_name,
                }
            )
        )
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return syms


def find_workset(workset_name_or_list, doc=None, partial=True):
    """
    Finds a workset in the given Revit document by name or list of names.

    Args:
        workset_name_or_list (str or list): The name of the workset to find or a list of workset names.
        doc (Document, optional): The Revit document to search in. If None, the default document is used.
        partial (bool, optional): If True, allows partial matching of workset names. Defaults to True.

    Returns:
        Workset: The first matching workset found, or None if no match is found.
    """
    workset_clctr = DB.FilteredWorksetCollector(doc or DOCS.doc).ToWorksets()
    if isinstance(workset_name_or_list, list):
        for workset in workset_clctr:
            for workset_name in workset_name_or_list:
                if workset_name in workset.Name:
                    return workset
    elif isinstance(workset_name_or_list, str):
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
    """
    Checks if the Revit model contains a family with the given name.

    Args:
        family_name (str): The name of the family to search for.
        doc (Document, optional): The Revit document to search in. If None, the current document is used.

    Returns:
        bool: True if the family is found in the model, False otherwise.
    """
    collector = get_family(family_name, doc=doc)
    return hasattr(collector, "Count") and collector.Count > 0


def model_has_workset(workset_name, partial=False, doc=None):
    """
    Checks if the model has a workset with the given name.

    Args:
        workset_name (str): The name of the workset to search for.
        partial (bool, optional): If True, allows partial matching of the workset name. Defaults to False.
        doc (Document, optional): The Revit document to search within. If None, the current document is used. Defaults to None.

    Returns:
        bool: True if the workset is found, False otherwise.
    """

    return find_workset(workset_name, partial=partial, doc=doc)


def get_worksets_names(doc=None):
    """

    Returns a string with the names of all user worksets in a document


    Args:
        document (Document): A Revit document. de


    Returns:
        str: A string with the names of all user worksets in a document.
    """
    doc = doc or DOCS.doc
    if not hasattr(doc, "IsWorkshared"):
        return "-"
    if not doc.IsWorkshared:
        return "Not Workshared"
    worksets_collection = (
        DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset).ToWorksets()
    )
    return ", ".join(w.Name for w in worksets_collection)


def get_critical_warnings_count(warnings, critical_warnings_template):
    """
    Counts the number of critical warnings from a list of warnings based on a template.

    Args:
        warnings (list): A list of warning objects. Each warning object should have a method
                         `GetFailureDefinitionId` that returns an object with a `Guid` attribute.
        critical_warnings_template (list): A list of string representations of GUIDs that are
                                           considered critical warnings.

    Returns:
        int: The count of critical warnings.
    """
    warnings_guid = [warning.GetFailureDefinitionId().Guid for warning in warnings]
    return sum(
        1
        for warning_guid in warnings_guid
        if str(warning_guid) in critical_warnings_template
    )


def get_sharedparam_definition_file():
    """
    Retrieves the shared parameters definition file from the host application.

    Returns:
        SharedParameterFile: The shared parameters file if it exists and is successfully opened.

    Raises:
        PyRevitException: If the shared parameters file is not defined or cannot be opened.
    """
    if HOST_APP.app.SharedParametersFilename:
        sparamf = HOST_APP.app.OpenSharedParameterFile()
        if sparamf:
            return sparamf
        else:
            raise PyRevitException("Failed opening Shared Parameters file.")
    else:
        raise PyRevitException("No Shared Parameters file defined.")


def get_defined_sharedparams():
    """
    Retrieves all defined shared parameters from the shared parameter file.

    Returns:
        list: A list of DB.ExternalDefinition objects representing the shared parameters.

    Raises:
        PyRevitException: If there is an error accessing the shared parameter file.
    """
    pp_list = []
    try:
        for def_group in get_sharedparam_definition_file().Groups:
            pp_list.extend([x for x in def_group.Definitions])
    except PyRevitException as ex:
        mlogger.debug("Error getting shared parameters. | %s", ex)
    return pp_list


def iter_project_parameters(doc=None):
    """
    Generator that yields project parameters from the given Revit document one at a time.

    Args:
        doc (Document, optional): The Revit document from which to retrieve the project parameters.
                                  If not provided, defaults to `DOCS.doc`.

    Yields:
        ProjectParameter: Individual ProjectParameter objects representing the project parameters in the document.
    """
    doc = doc or DOCS.doc

    # Build shared params dictionary more explicitly to avoid IronPython issues
    shared_params = {}
    try:
        defined_shared_params = get_defined_sharedparams()
        for param in defined_shared_params:
            shared_params[param.Name] = param
    except Exception:
        # If shared params can't be loaded, continue with empty dict
        pass

    if doc and not doc.IsFamilyDocument:
        param_bindings = doc.ParameterBindings
        pb_iterator = param_bindings.ForwardIterator()
        pb_iterator.Reset()
        while pb_iterator.MoveNext():
            key = pb_iterator.Key
            binding = param_bindings[key]
            param_ext_def = shared_params.get(key.Name, None)

            msp = db.ProjectParameter(
                key,
                binding,
                param_ext_def=param_ext_def,
            )
            yield msp


def get_project_parameters(doc=None):
    """
    Retrieves the project parameters from the given Revit document.

    Args:
        doc (Document, optional): The Revit document from which to retrieve the project parameters.
                                  If not provided, defaults to `DOCS.doc`.

    Returns:
        list: A list of ProjectParameter objects representing the project parameters in the document.
    """
    return list(iter_project_parameters(doc))


def get_project_parameter_id(param_name, doc=None):
    """
    Retrieves the ID of a project parameter by its name.

    Args:
        param_name (str): The name of the project parameter to find.
        doc (Document, optional): The Revit document to search in. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        ElementId: The ID of the project parameter.

    Raises:
        PyRevitException: If the parameter with the specified name is not found.
    """
    doc = doc or DOCS.doc
    for project_param in iter_project_parameters(doc):
        if project_param.name == param_name:
            return project_param.param_id
    raise PyRevitException("Parameter not found: {}".format(param_name))


def get_project_parameter(param_id_or_name, doc=None):
    """
    Retrieves a project parameter by its ID or name.

    Args:
        param_id_or_name (str or int): The ID or name of the project parameter to retrieve.
        doc (Document, optional): The Revit document to search in. If not provided, the default document is used.

    Returns:
        ProjectParameter: The matching project parameter if found, otherwise None.
    """
    for msp in iter_project_parameters(doc or DOCS.doc):
        if msp == param_id_or_name:
            return msp
    return None


def model_has_parameter(param_id_or_name, doc=None):
    """
    Checks if the model has a specific parameter by its ID or name.

    Args:
        param_id_or_name (str or int): The parameter ID or name to check for.
        doc (Document, optional): The Revit document to search in. If None, the current document is used.

    Returns:
        bool: True if the parameter exists in the model, False otherwise.
    """
    return get_project_parameter(param_id_or_name, doc=doc) is not None


def get_global_parameters(doc=None):
    """
    Retrieves all global parameters from the given Revit document.

    Args:
        doc (Document, optional): The Revit document from which to retrieve global parameters.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of global parameter elements in the document.
    """
    doc = doc or DOCS.doc
    return [
        doc.GetElement(x)
        for x in DB.GlobalParametersManager.GetAllGlobalParameters(doc)
    ]


def get_global_parameter(param_name, doc=None):
    """
    Retrieves a global parameter by its name from the given Revit document.

    Args:
        param_name (str): The name of the global parameter to retrieve.
        doc (DB.Document, optional): The Revit document to search in. If not provided, defaults to DOCS.doc.

    Returns:
        DB.GlobalParameter: The global parameter element if found, otherwise None.
    """
    doc = doc or DOCS.doc
    if features.GLOBAL_PARAMS:
        param_id = DB.GlobalParametersManager.FindByName(doc, param_name)
        if param_id != DB.ElementId.InvalidElementId:
            return doc.GetElement(param_id)


def get_project_info(doc=None):
    """
    Retrieves the project information from the given Revit document.

    Args:
        doc (Document, optional): The Revit document from which to retrieve the project information.
                                  If not provided, the default document (DOCS.doc) will be used.

    Returns:
        ProjectInfo: The project information of the specified or default Revit document.
    """
    return db.ProjectInfo(doc or DOCS.doc)


def get_phases_names(doc=None):
    """

    Returns a comma-separated list of the names of the phases in a project.


    Args:
        document (Document): A Revit document.


    Returns:
        str: A comma-separated list of the names of the phases in a project.
    """
    if not hasattr(doc, "Phases"):
        return "-"
    return ", ".join(phase.Name for phase in doc.Phases)


def get_revisions(doc=None):
    """
    Retrieves a list of revision elements from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve revisions from.
                                  If not provided, the default document (DOCS.doc) is used.

    Returns:
        list: A list of revision elements in the specified Revit document.
    """
    return list(
        DB.FilteredElementCollector(doc or DOCS.doc)
        .OfCategory(DB.BuiltInCategory.OST_Revisions)
        .WhereElementIsNotElementType()
    )


def get_sheet_revisions(sheet):
    """
    Retrieves the revisions associated with a given Revit sheet.

    Args:
        sheet (Autodesk.Revit.DB.ViewSheet): The Revit sheet from which to retrieve revisions.

    Returns:
        list[Autodesk.Revit.DB.Element]: A list of revision elements associated with the sheet.
    """
    doc = sheet.Document
    return [doc.GetElement(x) for x in sheet.GetAdditionalRevisionIds()]


def get_current_sheet_revision(sheet):
    """
    Retrieves the current revision of the given sheet.

    Args:
        sheet (Autodesk.Revit.DB.ViewSheet): The sheet for which to get the current revision.

    Returns:
        Autodesk.Revit.DB.Element: The current revision element of the sheet.
    """
    doc = sheet.Document
    return doc.GetElement(sheet.GetCurrentRevision())


def get_sheets(include_placeholders=True, include_noappear=True, doc=None):
    """
    Retrieves a list of sheets from the Revit document.

    Args:
        include_placeholders (bool, optional): If True, includes placeholder sheets in the result. Defaults to True.
        include_noappear (bool, optional): If True, includes sheets that do not appear in the project browser. Defaults to True.
        doc (Document, optional): The Revit document to retrieve sheets from. If None, uses the current document. Defaults to None.

    Returns:
        list: A list of sheets from the specified Revit document.
    """
    sheets = list(
        DB.FilteredElementCollector(doc or DOCS.doc)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
    )
    if not include_noappear:
        sheets = [
            x
            for x in sheets
            if x.Parameter[DB.BuiltInParameter.SHEET_SCHEDULED].AsInteger() > 0
        ]
    if not include_placeholders:
        return [x for x in sheets if not x.IsPlaceholder]

    return sheets


def get_document_clean_name(doc=None):
    """
    Return the name of the given document without the file path or file
    extension.

    Args:
        doc (DB.Document, optional): The Revit document to retrieve links from. If None, the default document
            (DOCS.doc) is used. Defaults to None.

    Returns:
        str: The name of the given document without the file path or file
        extension.
    """
    document_name = db.ProjectInfo(doc or DOCS.doc).path
    if not document_name:
        return "File Not Saved"
    if document_name.startswith("BIM 360://"):
        path = document_name.split("://", 1)[1]
    else:
        path = document_name
    return splitext(basename(path))[0]


def get_links(linktype=None, doc=None):
    """
    Retrieves external file references (links) from a Revit document.

    Args:
        linktype (DB.ExternalFileReferenceType, optional): The type of external file reference to filter by.
            If None, all external file references are returned. Defaults to None.
        doc (DB.Document, optional): The Revit document to retrieve links from. If None, the default document
            (DOCS.doc) is used. Defaults to None.

    Returns:
        list: A list of db.ExternalRef objects representing the external file references in the document.

    Raises:
        PyRevitException: If the document is not saved or if there is an error reading the links from the model path.
    """
    doc = doc or DOCS.doc
    location = doc.PathName
    if not location:
        raise PyRevitException("PathName is empty. Model is not saved.")
    links = []
    model_path = DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
    if not model_path:
        raise PyRevitException("Model is not saved. Can not read links.")
    try:
        trans_data = DB.TransmissionData.ReadTransmissionData(model_path)
        external_refs = trans_data.GetAllExternalFileReferenceIds()
        for ref_id in external_refs:
            ext_ref = trans_data.GetLastSavedReferenceData(ref_id)
            link = doc.GetElement(ref_id)
            if linktype:
                if ext_ref.ExternalFileReferenceType == linktype:
                    links.append(db.ExternalRef(link, ext_ref))
            else:
                links.append(db.ExternalRef(link, ext_ref))
        return links
    except Exception as data_err:
        raise PyRevitException(
            "Error reading links from model path: {} | {}".format(model_path, data_err)
        )


def get_linked_models(doc=None, loaded_only=False):
    """
    Retrieves the linked Revit models in the given document.

    Args:
        doc (Document, optional): The Revit document to search for linked models.
                                  If None, defaults to DOCS.doc.
        loaded_only (bool, optional): If True, only returns the linked models that are currently loaded.
                                      Defaults to False.

    Returns:
        list: A list of linked Revit models. If loaded_only is True, only the loaded models are returned.
    """
    doc = doc or DOCS.doc
    linkedmodels = get_links(linktype=DB.ExternalFileReferenceType.RevitLink, doc=doc)
    if loaded_only:
        return [x for x in linkedmodels if DB.RevitLinkType.IsLoaded(doc, x.id)]

    return linkedmodels


def get_linked_model_doc(linked_model):
    """
    Retrieves the document of a linked Revit model.

    Args:
        linked_model (Union[DB.RevitLinkType, db.ExternalRef]): The linked model, which can be either a RevitLinkType or an ExternalRef.

    Returns:
        Document: The document of the linked model if found, otherwise None.
    """
    lmodel = None
    if isinstance(linked_model, DB.RevitLinkType):
        lmodel = db.ExternalRef(linked_model)  # pylint: disable=E1120
    elif isinstance(linked_model, db.ExternalRef):
        lmodel = linked_model

    if lmodel:
        for open_doc in DOCS.docs:
            if open_doc.Title == lmodel.name:
                return open_doc


def get_linked_model_types(doc, rvt_links_instances):
    """
    Retrieves the types of linked Revit models.
    Args:
        doc (Document): The Revit document. Defaults to None.
        rvt_links_instances (list): A list of Revit link instances.
    Returns:
        list: A list of linked model types.
    """
    return [doc.GetElement(rvtlink.GetTypeId()) for rvtlink in rvt_links_instances]


def get_linked_model_instances(doc=None):
    """
    Returns a list of all rvt_links instances in a document

    Args:
        doc (Document): A Revit document.

    Returns:
        list: A list of Revit link instances.
    """
    return (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .OfCategory(DB.BuiltInCategory.OST_RvtLinks)
        .WhereElementIsNotElementType()
    )


def get_rvt_link_status(doc=None):
    """
    Retrieves the status of linked Revit models in the given document.

    Args:
        doc (Document, optional): The Revit document to query. If None, the current document is used.

    Returns:
        list: A list of statuses for each linked Revit model type.
    """
    doc = doc or DOCS.doc
    rvtlinks_instances = get_linked_model_instances(doc)
    rvtlinks_types = get_linked_model_types(doc, rvtlinks_instances)
    return [rvtlinktype.GetLinkedFileStatus() for rvtlinktype in rvtlinks_types]


def get_rvt_link_doc_name(rvtlink_instance):
    """
    Retrieves the name of the Revit link document from the given Revit link instance.

    Args:
        rvtlink_instance: The Revit link instance from which to extract the document name.

    Returns:
        str: The name of the Revit link document, without the file extension and any directory paths.
    """
    return get_name(rvtlink_instance).split("\\")[0].split(".rvt")[0]


def get_rvt_link_instance_name(rvtlink_instance=None):
    """
    Retrieves the name of a Revit link instance.

    Args:
        rvtlink_instance: The Revit link instance object.

    Returns:
        str: The name of the Revit link instance, extracted from the full name.
    """
    return get_name(rvtlink_instance).split(" : ")[1]


def find_first_legend(doc=None):
    """
    Finds the first legend view in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to search in. If not provided,
                                  it defaults to DOCS.doc.

    Returns:
        View: The first legend view found in the document, or None if no legend view is found.
    """
    doc = doc or DOCS.doc
    for view in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if view.ViewType == DB.ViewType.Legend and not view.IsTemplate:
            return view
    return None


def compare_revisions(src_rev, dest_rev, case_sensitive=False):
    """
    Compare two revision objects based on specific attributes.

    Args:
        src_rev (object): The source revision object to compare.
        dest_rev (object): The destination revision object to compare.
        case_sensitive (bool, optional): Flag to indicate if the comparison should be case sensitive. Defaults to False.

    Returns:
        bool: True if all specified attributes match between the two revisions, False otherwise.
    """
    return all(
        db.BaseWrapper.compare_attrs(
            src_rev,
            dest_rev,
            ["RevisionDate", "Description", "IssuedBy", "IssuedTo"],
            case_sensitive=case_sensitive,
        )
    )


def get_all_views(doc=None, view_types=None, include_nongraphical=False):
    """
    Retrieves all views from the given Revit document, with optional filtering by view types and graphical views.

    Args:
        doc (Document, optional): The Revit document to retrieve views from. If None, defaults to DOCS.doc.
        view_types (list, optional): A list of view types to filter the views. If None, no filtering is applied.
        include_nongraphical (bool, optional): If True, includes non-graphical views in the result. Defaults to False.

    Returns:
        list: A list of views from the Revit document, filtered by the specified criteria.
    """
    doc = doc or DOCS.doc
    all_views = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.View)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    if view_types:
        all_views = [x for x in all_views if x.ViewType in view_types]
    if not include_nongraphical:
        return [
            x
            for x in all_views
            if x.ViewType in GRAPHICAL_VIEWTYPES
            and not x.IsTemplate
            and not x.ViewSpecific
        ]
    return all_views


def get_all_view_templates(doc=None, view_types=None):
    """
    Retrieves all view templates from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to search for view templates.
                                  If None, the active document will be used.
        view_types (list, optional): A list of view types to filter the views.
                                     If None, all view types will be considered.

    Returns:
        list: A list of view templates found in the document.
    """
    return [
        x
        for x in get_all_views(
            doc=doc, view_types=view_types, include_nongraphical=True
        )
        if x.IsTemplate
    ]


def get_sheet_by_number(sheet_num, doc=None):
    """
    Retrieves a sheet from the document by its sheet number.

    Args:
        sheet_num (str): The sheet number to search for.
        doc (Document, optional): The Revit document to search within.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        Element: The sheet element with the specified sheet number,
                 or None if no matching sheet is found.
    """
    doc = doc or DOCS.doc
    return next((x for x in get_sheets(doc=doc) if x.SheetNumber == sheet_num), None)


def get_viewport_by_number(sheet_num, detail_num, doc=None):
    """
    Retrieves a viewport from a Revit document based on the sheet number and detail number.

    Args:
        sheet_num (str): The number of the sheet containing the viewport.
        detail_num (str): The detail number of the viewport to retrieve.
        doc (Document, optional): The Revit document to search in. If not provided, defaults to DOCS.doc.

    Returns:
        Element: The viewport element if found, otherwise None.
    """
    doc = doc or DOCS.doc
    sheet = get_sheet_by_number(sheet_num, doc=doc)
    if sheet:
        vps = [doc.GetElement(x) for x in sheet.GetAllViewports()]
        for vp in vps:
            det_num = vp.Parameter[
                DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER
            ].AsString()
            if det_num == detail_num:
                return vp


def get_view_by_sheetref(sheet_num, detail_num, doc=None):
    """
    Retrieves the view ID associated with a given sheet number and detail number.

    Args:
        sheet_num (int): The sheet number to search for.
        detail_num (int): The detail number to search for.
        doc (Document, optional): The Revit document to search within. If not provided, defaults to DOCS.doc.

    Returns:
        ElementId: The ID of the view associated with the specified sheet and detail numbers, or None if not found.
    """
    doc = doc or DOCS.doc
    vport = get_viewport_by_number(sheet_num, detail_num, doc=doc)
    if vport:
        return vport.ViewId


def is_schedule(view):
    """
    Determines if the given view is a schedule that is not a template,
    title block revision schedule, internal keynote schedule, or keynote legend.

    Args:
        view (DB.View): The Revit view to check.

    Returns:
        bool: True if the view is a schedule and not one of the excluded types, False otherwise.
    """
    if isinstance(view, DB.ViewSchedule) and not view.IsTemplate:
        isrevsched = view.IsTitleblockRevisionSchedule
        isintkeynote = view.IsInternalKeynoteSchedule
        iskeynotelegend = (
            view.Definition.CategoryId
            == get_category(DB.BuiltInCategory.OST_KeynoteTags, view.Document).Id
        )

        return not (isrevsched or isintkeynote or iskeynotelegend)
    return False


def get_all_schedules(doc=None):
    """
    Retrieves all schedule views from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve schedules from.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        filter: A filter object containing all schedule views in the document.
    """
    doc = doc or DOCS.doc
    all_scheds = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ViewSchedule)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return filter(is_schedule, all_scheds)


def get_view_by_name(view_name, view_types=None, doc=None):
    """
    Retrieves a Revit view by its name.

    Args:
        view_name (str): The name of the view to retrieve.
        view_types (list, optional): A list of view types to filter the search. Defaults to None.
        doc (Document, optional): The Revit document to search within. Defaults to the active document.

    Returns:
        View: The Revit view that matches the given name, or None if no match is found.
    """
    doc = doc or DOCS.doc
    for view in get_all_views(doc=doc, view_types=view_types):
        if get_name(view) == view_name:
            return view


def get_all_referencing_elements(doc=None):
    """
    Retrieves all elements in the given Revit document that reference views.
    This function collects all elements in the provided Revit document that are not element types,
    belong to a category, are instances of DB.Element, and whose category is in the predefined
    set of view-related built-in categories.

    Args:
        doc (DB.Document, optional): The Revit document to search for referencing elements.
                                     If not provided, defaults to DOCS.doc.

    Returns:
        list[DB.ElementId]: A list of element IDs that reference views in the document.
    """
    doc = doc or DOCS.doc
    all_referencing_elements = []
    for el in (
        DB.FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements()
    ):
        if (
            el.Category
            and isinstance(el, DB.Element)
            and get_builtincategory(el.Category) in BUILTINCATEGORIES_VIEW
        ):
            all_referencing_elements.append(el.Id)
    return all_referencing_elements


def get_all_referencing_elements_in_view(view):
    """
    Retrieves all elements in the given view that reference other elements.

    Args:
        view (DB.View): The Revit view from which to collect referencing elements.

    Returns:
        list[DB.ElementId]: A list of element IDs that reference other elements in the view.
    """
    all_referencing_elements_in_view = []
    for el in (
        DB.FilteredElementCollector(view.Document, view.Id)
        .WhereElementIsNotElementType()
        .ToElements()
    ):
        if (
            el.Category
            and isinstance(el, DB.Element)
            and get_builtincategory(el.Category) in BUILTINCATEGORIES_VIEW
        ):
            all_referencing_elements_in_view.append(el.Id)
    return all_referencing_elements_in_view


def get_schedules_on_sheet(viewsheet, doc=None):
    """
    Retrieves all schedule instances placed on a given Revit view sheet.

    Args:
        viewsheet (DB.ViewSheet): The Revit view sheet from which to retrieve schedule instances.
        doc (DB.Document, optional): The Revit document. If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of schedule instances (DB.ScheduleSheetInstance) that are placed on the given view sheet,
              excluding title block revision schedules.
    """
    doc = doc or DOCS.doc
    all_sheeted_scheds = (
        DB.FilteredElementCollector(doc).OfClass(DB.ScheduleSheetInstance).ToElements()
    )
    return [
        x
        for x in all_sheeted_scheds
        if x.OwnerViewId == viewsheet.Id
        and not doc.GetElement(x.ScheduleId).IsTitleblockRevisionSchedule
    ]


def get_schedules_instances(doc=None):
    """
    Retrieves all schedule instances placed on sheets.

    Args:
        doc (Document, optional): The Revit document to search within. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        List[ScheduleSheetInstance]: A list of ScheduleSheetInstance elements.
    """
    return (
        DB.FilteredElementCollector(doc or DOCS.doc)
        .OfClass(DB.ScheduleSheetInstance)
        .ToElements()
    )


def is_sheet_empty(viewsheet):
    """
    Checks if a given Revit sheet is empty.

    Args:
        viewsheet: The Revit sheet to check.

    Returns:
        bool: True if the sheet has no viewports or schedules, False otherwise.
    """
    sheet_views = viewsheet.GetAllViewports()
    sheet_scheds = get_schedules_on_sheet(viewsheet, doc=viewsheet.Document)
    if sheet_views or sheet_scheds:
        return False
    return True


def get_doc_categories(doc=None, include_subcats=True):
    """
    Retrieves all categories from the given Revit document, optionally including subcategories.

    Args:
        doc (Document, optional): The Revit document from which to retrieve categories.
                                  If not provided, defaults to DOCS.doc.
        include_subcats (bool, optional): Whether to include subcategories in the result.
                                          Defaults to True.

    Returns:
        list: A list of all categories (and subcategories, if include_subcats is True) in the document.
    """
    doc = doc or DOCS.doc
    all_cats = []
    cats = doc.Settings.Categories
    all_cats.extend(cats)
    if include_subcats:
        for cat in cats:
            all_cats.extend([x for x in cat.SubCategories])
    return all_cats


def get_schedule_categories(doc=None):
    """
    Retrieves the categories that are valid for schedules in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve the schedule categories from.
                                  If not provided, it defaults to DOCS.doc.

    Returns:
        list: A list of categories that are valid for schedules in the given Revit document.
    """
    doc = doc or DOCS.doc
    all_cats = get_doc_categories(doc)
    cats = []
    for cat_id in DB.ViewSchedule.GetValidCategoriesForSchedule():
        for cat in all_cats:
            if cat.Id == cat_id:
                cats.append(cat)
    return cats


def get_key_schedule_categories(doc=None):
    """
    Retrieves the categories that are valid for key schedules in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve categories from.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of categories that are valid for key schedules.
    """
    doc = doc or DOCS.doc
    all_cats = get_doc_categories(doc)
    cats = []
    for cat_id in DB.ViewSchedule.GetValidCategoriesForKeySchedule():
        for cat in all_cats:
            if cat.Id == cat_id:
                cats.append(cat)
    return cats


def get_takeoff_categories(doc=None):
    """
    Retrieves the categories that are valid for material takeoff schedules in a given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve categories from. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        list: A list of categories that are valid for material takeoff schedules.
    """
    doc = doc or DOCS.doc
    all_cats = get_doc_categories(doc)
    cats = []
    for cat_id in DB.ViewSchedule.GetValidCategoriesForMaterialTakeoff():
        for cat in all_cats:
            if cat.Id == cat_id:
                cats.append(cat)
    return cats


def get_category(cat_name_or_builtin, doc=None):
    """
    Retrieves a Revit category based on the provided category name, built-in category, or category object.

    Args:
        cat_name_or_builtin (Union[str, DB.BuiltInCategory, DB.Category]): The category name as a string,
            a built-in category enum, or a category object.
        doc (Optional[Document]): The Revit document to search within. If not provided, defaults to DOCS.doc.

    Returns:
        DB.Category: The matching Revit category object, or None if no match is found.
    """
    doc = doc or DOCS.doc
    all_cats = get_doc_categories(doc)
    if isinstance(cat_name_or_builtin, str):
        for cat in all_cats:
            if cat.Name == cat_name_or_builtin:
                return cat
    elif isinstance(cat_name_or_builtin, DB.BuiltInCategory):
        get_elementid_value = get_elementid_value_func()
        for cat in all_cats:
            if get_elementid_value(cat.Id) == int(cat_name_or_builtin):
                return cat
    elif isinstance(cat_name_or_builtin, DB.Category):
        return cat_name_or_builtin


def get_builtincategory(cat_name_or_id, doc=None):
    """
    Retrieves the BuiltInCategory for a given category name or ElementId.

    Args:
        cat_name_or_id (str or DB.ElementId): The name of the category as a string or the ElementId of the category.
        doc (optional): The Revit document. If not provided, defaults to DOCS.doc.

    Returns:
        DB.BuiltInCategory: The corresponding BuiltInCategory if found, otherwise None.
    """
    doc = doc or DOCS.doc
    cat_id = None
    if isinstance(cat_name_or_id, str):
        cat = get_category(cat_name_or_id)
        if cat:
            cat_id = cat.Id
    elif isinstance(cat_name_or_id, DB.ElementId):
        cat_id = cat_name_or_id
    if cat_id:
        get_elementid_value = get_elementid_value_func()
        for bicat in DB.BuiltInCategory.GetValues(DB.BuiltInCategory):
            if int(bicat) == get_elementid_value(cat_id):
                return bicat


def get_subcategories(doc=None, purgable=False, filterfunc=None):
    """
    Retrieves subcategories from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve subcategories from.
                                  If None, defaults to DOCS.doc.
        purgable (bool, optional): If True, only includes subcategories that are purgable
                                   (element ID value greater than 1). Defaults to False.
        filterfunc (function, optional): A function to filter the subcategories.
                                         If provided, only subcategories that satisfy
                                         the filter function will be included.

    Returns:
        list: A list of subcategories from the given Revit document.
    """
    doc = doc or DOCS.doc
    # collect custom categories
    subcategories = []
    get_elementid_value = get_elementid_value_func()
    for cat in doc.Settings.Categories:
        for subcat in cat.SubCategories:
            if purgable:
                if get_elementid_value(subcat.Id) > 1:
                    subcategories.append(subcat)
            else:
                subcategories.append(subcat)
    if filterfunc:
        subcategories = filter(filterfunc, subcategories)
    return subcategories


def get_subcategory(cat_name_or_builtin, subcategory_name, doc=None):
    """
    Retrieves a subcategory from a given category in a Revit document.

    Args:
        cat_name_or_builtin (str or BuiltInCategory): The name of the category or a built-in category.
        subcategory_name (str): The name of the subcategory to retrieve.
        doc (Document, optional): The Revit document to search in. Defaults to the active document.

    Returns:
        Category: The subcategory if found, otherwise None.
    """
    doc = doc or DOCS.doc
    cat = get_category(cat_name_or_builtin)
    if cat:
        for subcat in cat.SubCategories:
            if subcat.Name == subcategory_name:
                return subcat


def get_builtinparameter(element, param_name, doc=None):
    """
    Retrieves the built-in parameter associated with a given element and parameter name.

    Args:
        element (Element): The Revit element from which to retrieve the parameter.
        param_name (str): The name of the parameter to look up.
        doc (Document, optional): The Revit document. If not provided, defaults to DOCS.doc.

    Returns:
        BuiltInParameter: The built-in parameter corresponding to the given element and parameter name.

    Raises:
        PyRevitException: If the parameter with the given name is not found.
    """
    doc = doc or DOCS.doc
    eparam = element.LookupParameter(param_name)
    if eparam:
        eparam_def_id = eparam.Definition.Id
        get_elementid_value = get_elementid_value_func()
        for biparam in DB.BuiltInParameter.GetValues(DB.BuiltInParameter):
            if int(biparam) == get_elementid_value(eparam_def_id):
                return biparam
    else:
        raise PyRevitException("Parameter not found: {}".format(param_name))


def get_view_cutplane_offset(view):
    """
    Retrieves the offset of the cut plane for a given Revit view.

    Args:
        view (Autodesk.Revit.DB.View): The Revit view from which to get the cut plane offset.

    Returns:
        float: The offset of the cut plane in the view.
    """
    viewrange = view.GetViewRange()
    return viewrange.GetOffset(DB.PlanViewPlane.CutPlane)


def get_project_location_transform(doc=None):
    """
    Retrieves the transformation matrix of the active project location in the given Revit document.

    Args:
        doc (Document, optional): The Revit document from which to get the project location transform.
                                  If not provided, it defaults to DOCS.doc.

    Returns:
        Transform: The transformation matrix of the active project location.
    """
    doc = doc or DOCS.doc
    return doc.ActiveProjectLocation.GetTransform()


def get_all_linkedmodels(doc=None):
    """
    Retrieves all linked Revit models in the given document.

    Args:
        doc (Document, optional): The Revit document to search for linked models.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        List[Element]: A list of RevitLinkType elements representing the linked models.
    """
    doc = doc or DOCS.doc
    return DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkType).ToElements()


def get_all_linkeddocs(doc=None):
    """
    Retrieves all linked documents in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to search for linked documents.
                                  If None, it defaults to DOCS.doc.

    Returns:
        list: A list of linked Revit documents.
    """
    doc = doc or DOCS.doc
    linkinstances = (
        DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
    )
    docs = [x.GetLinkDocument() for x in linkinstances]
    return [x for x in docs if x]


def get_all_grids(group_by_direction=False, include_linked_models=False, doc=None):
    """
    Retrieves all grid elements from the given Revit document and optionally from linked models.

    Args:
        group_by_direction (bool): If True, groups the grids by their direction.
        include_linked_models (bool): If True, includes grids from linked models.
        doc (Document, optional): The Revit document to retrieve grids from. If None, uses the current document.

    Returns:
        list or dict: A list of all grid elements if group_by_direction is False.
                      A dictionary grouping grid elements by their direction if group_by_direction is True.
    """
    doc = doc or DOCS.doc
    target_docs = [doc]
    if include_linked_models:
        target_docs.extend(get_all_linkeddocs())

    all_grids = []
    for tdoc in target_docs:
        if tdoc is not None:
            all_grids.extend(
                list(
                    DB.FilteredElementCollector(tdoc)
                    .OfCategory(DB.BuiltInCategory.OST_Grids)
                    .WhereElementIsNotElementType()
                    .ToElements()
                )
            )

    if group_by_direction:
        direcs = {db.XYZPoint(x.Curve.Direction) for x in all_grids}
        grouped_grids = {}
        for direc in direcs:
            grouped_grids[direc] = [
                x for x in all_grids if direc == db.XYZPoint(x.Curve.Direction)
            ]
        return grouped_grids
    return all_grids


def get_gridpoints(grids=None, include_linked_models=False, doc=None):
    """
    Retrieves the intersection points of grid lines in a Revit document.

    Args:
        grids (list, optional): A list of grid elements to consider. If None, all grids in the document are considered.
        include_linked_models (bool, optional): If True, includes grids from linked models. Defaults to False.
        doc (Document, optional): The Revit document to operate on. If None, uses the current active document.

    Returns:
        list: A list of GridPoint objects representing the intersection points of the grid lines.
    """
    doc = doc or DOCS.doc
    source_grids = grids or get_all_grids(
        doc=doc, include_linked_models=include_linked_models
    )
    gints = {}
    for grid1 in source_grids:
        for grid2 in source_grids:
            results = framework.clr.Reference[DB.IntersectionResultArray]()
            intres = grid1.Curve.Intersect(grid2.Curve, results)
            if intres == DB.SetComparisonResult.Overlap:
                gints[db.XYZPoint(results.get_Item(0).XYZPoint)] = [grid1, grid2]
    return [GridPoint(point=k, grids=v) for k, v in gints.items()]


def get_closest_gridpoint(element, gridpoints):
    """
    Finds the closest grid point to a given element.

    Args:
        element: The element for which the closest grid point is to be found.
                 It is expected to have a Location attribute with a Point property.
        gridpoints: A list of grid points. Each grid point is expected to have a
                    point attribute with an unwrap() method that returns an object
                    with a DistanceTo method.

    Returns:
        The grid point that is closest to the given element.
    """
    dist = (
        gridpoints[0].point.unwrap().DistanceTo(element.Location.Point),
        gridpoints[0],
    )
    for grid_point in gridpoints:
        gp_dist = grid_point.point.unwrap().DistanceTo(element.Location.Point)
        if gp_dist < dist[0]:
            dist = (gp_dist, grid_point)
    return dist[1]


def get_category_set(category_list, doc=None):
    """
    Creates a CategorySet from a list of built-in categories.

    Args:
        category_list (list): A list of built-in categories to include in the CategorySet.
        doc (Document, optional): The Revit document to use. If not provided, defaults to DOCS.doc.

    Returns:
        CategorySet: A set of categories created from the provided list.
    """
    doc = doc or DOCS.doc
    cat_set = HOST_APP.app.Create.NewCategorySet()
    for builtin_cat in category_list:
        cat = doc.Settings.Categories.get_Item(builtin_cat)
        cat_set.Insert(cat)
    return cat_set


def get_all_category_set(bindable=True, doc=None):
    """
    Retrieves a set of all categories in the Revit document.

    Args:
        bindable (bool, optional): If True, only includes categories that allow bound parameters. Defaults to True.
        doc (Document, optional): The Revit document to retrieve categories from. If None, uses the default document.

    Returns:
        CategorySet: A set of categories from the specified Revit document.
    """
    doc = doc or DOCS.doc
    cat_set = HOST_APP.app.Create.NewCategorySet()
    for cat in doc.Settings.Categories:
        if bindable:
            if cat.AllowsBoundParameters:
                cat_set.Insert(cat)
        else:
            cat_set.Insert(cat)
    return cat_set


def get_rule_filters(doc=None):
    """
    Retrieves a list of rule-based filters from the given Revit document.

    Args:
        doc (DB.Document, optional): The Revit document to retrieve the filters from.
                                     If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of ParameterFilterElement instances from the document.
    """
    doc = doc or DOCS.doc
    rfcl = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ParameterFilterElement)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return list(rfcl)


def get_connected_circuits(element, spare=False, space=False):
    """
    Retrieves the electrical circuits connected to a given element.

    Args:
        element (DB.Element): The Revit element to get connected circuits for.
        spare (bool, optional): Include spare circuits if True. Defaults to False.
        space (bool, optional): Include space circuits if True. Defaults to False.

    Returns:
        list: A list of electrical systems connected to the element that match the specified circuit types.
    """
    circuit_types = [DB.Electrical.CircuitType.Circuit]
    if spare:
        circuit_types.append(DB.Electrical.CircuitType.Spare)
    if space:
        circuit_types.append(DB.Electrical.CircuitType.Space)
    if HOST_APP.is_newer_than(
        2021, or_equal=True
    ):  # deprecation of ElectricalSystems in 2021
        if element.MEPModel and element.MEPModel.GetElectricalSystems():
            return [
                x
                for x in element.MEPModel.GetElectricalSystems()
                if x.CircuitType in circuit_types
            ]
    else:
        if element.MEPModel and element.MEPModel.ElectricalSystems:
            return [
                x
                for x in element.MEPModel.ElectricalSystems
                if x.CircuitType in circuit_types
            ]


def get_element_categories(elements):
    """
    Given a list of Revit elements, returns a list of unique categories.

    Args:
        elements (list): A list of Revit elements.

    Returns:
        list: A list of unique categories of the given elements.
    """
    catsdict = {x.Category.Name: x.Category for x in elements}
    uniquenames = set(catsdict.keys())
    return [catsdict[x] for x in uniquenames]


def get_category_schedules(category_or_catname, doc=None):
    """
    Retrieves all schedules for a given category in a Revit document.

    Args:
        category_or_catname (str or Category): The category or category name to filter schedules.
        doc (Document, optional): The Revit document to search in. Defaults to None, in which case the default document is used.

    Returns:
        list: A list of schedules that belong to the specified category.
    """
    doc = doc or DOCS.doc
    cat = get_category(category_or_catname)
    scheds = get_all_schedules(doc=doc)
    return [x for x in scheds if x.Definition.CategoryId == cat.Id]


def get_schedule_field(schedule, field_name):
    """
    Retrieves a specific field from a Revit schedule by its name.

    Args:
        schedule (Schedule): The Revit schedule object.
        field_name (str): The name of the field to retrieve.

    Returns:
        ScheduleField: The field object if found, otherwise None.
    """
    for field_idx in schedule.Definition.GetFieldOrder():
        field = schedule.Definition.GetField(field_idx)
        if field.GetName() == field_name:
            return field


def get_schedule_filters(schedule, field_name, return_index=False):
    """
    Retrieves the filters applied to a schedule based on a specified field name.

    Args:
        schedule (Schedule): The schedule from which to retrieve filters.
        field_name (str): The name of the field to match filters against.
        return_index (bool, optional): If True, returns the indices of the matching filters.
                                       If False, returns the filter objects. Defaults to False.

    Returns:
        list: A list of matching filters or their indices, depending on the value of return_index.
    """
    matching_filters = []
    field = get_schedule_field(schedule, field_name)
    if field:
        for idx, sfilter in enumerate(schedule.Definition.GetFilters()):
            if sfilter.FieldId == field.FieldId:
                if return_index:
                    matching_filters.append(idx)
                else:
                    matching_filters.append(sfilter)
    return matching_filters


def get_sheet_tblocks(src_sheet):
    """
    Retrieves all title block elements from a given Revit sheet.

    Args:
        src_sheet (DB.ViewSheet): The source Revit sheet from which to collect title blocks.

    Returns:
        list: A list of title block elements present on the specified sheet.
    """
    sheet_tblocks = (
        DB.FilteredElementCollector(src_sheet.Document, src_sheet.Id)
        .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return list(sheet_tblocks)


def get_sheet_sets(doc=None):
    """
    Retrieves all sheet sets from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve sheet sets from.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of ViewSheetSet elements from the document.
    """
    doc = doc or DOCS.doc
    sheet_sets = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ViewSheetSet)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    return list(sheet_sets)


def get_rev_number(revision, sheet=None):
    """
    Get the revision number for a given revision.
    If a sheet is provided and it is an instance of DB.ViewSheet, the function
    returns the revision number as it appears on the sheet. Otherwise, it returns
    the sequence number of the revision or the revision number if it exists.

    Args:
        revision (DB.Revision): The revision object to get the number for.
        sheet (DB.ViewSheet, optional): The sheet object to get the revision number from. Defaults to None.

    Returns:
        str: The revision number as a string.
    """
    # if sheet is provided, get number on sheet
    if sheet and isinstance(sheet, DB.ViewSheet):
        return sheet.GetRevisionNumberOnSheet(revision.Id)
    # otherwise get number from revision
    revnum = revision.SequenceNumber
    if hasattr(revision, "RevisionNumber"):
        revnum = revision.RevisionNumber
    return revnum


def get_pointclouds(doc=None):
    """
    Retrieves all point cloud elements from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to search for point cloud elements.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of point cloud elements found in the specified document.
    """
    doc = doc or DOCS.doc
    return get_elements_by_categories([DB.BuiltInCategory.OST_PointClouds], doc=doc)


def get_mep_connections(element):
    """
    Retrieves the MEP (Mechanical, Electrical, and Plumbing) connections for a given Revit element.

    Args:
        element (DB.Element): The Revit element for which to retrieve MEP connections. This can be a
                              FamilyInstance or a Plumbing Pipe.

    Returns:
        list: A list of elements that are connected to the given element through MEP connections.

    Returns an empty list if no connections are found or if the element does not have a
              ConnectorManager.
    """
    connmgr = None
    if isinstance(element, DB.FamilyInstance):
        connmgr = element.MEPModel.ConnectorManager
    elif isinstance(element, DB.Plumbing.Pipe):
        connmgr = element.ConnectorManager

    if connmgr:
        connelements = [
            y.Owner
            for x in connmgr.Connectors
            for y in x.AllRefs
            if x.IsConnected
            and y.Owner.Id != element.Id
            and y.ConnectorType != DB.ConnectorType.Logical
        ]
        return connelements


def get_fillpattern_element(fillpattern_name, fillpattern_target, doc=None):
    """
    Retrieves a FillPatternElement from the Revit document based on the given fill pattern name and target.

    Args:
        fillpattern_name (str): The name of the fill pattern to search for.
        fillpattern_target (DB.FillPatternTarget): The target type of the fill pattern (e.g., Drafting or Model).
        doc (DB.Document, optional): The Revit document to search in. If not provided, defaults to DOCS.doc.

    Returns:
        DB.FillPatternElement: The FillPatternElement that matches the given name and target, or None if not found.
    """
    doc = doc or DOCS.doc
    existing_fp_elements = DB.FilteredElementCollector(doc).OfClass(
        framework.get_type(DB.FillPatternElement)
    )

    for existing_fp_element in existing_fp_elements:
        fillpattern = existing_fp_element.GetFillPattern()
        if (
            fillpattern_name == fillpattern.Name
            and fillpattern_target == fillpattern.Target
        ):
            return existing_fp_element


def get_all_fillpattern_elements(fillpattern_target, doc=None):
    """
    Retrieves all fill pattern elements from the given document that match the specified fill pattern target.

    Args:
        fillpattern_target (DB.FillPatternTarget): The target fill pattern to match.
        doc (DB.Document, optional): The Revit document to search within. If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of fill pattern elements that match the specified fill pattern target.
    """
    doc = doc or DOCS.doc
    existing_fp_elements = DB.FilteredElementCollector(doc).OfClass(
        framework.get_type(DB.FillPatternElement)
    )

    return [
        x
        for x in existing_fp_elements
        if x.GetFillPattern().Target == fillpattern_target
    ]


def get_fillpattern_from_element(element, background=True, doc=None):
    """
    Retrieves the fill pattern from a given Revit element.

    Args:
        element (DB.Element): The Revit element from which to retrieve the fill pattern.
        background (bool, optional): If True, retrieves the background fill pattern;
                                     otherwise, retrieves the foreground fill pattern.
                                     Defaults to True.
        doc (DB.Document, optional): The Revit document. If not provided, defaults to DOCS.doc.

    Returns:
        DB.FillPattern: The fill pattern of the specified element, or None if not found.
    """
    doc = doc or DOCS.doc

    def get_fpm_from_frtype(etype):
        fp_id = None
        if HOST_APP.is_newer_than(2018):
            # return requested fill pattern (background or foreground)
            fp_id = (
                etype.BackgroundPatternId if background else etype.ForegroundPatternId
            )
        else:
            fp_id = etype.FillPatternId
        if fp_id:
            fillpat_element = doc.GetElement(fp_id)
            if fillpat_element:
                return fillpat_element.GetFillPattern()

    if isinstance(element, DB.FilledRegion):
        return get_fpm_from_frtype(doc.GetElement(element.GetTypeId()))


def get_local_keynote_file(doc=None):
    """
    Retrieves the path to the local keynote file for the given Revit document.

    Args:
        doc (DB.Document, optional): The Revit document. If not provided, the default document (DOCS.doc) is used.

    Returns:
        str: The user-visible path to the local keynote file if it is an external file reference, otherwise None.
    """
    doc = doc or DOCS.doc
    knote_table = DB.KeynoteTable.GetKeynoteTable(doc)
    if knote_table.IsExternalFileReference():
        knote_table_ref = knote_table.GetExternalFileReference()
        return DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
            knote_table_ref.GetAbsolutePath()
        )
    return None


def get_external_keynote_file(doc=None):
    """
    Retrieves the path to the external keynote file associated with the given Revit document.

    Args:
        doc (DB.Document, optional): The Revit document to query. If not provided, defaults to DOCS.doc.

    Returns:
        str: The in-session path to the external keynote file if it exists and has a valid display path, otherwise None.
    """
    doc = doc or DOCS.doc
    knote_table = DB.KeynoteTable.GetKeynoteTable(doc)
    if knote_table.RefersToExternalResourceReferences():
        refs = knote_table.GetExternalResourceReferences()
        if refs:
            for ref_type, ref in dict(refs).items():
                if ref.HasValidDisplayPath():
                    return ref.InSessionPath
    return None


def get_keynote_file(doc=None):
    """
    Retrieves the keynote file path for the given Revit document.
    If a local keynote file is available, it returns the local path.
    Otherwise, it returns the external keynote file path.

    Args:
        doc (Document, optional): The Revit document. If not provided,
                                  the default document (DOCS.doc) is used.

    Returns:
        str: The path to the keynote file.
    """
    doc = doc or DOCS.doc
    local_path = get_local_keynote_file(doc=doc)
    if not local_path:
        return get_external_keynote_file(doc=doc)
    return local_path


def get_used_keynotes(doc=None):
    """
    Retrieves all keynote tags used in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to search for keynote tags.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        List[Element]: A list of keynote tag elements found in the document.
    """
    doc = doc or DOCS.doc
    return (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_KeynoteTags)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_visible_keynotes(view=None):
    """
    Retrieves all visible keynote tags in the specified Revit view.

    Args:
        view (Autodesk.Revit.DB.View): The Revit view from which to retrieve keynote tags.

    Returns:
        list[Autodesk.Revit.DB.Element]: A list of keynote tag elements visible in the specified view.
    """
    doc = view.Document
    return (
        DB.FilteredElementCollector(doc, view.Id)
        .OfCategory(DB.BuiltInCategory.OST_KeynoteTags)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_available_keynotes(doc=None):
    """
    Retrieves the available keynotes from the given Revit document.

    Args:
        doc (DB.Document, optional): The Revit document from which to retrieve keynotes.
                                     If not provided, the default document (DOCS.doc) will be used.

    Returns:
        DB.KeyBasedTreeEntries: A collection of keynote entries from the keynote table.
    """
    doc = doc or DOCS.doc
    knote_table = DB.KeynoteTable.GetKeynoteTable(doc)
    return knote_table.GetKeyBasedTreeEntries()


def get_available_keynotes_tree(doc=None):
    """
    Retrieves the available keynotes in a hierarchical tree structure.

    Args:
        doc (Document, optional): The Revit document to retrieve keynotes from.
                                  If not provided, defaults to the current document.

    Returns:
        dict: A dictionary representing the hierarchical structure of keynotes.

    Raises:
        NotImplementedError: This function is not yet implemented.
    """
    doc = doc or DOCS.doc
    knotes = get_available_keynotes(doc=doc)
    # TODO: implement knotes tree
    raise NotImplementedError()


def is_placed(spatial_element):
    """
    Check if a spatial element (Room, Area, or Space) is placed and has a positive area.

    Args:
        spatial_element (DB.Element): The spatial element to check. It can be an instance of
                                      DB.Architecture.Room, DB.Area, or DB.Mechanical.Space.

    Returns:
        bool: True if the spatial element is placed and has an area greater than 0, False otherwise.
    """
    return (
        isinstance(
            spatial_element, (DB.Architecture.Room, DB.Area, DB.Mechanical.Space)
        )
        and spatial_element.Area > 0
    )


def get_central_path(doc=None):
    """

    Returns the central model path of a Revit document if it is workshared.

    Args:
        doc (Document, optional): The Revit document. If not provided, defaults to DOCS.doc.

    Returns:
        str: The user-visible path to the central model if the document is workshared.
    """
    doc = doc or DOCS.doc
    if doc.IsWorkshared:
        model_path = doc.GetWorksharingCentralModelPath()
        return DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(model_path)


def is_metric(doc=None):
    """
    Determines if the given Revit document uses the metric unit system.

    Args:
        doc (Document, optional): The Revit document to check. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        bool: True if the document uses the metric unit system, False otherwise.
    """
    doc = doc or DOCS.doc
    return doc.DisplayUnitSystem == DB.DisplayUnit.METRIC


def is_imperial(doc=None):
    """
    Checks if the given Revit document uses the imperial unit system.

    Args:
        doc (Document, optional): The Revit document to check. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        bool: True if the document uses the imperial unit system, False otherwise.
    """
    doc = doc or DOCS.doc
    return doc.DisplayUnitSystem == DB.DisplayUnit.IMPERIAL


def get_view_sheetrefinfo(view):
    """
    Retrieves sheet reference information for a given view.
    This function checks if the view is placed on a sheet by looking at the
    'Sheet Number' and 'Sheet Name' parameters. If the view is placed on a
    sheet, it returns the sheet number, sheet name, and detail number. If the
    view is not placed on a sheet, it checks the 'Referencing Sheet' and
    'Referencing Detail' parameters to see if the view is referenced by another
    view on a sheet, and returns the corresponding information.

    Args:
        view (DB.View): The Revit view object to retrieve sheet reference
                        information from.

    Returns:
        SheetRefInfo: An object containing the sheet number, sheet name, detail
                      number, and reference view ID if applicable.
    """
    sheet_num = view.Parameter[DB.BuiltInParameter.VIEWPORT_SHEET_NUMBER].AsString()
    sheet_name = view.Parameter[DB.BuiltInParameter.VIEWPORT_SHEET_NAME].AsString()
    detail_num = view.Parameter[DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER].AsString()

    if sheet_num:
        return SheetRefInfo(
            sheet_num=sheet_num,
            sheet_name=sheet_name,
            detail_num=detail_num,
            ref_viewid=None,
        )
    ref_sheet_num = view.Parameter[
        DB.BuiltInParameter.VIEW_REFERENCING_SHEET
    ].AsString()
    ref_sheet = get_sheet_by_number(ref_sheet_num)
    ref_sheet_name = get_name(ref_sheet) if ref_sheet else ""
    ref_detail_num = view.Parameter[
        DB.BuiltInParameter.VIEW_REFERENCING_DETAIL
    ].AsString()
    if ref_sheet_num:
        return SheetRefInfo(
            sheet_num=ref_sheet_num,
            sheet_name=ref_sheet_name,
            detail_num=ref_detail_num,
            ref_viewid=get_view_by_sheetref(ref_sheet_num, ref_detail_num),
        )


def get_all_sheeted_views(doc=None, sheets=None):
    """
    Retrieves all view IDs that are placed on sheets in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to query. If not provided, defaults to DOCS.doc.
        sheets (list, optional): A list of sheet elements to query. If not provided, defaults to all sheets in the document.

    Returns:
        set: A set of view IDs that are placed on the provided sheets.
    """
    doc = doc or DOCS.doc
    sheets = sheets or get_sheets(doc=doc)
    all_sheeted_view_ids = set()
    for sht in sheets:
        vp_ids = [doc.GetElement(x).ViewId for x in sht.GetAllViewports()]
        all_sheeted_view_ids.update(vp_ids)
    return all_sheeted_view_ids


def is_view_sheeted(view):
    """
    Checks if a given view is placed on a sheet.

    Args:
        view (Autodesk.Revit.DB.View): The Revit view to check.

    Returns:
        bool: True if the view is placed on a sheet, False otherwise.
    """
    return view.Id in get_all_sheeted_views(doc=view.Document)


def can_refer_other_views(source_view):
    """
    Determines if the given source view can refer to other views.

    Args:
        source_view: The view to check. Expected to be an instance of a Revit view class.

    Returns:
        bool: True if the source view is an instance of DB.ViewDrafting, DB.ViewPlan, or DB.ViewSection; otherwise, False.
    """
    return isinstance(source_view, (DB.ViewDrafting, DB.ViewPlan, DB.ViewSection))


def is_referring_to(source_view, target_view):
    """
    Determines if the source view is referring to the target view.

    Args:
        source_view (Autodesk.Revit.DB.View): The view that may be referring to another view.
        target_view (Autodesk.Revit.DB.View): The view that is being checked if it is referred to by the source view.

    Returns:
        bool: True if the source view is referring to the target view, False otherwise.
    """
    doc = source_view.Document
    target_viewname = get_name(target_view)
    if can_refer_other_views(source_view):
        for ref_elid in get_all_referencing_elements_in_view(source_view):
            viewref_el = doc.GetElement(ref_elid)
            targetview_param = viewref_el.Parameter[
                DB.BuiltInParameter.REFERENCE_VIEWER_TARGET_VIEW
            ]
            if targetview_param:
                tvp_view = doc.GetElement(targetview_param.AsElementId())
                if tvp_view and get_name(tvp_view) == target_viewname:
                    return True
            else:
                viewref_name = get_name(viewref_el)
                if viewref_name == target_viewname:
                    return True


def yield_referring_views(target_view, all_views=None):
    """
    Yields the IDs of views that refer to the target view.

    Args:
        target_view (View): The view that other views may refer to.
        all_views (list[View], optional): A list of all views to check. If not provided,
                                          all views in the document of the target view will be used.
    Yields:
        ElementId: The ID of a view that refers to the target view.
    """
    all_views = all_views or get_all_views(doc=target_view.Document)
    for view in all_views:
        if is_referring_to(view, target_view):
            yield view.Id


def yield_referenced_views(doc=None, all_views=None):
    """
    Yields the IDs of views that have referring views.

    Args:
        doc (Document, optional): The Revit document to query. Defaults to None, in which case the global DOCS.doc is used.
        all_views (list, optional): A list of all views in the document. Defaults to None, in which case all views are retrieved using get_all_views(doc).
    Yields:
        ElementId: The ID of a view that has referring views.
    """
    doc = doc or DOCS.doc
    all_views = all_views or get_all_views(doc=doc)
    for view in all_views:
        # if it has any referring views, yield
        if next(yield_referring_views(view), None):
            yield view.Id


def yield_unreferenced_views(doc=None, all_views=None):
    """
    Yields the IDs of views in a Revit document that have no referring views.

    Args:
        doc (Document, optional): The Revit document to search for unreferenced views.
                                  If not provided, defaults to DOCS.doc.
        all_views (list, optional): A list of all views in the document.
                                    If not provided, it will be retrieved using get_all_views(doc).
    Yields:
        ElementId: The ID of each view that has no referring views.
    """
    doc = doc or DOCS.doc
    all_views = all_views or get_all_views(doc=doc)
    for view in all_views:
        # if it has NO referring views, yield
        if len(list(yield_referring_views(view))) == 0:
            yield view.Id


def get_line_categories(doc=None):
    """
    Retrieves the line categories from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve the line categories from.
                                  If not provided, it defaults to DOCS.doc.

    Returns:
        SubCategories: The subcategories of the line category in the Revit document.
    """
    doc = doc or DOCS.doc
    lines_cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
    return lines_cat.SubCategories


def get_line_styles(doc=None):
    """
    Retrieves the line styles from the given Revit document.

    Args:
        doc (Document, optional): The Revit document to retrieve line styles from.
                                  If None, the current document will be used.

    Returns:
        list: A list of GraphicsStyle objects representing the line styles in the document.
    """
    return [
        x.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
        for x in get_line_categories(doc=doc)
    ]


def get_history(target_element):
    """
    Retrieves the worksharing history of a given Revit element.

    Args:
        target_element (DB.Element): The Revit element for which to retrieve the history.

    Returns:
        ElementHistory: An object containing the creator, owner, and last changed by information of the element.
    """
    doc = target_element.Document
    if doc.IsWorkshared:
        wti = DB.WorksharingUtils.GetWorksharingTooltipInfo(doc, target_element.Id)
        return ElementHistory(
            creator=wti.Creator, owner=wti.Owner, last_changed_by=wti.LastChangedBy
        )


def is_detail_curve(element):
    """
    Check if the given element is a detail curve.

    Args:
        element: The element to check.

    Returns:
        bool: True if the element is a detail curve, False otherwise.
    """
    return isinstance(element, DETAIL_CURVES)


def is_model_curve(element):
    """
    Check if the given element is a model curve.

    Args:
        element: The element to check.

    Returns:
        bool: True if the element is a model curve, False otherwise.
    """
    return isinstance(element, MODEL_CURVES)


def is_sketch_curve(element):
    """
    Determines if the given Revit element is a sketch curve.

    Args:
        element (DB.Element): The Revit element to check.

    Returns:
        bool: True if the element is a sketch curve, False otherwise.
    """
    if element.Category:
        cid = element.Category.Id
        return cid == DB.ElementId(DB.BuiltInCategory.OST_SketchLines)


def get_all_schemas():
    """
    Retrieves all the schemas from the Extensible Storage in Revit.

    Returns:
        IList[Schema]: A list of all schemas available in the Extensible Storage.
    """
    return DB.ExtensibleStorage.Schema.ListSchemas()


def get_schema_field_values(element, schema):
    """
    Retrieves the values of fields from a given schema for a specified Revit element.

    Args:
        element (DB.Element): The Revit element from which to retrieve the schema field values.
        schema (DB.ExtensibleStorage.Schema): The schema that defines the fields to retrieve.

    Returns:
        dict: A dictionary where the keys are field names and the values are the corresponding field values.
    """
    field_values = {}
    entity = element.GetEntity(schema)
    if entity:
        for field in schema.ListFields():
            field_type = field.ValueType
            if field.ContainerType == DB.ExtensibleStorage.ContainerType.Array:
                field_type = framework.IList[field.ValueType]
            elif field.ContainerType == DB.ExtensibleStorage.ContainerType.Map:
                field_type = framework.IDictionary[field.KeyType, field.ValueType]
            try:
                value = entity.Get[field_type](
                    field.FieldName, DB.DisplayUnitType.DUT_UNDEFINED
                )
            except:
                value = None

            field_values[field.FieldName] = value
    return field_values


def get_family_type(type_name, family_doc):
    """
    Retrieves a family type from a Revit family document by its name.

    Args:
        type_name (str): The name of the family type to retrieve.
        family_doc (Document): The Revit family document to search in. If None, the default document (DOCS.doc) is used.

    Returns:
        FamilyType: The family type with the specified name.

    Raises:
        PyRevitException: If the provided document is not a family document.
    """
    family_doc = family_doc or DOCS.doc
    if family_doc.IsFamilyDocument:
        for ftype in family_doc.FamilyManager.Types:
            if ftype.Name == type_name:
                return ftype
    else:
        raise PyRevitException("Document is not a family")


def get_family_parameter(param_name, family_doc):
    """
    Retrieves a family parameter from a Revit family document by its name.

    Args:
        param_name (str): The name of the parameter to retrieve.
        family_doc (Document): The Revit family document to search in. If None, defaults to DOCS.doc.

    Returns:
        FamilyParameter: The family parameter with the specified name.

    Raises:
        PyRevitException: If the provided document is not a family document.
    """
    family_doc = family_doc or DOCS.doc
    if family_doc.IsFamilyDocument:
        for fparam in family_doc.FamilyManager.GetParameters():
            if fparam.Definition.Name == param_name:
                return fparam
    else:
        raise PyRevitException("Document is not a family")


def get_family_parameters(family_doc):
    """
    Retrieves the parameters of a Revit family document.

    Args:
        family_doc: The Revit family document from which to retrieve parameters.
                    If None, the default document (DOCS.doc) will be used.

    Returns:
        A collection of family parameters from the specified family document.

    Raises:
        PyRevitException: If the provided document is not a family document.
    """
    family_doc = family_doc or DOCS.doc
    if family_doc.IsFamilyDocument:
        return family_doc.FamilyManager.GetParameters()
    else:
        raise PyRevitException("Document is not a family")


def get_family_label_parameters(family_doc):
    """
    Retrieves the set of family label parameters from a given Revit family document.

    Args:
        family_doc (DB.Document): The Revit family document to retrieve label parameters from.
                                  If None, the default document (DOCS.doc) is used.

    Returns:
        set: A set of family label parameters (DB.FamilyParameter) found in the document.

    Raises:
        PyRevitException: If the provided document is not a family document.
    """
    family_doc = family_doc or DOCS.doc
    if family_doc.IsFamilyDocument:
        dims = (
            DB.FilteredElementCollector(family_doc)
            .OfClass(DB.Dimension)
            .WhereElementIsNotElementType()
        )
        label_params = set()
        for dim in dims:
            try:
                # throws exception when dimension can not be labeled
                if isinstance(dim.FamilyLabel, DB.FamilyParameter):
                    label_params.add(dim.FamilyLabel)
            except Exception:
                pass
        return label_params
    else:
        raise PyRevitException("Document is not a family")


def get_door_rooms(door):
    """Get from/to rooms associated with given door element.


    Args:
        door (DB.FamilyInstance): door instance


    Returns:
        tuple(DB.Architecture.Room, DB.Architecture.Room): from/to rooms
    """
    door_phase = door.Document.GetElement(door.CreatedPhaseId)
    return (door.FromRoom[door_phase], door.ToRoom[door_phase])


def get_doors(elements=None, doc=None, room_id=None):
    """Get all doors in active or given document.


    Args:
        elements (list[DB.Element]): find rooms in given elements instead
        doc (DB.Document): target document; default is active document
        room_id (DB.ElementId): only doors associated with given room


    Returns:
        (list[DB.Element]): room instances
    """
    doc = doc or DOCS.doc
    all_doors = get_elements_by_categories(
        [DB.BuiltInCategory.OST_Doors], elements=elements, doc=doc
    )
    if room_id:
        room_doors = []
        for door in all_doors:
            from_room, to_room = get_door_rooms(door)
            if (from_room and from_room.Id == room_id) or (
                to_room and to_room.Id == room_id
            ):
                room_doors.append(door)
        return room_doors
    else:
        return list(all_doors)


def get_all_print_settings(doc=None):
    """
    Retrieves all print settings from the given Revit document.

    Args:
        doc (Document, optional): The Revit document from which to retrieve print settings.
                                  If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of print settings elements from the document.
    """
    doc = doc or DOCS.doc
    return [doc.GetElement(x) for x in doc.GetPrintSettingIds()]


def get_used_paper_sizes(doc=None):
    """
    Retrieves a list of used paper sizes from the print settings in the given Revit document.

    Args:
        doc (Document, optional): The Revit document to query. If not provided, defaults to DOCS.doc.

    Returns:
        list: A list of paper sizes used in the print settings of the document.
    """
    doc = doc or DOCS.doc
    return [x.PrintParameters.PaperSize for x in get_all_print_settings(doc=doc)]


def find_paper_size_by_name(paper_size_name, doc=None):
    """
    Finds and returns a paper size object by its name.

    Args:
        paper_size_name (str): The name of the paper size to find.
        doc (Document, optional): The Revit document to search in. If not provided,
                                  the default document (DOCS.doc) will be used.

    Returns:
        PaperSize: The paper size object that matches the given name, or None if not found.
    """
    doc = doc or DOCS.doc
    paper_size_name = paper_size_name.lower()
    for psize in doc.PrintManager.PaperSizes:
        if psize.Name.lower() == paper_size_name:
            return psize


def find_paper_sizes_by_dims(printer_name, paper_width, paper_height, doc=None):
    """
    Finds paper sizes by dimensions for a given printer.

    Args:
        printer_name (str): The name of the printer.
        paper_width (float): The width of the paper in inches.
        paper_height (float): The height of the paper in inches.
        doc (optional): The document context. Defaults to None.

    Returns:
        list: A list of matching paper sizes.
    """
    doc = doc or DOCS.doc
    paper_sizes = []
    system_paper_sizes = coreutils.get_paper_sizes(printer_name)
    mlogger.debug("looking for paper size W:%s H:%s", paper_width, paper_height)
    mlogger.debug(
        "system paper sizes: %s -> %s",
        printer_name,
        [x.PaperName for x in system_paper_sizes],
    )
    for sys_psize in system_paper_sizes:
        sys_pname = sys_psize.PaperName
        sys_pwidth = int(sys_psize.Width / 100.00)
        sys_pheight = int(sys_psize.Height / 100.00)
        wxd = paper_width == sys_pwidth and paper_height == sys_pheight
        dxw = paper_width == sys_pheight and paper_height == sys_pwidth
        mlogger.debug(
            '%s "%s" W:%s H:%s',
            "✓" if wxd or dxw else " ",
            sys_pname,
            sys_pwidth,
            sys_pheight,
        )
        if wxd or dxw:
            psize = find_paper_size_by_name(sys_pname)
            if psize:
                paper_sizes.append(psize)
                mlogger.debug("found matching paper: %s", psize.Name)
    return paper_sizes


def get_titleblock_print_settings(tblock, printer_name, doc_psettings):
    """
    Retrieves the print settings for a given title block that match the specified printer and document print settings.

    Args:
        tblock (DB.FamilyInstance): The title block instance.
        printer_name (str): The name of the printer.
        doc_psettings (list[DB.PrintSetting]): A list of document print settings.

    Returns:
        list[DB.PrintSetting]: A sorted list of print settings that match the title block size and orientation.
    """
    doc = tblock.Document
    page_width_param = tblock.Parameter[DB.BuiltInParameter.SHEET_WIDTH]
    page_height_param = tblock.Parameter[DB.BuiltInParameter.SHEET_HEIGHT]
    page_width = int(round(page_width_param.AsDouble() * 12.0))
    page_height = int(round(page_height_param.AsDouble() * 12.0))
    tform = tblock.GetTotalTransform()
    is_portrait = (page_width < page_height) or (int(tform.BasisX.Y) == -1)
    paper_sizes = find_paper_sizes_by_dims(
        printer_name, page_width, page_height, doc=doc
    )
    paper_size_names = [x.Name for x in paper_sizes]
    page_orient = (
        DB.PageOrientationType.Portrait
        if is_portrait
        else DB.PageOrientationType.Landscape
    )
    all_tblock_psettings = set()
    for doc_psetting in doc_psettings:
        try:
            pparams = doc_psetting.PrintParameters
            if (
                pparams.PaperSize
                and pparams.PaperSize.Name in paper_size_names
                and (pparams.ZoomType == DB.ZoomType.Zoom and pparams.Zoom == 100)
                and pparams.PageOrientation == page_orient
            ):
                all_tblock_psettings.add(doc_psetting)
        except Exception:
            mlogger.debug("incompatible psettings: %s", doc_psetting.Name)
    return sorted(all_tblock_psettings, key=lambda x: x.Name)


def get_crop_region(view):
    """Takes crop region of a view.

    Args:
        view (DB.View): view to get crop region from

    Returns:
        (list[DB.CurveLoop]): list of curve loops
    """
    crsm = view.GetCropRegionShapeManager()
    if HOST_APP.is_newer_than(2015):
        crsm_valid = crsm.CanHaveShape
    else:
        crsm_valid = crsm.Valid

    if crsm_valid:
        if HOST_APP.is_newer_than(2015):
            curve_loops = list(crsm.GetCropShape())
        else:
            curve_loops = [crsm.GetCropRegionShape()]

        if curve_loops:
            return curve_loops


def is_cropable_view(view):
    """
    Determines if a given Revit view can be cropped.

    Args:
        view (DB.View): The Revit view to check.

    Returns:
        bool: True if the view can be cropped, False otherwise.

    Notes:
        A view is considered cropable if it is not an instance of DB.ViewSheet or DB.TableView,
        and its ViewType is not Legend or DraftingView.
    """
    return not isinstance(view, (DB.ViewSheet, DB.TableView)) and view.ViewType not in (
        DB.ViewType.Legend,
        DB.ViewType.DraftingView,
    )


def get_view_filters(view, ordered=True):
    """
    Retrieves the filters applied to a given Revit view.

    Args:
        view (Autodesk.Revit.DB.View): The Revit view from which to retrieve the filters.
        ordered (bool, optional): If True, returns filters in their proper order using GetOrderedFilters().
                                 If False, returns filters in arbitrary order using GetFilters().
                                 Defaults to True.

    Returns:
        list[Autodesk.Revit.DB.Element]: A list of filter elements applied to the view.
    """
    view_filters = []
    if ordered:
        for filter_id in view.GetOrderedFilters():
            filter_element = view.Document.GetElement(filter_id)
            view_filters.append(filter_element)
    else:
        for filter_id in view.GetFilters():
            filter_element = view.Document.GetElement(filter_id)
            view_filters.append(filter_element)
    return view_filters


def get_element_workset(element):
    """
    Retrieves the workset of a given Revit element.

    Args:
        element (DB.Element): The Revit element for which to retrieve the workset.

    Returns:
        DB.Workset: The workset to which the element belongs, or None if the element's workset ID is invalid.
    """
    doc = element.Document
    workset_table = doc.GetWorksetTable()
    if element.WorksetId != DB.WorksetId.InvalidWorksetId:
        return workset_table.GetWorkset(element.WorksetId)


def get_geometry(element, include_invisible=False, compute_references=False, detail_level=DB.ViewDetailLevel.Medium):
    """
    Retrieves the geometry of a given Revit element.

    Args:
        element (DB.Element): The Revit element from which to retrieve geometry.
        include_invisible (bool, optional): If True, includes non-visible objects in the geometry. Defaults to False.
        compute_references (bool, optional): If True, computes references for the geometry objects. Defaults to False.
        detail_level (DB.ViewDetailLevel, optional): The detail level used for geometry extraction. Defaults to medium.

    Returns:
        list: A list of geometry objects associated with the element. If the element has no geometry, returns None.

    Raises:
        TypeError: If the element's geometry cannot be retrieved.

    Notes:
        - If the geometry object is an instance of DB.GeometryInstance, its instance geometry is retrieved and added to the list.
        - Logs a debug message if the element has no geometry.
    """
    geom_opts = DB.Options()
    geom_opts.IncludeNonVisibleObjects = include_invisible
    geom_opts.ComputeReferences = compute_references
    geom_opts.DetailLevel = detail_level
    geom_objs = []
    try:
        for gobj in element.Geometry[geom_opts]:
            if isinstance(gobj, DB.GeometryInstance):
                inst_geom = gobj.GetInstanceGeometry()
                geom_objs.extend(list(inst_geom))
            else:
                geom_objs.append(gobj)
        return geom_objs
    except TypeError:
        get_elementid_value = get_elementid_value_func()
        mlogger.debug("element %s has no geometry", get_elementid_value(element.Id))
        return


def get_array_group_ids(doc=None):
    """
    Collects and returns the IDs of all array groups in the given document.

    Args:
        document (DB.Document): The Revit document to search for array groups.

    Returns:
        list: A list of element IDs representing the array groups.
    """
    array_list = DB.FilteredElementCollector(doc or DOCS.doc).OfCategory(
        DB.BuiltInCategory.OST_IOSArrays
    )
    arrays_groups = []
    for ar in array_list:
        arrays_groups.extend(ar.GetOriginalMemberIds())
        arrays_groups.extend(ar.GetCopiedMemberIds())
    return set(arrays_groups)


def get_array_group_ids_types(doc=None):
    """
    Retrieves the unique types of array groups in the given Revit document.

    Args:
        doc: The Revit document from which to collect array group types.

    Returns:
        A set of unique array group type IDs present in the document.
    """
    arrays_groups = get_array_group_ids(doc or DOCS.doc)
    return {doc.GetElement(ar).GetTypeId() for ar in arrays_groups}
