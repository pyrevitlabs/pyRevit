"""Database objects creation functions."""

import sys

from pyrevit import HOST_APP, DOCS, PyRevitException
from pyrevit import framework
from pyrevit.framework import clr
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB
from pyrevit.revit.db import query
from pyrevit.revit import units
from pyrevit.compat import IRONPY, get_elementid_value_func

# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# value evaluators for (str, numeric) values
PARAM_VALUE_EVALUATORS = {
    "startswith": (DB.FilterStringBeginsWith, DB.FilterStringBeginsWith),
    "contains": (DB.FilterStringContains, DB.FilterStringContains),
    "endswith": (DB.FilterStringEndsWith, DB.FilterStringEndsWith),
    "==": (DB.FilterStringEquals, DB.FilterNumericEquals),
    ">": (DB.FilterStringGreater, DB.FilterNumericGreater),
    ">=": (DB.FilterStringGreaterOrEqual, DB.FilterNumericGreaterOrEqual),
    "<": (DB.FilterStringLess, DB.FilterNumericLess),
    "<=": (DB.FilterStringLessOrEqual, DB.FilterNumericLessOrEqual),
}


# http://www.revitapidocs.com/2018.1/5da8e3c5-9b49-f942-02fc-7e7783fe8f00.htm
class FamilyLoaderOptionsHandler(DB.IFamilyLoadOptions):
    """Family loader options handler."""

    # pythonnet requires a namespace to bake .NET interface implementations
    __namespace__ = "PyRevitLabs.Python"

    def __init__(self, overwriteParameterValues=True):
        self._overwriteParameterValues = overwriteParameterValues

    def OnFamilyFound(self, familyInUse, overwriteParameterValues):  # pylint: disable=W0613
        """A method called when the family was found in the target document.

        The interface declares ref parameters: IronPython passes a
        StrongBox to mutate; pythonnet expects the updated values returned
        in a tuple after the return value.
        """
        if IRONPY:
            overwriteParameterValues.Value = self._overwriteParameterValues
            return True
        return (True, self._overwriteParameterValues)

    def OnSharedFamilyFound(
        self,
        sharedFamily,  # pylint: disable=W0613
        familyInUse,  # pylint: disable=W0613
        source,  # pylint: disable=W0613
        overwriteParameterValues,
    ):  # pylint: disable=W0613
        if IRONPY:
            source.Value = DB.FamilySource.Family
            overwriteParameterValues.Value = self._overwriteParameterValues
            return True
        return (True, DB.FamilySource.Family, self._overwriteParameterValues)


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    """Handle copy and paste errors."""

    def OnDuplicateTypeNamesFound(self, args):  # pylint: disable=unused-argument
        """Use destination model types if duplicate."""
        return DB.DuplicateTypeAction.UseDestinationTypes


def create_param_from_definition(
    param_def,
    category_list,
    builtin_param_group,
    type_param=False,
    allow_vary_betwen_groups=False,  # pylint: disable=unused-argument
    doc=None,
):
    doc = doc or DOCS.doc
    # verify and create category set
    if category_list:
        category_set = query.get_category_set(category_list, doc=doc)
    else:
        category_set = query.get_all_category_set(doc=doc)

    if not category_set:
        raise PyRevitException("Can not create category set.")

    # create binding
    if type_param:
        new_binding = HOST_APP.app.Create.NewTypeBinding(category_set)
    else:
        new_binding = HOST_APP.app.Create.NewInstanceBinding(category_set)

    # FIXME: set allow_vary_betwen_groups
    # param_def.SetAllowVaryBetweenGroups(doc, allow_vary_betwen_groups)
    # insert the binding
    doc.ParameterBindings.Insert(param_def, new_binding, builtin_param_group)
    return True


def create_shared_param(
    param_id_or_name,
    category_list,
    builtin_param_group,
    type_param=False,
    allow_vary_betwen_groups=False,
    doc=None,
):
    doc = doc or DOCS.doc
    # get define shared parameters
    # this is where we grab the ExternalDefinition for the parameter
    msp_list = query.get_defined_sharedparams()
    param_def = None
    for msp in msp_list:
        if msp == param_id_or_name:
            param_def = msp.param_def
    if not param_def:
        raise PyRevitException("Can not find shared parameter.")

    # now create the binding for this definition
    return create_param_from_definition(
        param_def,
        category_list,
        builtin_param_group=builtin_param_group,
        type_param=type_param,
        allow_vary_betwen_groups=allow_vary_betwen_groups,
        doc=doc,
    )


# def create_project_parameter(param_name,
#                              param_type,
#                              category_list,
#                              builtin_param_group,
#                              type_param=False,
#                              allow_vary_betwen_groups=False,
#                              doc=None):
#     doc = doc or DOCS.doc
#     # setup the stupid hacky way to create the project parameter
#     # https://forums.autodesk.com/t5/revit-api-forum/create-project-parameter-not-shared-parameter/td-p/5150182
#     # record the existing shared param file
#     existing_spfile = HOST_APP.app.SharedParametersFilename
#     # go thru creating a temp param file, creating the ext definition
#     temp_spfile = appdata.get_instance_data_file('newpparam')
#     coreutils.touch(temp_spfile)
#     HOST_APP.app.SharedParametersFilename = temp_spfile
#     # create param definition
#     edco = DB.ExternalDefinitionCreationOptions(param_name, param_type)
#     temp_groups = HOST_APP.app.OpenSharedParameterFile().Groups
#     temp_group = temp_groups.Create("ProjectParams")
#     param_def = temp_group.Definitions.Create(edco)
#     # reset shared param file to original
#     HOST_APP.app.SharedParametersFilename = existing_spfile
#     appdata.garbage_data_file(temp_spfile)

#     # now create the binding for this definition
#     return create_param_from_definition(
#         param_def,
#         category_list,
#         builtin_param_group=builtin_param_group,
#         type_param=type_param,
#         allow_vary_betwen_groups=allow_vary_betwen_groups,
#         doc=doc)


def create_new_project(template=None, imperial=True):
    if template:
        return HOST_APP.app.NewProjectDocument(template)
    else:
        units = DB.UnitSystem.Imperial if imperial else DB.UnitSystem.Metric
        return HOST_APP.app.NewProjectDocument(units)


def create_revision(
    description=None, by=None, to=None, date=None, alphanum=False, nonum=False, doc=None
):
    new_rev = DB.Revision.Create(doc or DOCS.doc)
    new_rev.Description = description
    new_rev.IssuedBy = by or ""
    new_rev.IssuedTo = to or ""
    if alphanum:
        new_rev.NumberType = DB.RevisionNumberType.Alphanumeric
    if nonum:
        new_rev.NumberType = coreutils.get_enum_none(DB.RevisionNumberType)
    new_rev.RevisionDate = date or ""
    return new_rev


def copy_elements(element_ids, src_doc, dest_doc, return_ids=False):
    cp_options = DB.CopyPasteOptions()
    cp_options.SetDuplicateTypeNamesHandler(CopyUseDestination())

    if element_ids:
        copied_ids = DB.ElementTransformUtils.CopyElements(
            src_doc,
            framework.List[DB.ElementId](element_ids),
            dest_doc,
            None,
            cp_options,
        )

    if return_ids:
        return copied_ids
    return True


def copy_revisions(revisions, src_doc, dest_doc):
    if revisions is None:
        all_src_revs = query.get_revisions(doc=src_doc)
    else:
        all_src_revs = revisions

    for src_rev in all_src_revs:
        # get an updated list of revisions
        if any(
            [
                query.compare_revisions(x, src_rev)
                for x in query.get_revisions(doc=dest_doc)
            ]
        ):
            mlogger.debug(
                "Revision already exists: %s %s",
                src_rev.RevisionDate,
                src_rev.Description,
            )
        else:
            mlogger.debug(
                "Creating revision: %s %s", src_rev.RevisionDate, src_rev.Description
            )
            create_revision(
                description=src_rev.Description,
                by=src_rev.IssuedBy,
                to=src_rev.IssuedTo,
                date=src_rev.RevisionDate,
                doc=dest_doc,
            )


def copy_all_revisions(src_doc, dest_doc):
    copy_revisions(None, src_doc=src_doc, dest_doc=dest_doc)


def copy_viewtemplates(viewtemplates, src_doc, dest_doc):
    if viewtemplates is None:
        all_viewtemplates = query.get_all_view_templates(doc=src_doc)
    else:
        all_viewtemplates = viewtemplates

    vtemp_ids = [x.Id for x in all_viewtemplates]
    copy_elements(vtemp_ids, src_doc=src_doc, dest_doc=dest_doc)


def create_sheet(
    sheet_num, sheet_name, titleblock_id=DB.ElementId.InvalidElementId, doc=None
):
    doc = doc or DOCS.doc
    mlogger.debug("Creating sheet: %s - %s", sheet_num, sheet_name)
    mlogger.debug("Titleblock id is: %s", titleblock_id)
    newsheet = DB.ViewSheet.Create(doc, titleblock_id)
    newsheet.Name = sheet_name
    newsheet.SheetNumber = sheet_num
    return newsheet


def create_3d_view(view_name, isometric=True, doc=None):
    doc = doc or DOCS.doc
    nview = query.get_view_by_name(view_name, doc=doc)
    if not nview:
        default_3dview_type = doc.GetDefaultElementTypeId(
            DB.ElementTypeGroup.ViewType3D
        )
        if isometric:
            nview = DB.View3D.CreateIsometric(doc, default_3dview_type)
        else:
            nview = DB.View3D.CreatePerspective(doc, default_3dview_type)

    nview.Name = view_name

    nview.CropBoxActive = False
    nview.CropBoxVisible = False
    if nview.CanToggleBetweenPerspectiveAndIsometric():
        if isometric:
            nview.ToggleToIsometric()
        else:
            nview.ToggleToPerspective()
    return nview


def create_revision_sheetset(
    revisions, name_format="Revision {}", match_any=True, doc=None
):
    doc = doc or DOCS.doc
    # get printed printmanager
    printmanager = doc.PrintManager
    printmanager.PrintRange = DB.PrintRange.Select
    viewsheetsetting = printmanager.ViewSheetSetting

    # collect data
    sheetsnotsorted = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
    viewsheetsets = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ViewSheetSet)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    allviewsheetsets = {vss.Name: vss for vss in viewsheetsets}
    revnums = [str(query.get_rev_number(x)) for x in revisions]
    sheetsetname = name_format.format(", ".join(revnums))

    # find revised sheets
    myviewset = DB.ViewSet()
    check_func = any if match_any else all
    get_elementid_value = get_elementid_value_func()
    for sheet in sheets:
        revs = sheet.GetAllRevisionIds()
        sheet_revids = [get_elementid_value(x) for x in revs]
        if check_func([get_elementid_value(x.Id) in sheet_revids for x in revisions]):
            myviewset.Insert(sheet)
    # needs transaction
    # delete existing sheet set if any
    # create new sheet set
    if sheetsetname in allviewsheetsets.keys():
        viewsheetsetting.CurrentViewSheetSet = allviewsheetsets[sheetsetname]
        viewsheetsetting.Delete()

    viewsheetsetting.CurrentViewSheetSet.Views = myviewset
    viewsheetsetting.SaveAs(sheetsetname)
    return myviewset


def load_family(family_file, doc=None):
    """
    Loads Family from specified file

    Args:
        family_file (str): Required. Fully qualified filename of the Family file, usually ending in .rfa.
        doc (DB.Document): Optional. If not specified DOCS.doc used.

    Returns:
        list[DB.FamilySymbol]: list of all Family symbols. Returns symbols whether the family
        was just loaded or already existed in the document. Returns empty list only if the
        family file cannot be loaded and the family is not found in the document.

    WARNING! This function MUST be used within a transaction!

    Important:
        A non-empty list does not prove Revit loaded the file; it can contain
        symbols from a matching family already in the document. Call
        :func:`load_family_with_result` when the direct Revit load result is
        required.

    Example:
        from pyrevit.revit.db import create, transaction

        family_path = r"C:\\Families\\MyFamily.rfa"
        with transaction.Transaction('Load Family'):
            symbols = create.load_family(family_path)
            if symbols:
                print("Found {} symbol(s)".format(len(symbols)))
                for symbol in symbols:
                    print("  - {}".format(symbol.Family.Name))
            else:
                print("Family file not found or failed to load")

    """
    _, fam_symbols = load_family_with_result(family_file, doc=doc)
    return fam_symbols


def load_family_with_result(family_file, doc=None):
    """Load a family and return Revit's result with its available symbols.

    Args:
        family_file (str): Fully qualified path to the family file.
        doc (DB.Document): Target document. Defaults to the active document.

    Returns:
        tuple[bool, list[DB.FamilySymbol]]: The direct Revit load result and
        symbols from the loaded or matching existing family.

    Important:
        A false result can still include symbols when Revit refuses the file
        because a matching family is already present. Callers that report an
        overwrite must use the boolean result rather than symbol-list truthiness.
    """
    doc = doc or DOCS.doc
    mlogger.debug("Loading family from: %s", family_file)

    fam_symbols = []
    # LoadFamily's out-param needs engine-specific marshaling: an explicit
    # clr.Reference under IronPython, a return tuple under pythonnet
    if IRONPY:
        ret_ref = clr.Reference[DB.Family]()
        loaded = doc.LoadFamily(family_file, FamilyLoaderOptionsHandler(), ret_ref)
        fam = ret_ref.Value
    else:
        loaded, fam = doc.LoadFamily(family_file, FamilyLoaderOptionsHandler(), None)

    if not loaded:
        # Family may already be loaded - check if the out-param has it
        if fam:
            mlogger.debug(
                "Family already loaded, retrieving symbols from document: %s",
                family_file,
            )
        else:
            # Try to find existing family by name from file path
            family_name = coreutils.get_file_name(family_file)
            mlogger.debug(
                "Family may already be loaded, attempting to retrieve by name: %s",
                family_name,
            )
            existing_families = query.get_family(family_name, doc=doc)
            if existing_families:
                # get_family returns FamilySymbol elements, which is what we need
                return False, list(existing_families)
            mlogger.debug(
                "Cannot load Family from file=%s and family not found in document.",
                family_file,
            )
            return False, fam_symbols

    # Collect symbols from the family
    for fam_symbol_id in fam.GetFamilySymbolIds():
        fam_symbol = doc.GetElement(fam_symbol_id)
        if fam_symbol:
            fam_symbols.append(fam_symbol)
    return bool(loaded), fam_symbols


def load_family_symbol(family_file, symbol_name, doc=None):
    """Load one family symbol through the engine-specific out-param bridge.

    Args:
        family_file (str): Fully qualified path to the family file.
        symbol_name (str): Family type name to load.
        doc (DB.Document): Target document. Defaults to the active document.

    Returns:
        bool: True when Revit loads the requested symbol.

    Important:
        The caller must have an open Revit transaction.
    """
    doc = doc or DOCS.doc
    load_options = FamilyLoaderOptionsHandler()
    if IRONPY:
        symbol_ref = clr.Reference[DB.FamilySymbol]()
        return doc.LoadFamilySymbol(family_file, symbol_name, load_options, symbol_ref)
    loaded, _ = doc.LoadFamilySymbol(family_file, symbol_name, load_options, None)
    return loaded


def enable_worksharing(
    levels_workset_name="Shared Levels and Grids",
    default_workset_name="Workset1",
    doc=None,
):
    doc = doc or DOCS.doc
    if not doc.IsWorkshared:
        if doc.CanEnableWorksharing:
            doc.EnableWorksharing(levels_workset_name, default_workset_name)
        else:
            raise PyRevitException(
                "Worksharing can not be enabled. (CanEnableWorksharing is False)"
            )


def create_workset(workset_name, doc=None):
    doc = doc or DOCS.doc
    if not doc.IsWorkshared:
        raise PyRevitException("Document is not workshared.")

    return DB.Workset.Create(doc, workset_name)


def create_filledregion(filledregion_name, fillpattern_element, doc=None):
    doc = doc or DOCS.doc
    filledregion_types = DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType)
    for filledregion_type in filledregion_types:
        if query.get_name(filledregion_type) == filledregion_name:
            raise PyRevitException(
                'Filled Region matching "{}" already exists.'.format(filledregion_name)
            )
    source_filledregion = filledregion_types.FirstElement()
    new_filledregion = source_filledregion.Duplicate(filledregion_name)
    new_filledregion.ForegroundPatternId = fillpattern_element.Id
    return new_filledregion


def create_text_type(
    name,
    font_name=None,
    font_size=0.01042,
    tab_size=0.02084,
    bold=False,
    italic=False,
    underline=False,
    width_factor=1.0,
    doc=None,
):
    doc = doc or DOCS.doc
    tnote_typeid = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
    tnote_type = doc.GetElement(tnote_typeid)
    spec_tnote_type = tnote_type.Duplicate(name)
    if font_name:
        spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_FONT].Set(font_name)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_SIZE].Set(font_size)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_TAB_SIZE].Set(tab_size)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_STYLE_BOLD].Set(1 if bold else 0)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_STYLE_ITALIC].Set(
        1 if italic else 0
    )
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_STYLE_UNDERLINE].Set(
        1 if underline else 0
    )
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_WIDTH_SCALE].Set(width_factor)
    return spec_tnote_type


def create_param_value_filter(
    filter_name,
    param_id,
    param_values,
    evaluator,
    match_any=True,
    case_sensitive=False,
    exclude=False,
    category_list=None,
    doc=None,
):
    doc = doc or DOCS.doc

    rules = None
    param_prov = DB.ParameterValueProvider(param_id)

    # decide how to combine the rules
    logical_merge = DB.LogicalOrFilter if match_any else DB.LogicalAndFilter

    # create the rule set
    get_elementid_value = get_elementid_value_func()
    for pvalue in param_values:
        # grab the evaluator
        param_eval = PARAM_VALUE_EVALUATORS.get(evaluator, None)
        if not param_eval:
            raise PyRevitException("Unknown evaluator")

        # if value is str, eval is expected to be str
        str_eval, num_eval = param_eval
        if isinstance(pvalue, str):
            if HOST_APP.is_newer_than(2022):
                rule = DB.FilterStringRule(param_prov, str_eval(), pvalue)
            else:
                rule = DB.FilterStringRule(
                    param_prov, str_eval(), pvalue, case_sensitive
                )
        # if num_eval is for str, e.g. "contains", or "startswith"
        # convert numeric values to str
        elif isinstance(num_eval, DB.FilterStringRuleEvaluator):
            if isinstance(pvalue, (int, float)):
                if HOST_APP.is_newer_than(2022):
                    rule = DB.FilterStringRule(param_prov, num_eval(), str(pvalue))
                else:
                    rule = DB.FilterStringRule(
                        param_prov, num_eval(), str(pvalue), False
                    )
            elif isinstance(pvalue, DB.ElementId):
                p_id = str(get_elementid_value(pvalue))
                if HOST_APP.is_newer_than(2022):
                    rule = DB.FilterStringRule(param_prov, num_eval(), p_id)
                else:
                    rule = DB.FilterStringRule(param_prov, num_eval(), p_id, False)
        # if value is int, eval is expected to be numeric
        elif isinstance(pvalue, int):
            rule = DB.FilterIntegerRule(param_prov, num_eval(), pvalue)
        # if value is float, eval is expected to be numeric
        elif isinstance(pvalue, float):
            rule = DB.FilterDoubleRule(
                param_prov, num_eval(), pvalue, sys.float_info.epsilon
            )
        # if value is element id, eval is expected to be numeric
        elif isinstance(pvalue, DB.ElementId):
            rule = DB.FilterElementIdRule(param_prov, num_eval(), pvalue)
        if exclude:
            rule = DB.FilterInverseRule(rule)

        if rules:
            rules = logical_merge(rules, DB.ElementParameterFilter(rule))
        else:
            rules = DB.ElementParameterFilter(rule)

    # collect applicable categories
    if category_list:
        category_set = query.get_category_set(category_list, doc=doc)
    else:
        category_set = query.get_all_category_set(doc=doc)

    # filter the applicable categories
    filter_cats = []
    for cat in category_set:
        if DB.ParameterFilterElement.AllRuleParametersApplicable(
            doc, framework.List[DB.ElementId]([cat.Id]), rules
        ):
            filter_cats.append(cat.Id)

    # create filter
    return DB.ParameterFilterElement.Create(
        doc, filter_name, framework.List[DB.ElementId](filter_cats), rules
    )


# model and view creation ----------------------------------------------------
# Points may be DB.XYZ or (x, y[, z]) tuples; lengths may be feet or strings
# that units.parse_length reads, such as 32'-6" or 900mm. Every function here
# changes the document, so call it inside a transaction.

ELEVATION_SIDES = {
    "south": (0.0, -1.0),
    "north": (0.0, 1.0),
    "east": (1.0, 0.0),
    "west": (-1.0, 0.0),
}

_PLAN_VIEW_FAMILIES = {
    "floor": DB.ViewFamily.FloorPlan,
    "ceiling": DB.ViewFamily.CeilingPlan,
    "structural": DB.ViewFamily.StructuralPlan,
}


def to_xyz(point, z=None):
    """Return a DB.XYZ from an XYZ or an (x, y[, z]) tuple.

    Args:
        point (DB.XYZ | tuple): point; tuple values may be length strings.
        z (float, optional): elevation that replaces the point's own Z.

    Returns:
        (DB.XYZ): the point.
    """
    if isinstance(point, DB.XYZ):
        return point if z is None else DB.XYZ(point.X, point.Y, z)
    values = [units.parse_length(value) for value in point]
    own_z = values[2] if len(values) > 2 else 0.0
    return DB.XYZ(values[0], values[1], own_z if z is None else z)


def rectangle_points(x1, y1, x2, y2):
    """Return the corners of an axis-aligned rectangle, counter-clockwise from (x1, y1).

    Edge 0 runs along X at y1, edge 1 along Y at x2, edge 2 along X at y2
    and edge 3 along Y at x1; the roof functions refer to edges by index.
    """
    x1, y1, x2, y2 = [units.parse_length(v) for v in (x1, y1, x2, y2)]
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def _point_pairs(points, closed):
    points = list(points)
    count = len(points) if closed else len(points) - 1
    return [(points[i], points[(i + 1) % len(points)]) for i in range(count)]


def create_curve_loop(points, z=0.0):
    """Return a closed DB.CurveLoop of lines through ``points`` at elevation ``z``."""
    loop = DB.CurveLoop()
    for start, end in _point_pairs(points, closed=True):
        loop.Append(DB.Line.CreateBound(to_xyz(start, z), to_xyz(end, z)))
    return loop


def create_curve_array(points, z=0.0, closed=True):
    """Return a DB.CurveArray of lines through ``points`` at elevation ``z``."""
    curves = DB.CurveArray()
    for start, end in _point_pairs(points, closed):
        curves.Append(DB.Line.CreateBound(to_xyz(start, z), to_xyz(end, z)))
    return curves


def _require_transaction(doc, action):
    if not doc.IsModifiable:
        raise PyRevitException(
            "To {}, start a transaction first "
            "(with revit.Transaction('name'): ...).".format(action)
        )


def _activate(symbol, doc):
    if not symbol.IsActive:
        symbol.Activate()
        doc.Regenerate()
    return symbol


def create_wall(
    start,
    end,
    wall_type,
    level=None,
    height=10.0,
    top_level=None,
    base_offset=0.0,
    structural=False,
    doc=None,
):
    """Create a straight wall along its location line.

    Args:
        start (DB.XYZ | tuple): location line start (plan point).
        end (DB.XYZ | tuple): location line end.
        wall_type (DB.WallType | str): wall type or its name.
        level (DB.Level | str, optional): base level, defaults to the active
            plan's level or the lowest level.
        height (float | str, optional): unconnected height.
        top_level (DB.Level | str, optional): make the top follow this level
            instead of an unconnected height.
        base_offset (float | str, optional): offset from the base level.
        structural (bool, optional): structural wall.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.Wall): the wall.

    Raises:
        PyRevitException: when no transaction is open, or a name doesn't
            match (the message lists the valid names).
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create walls")
    level = query.find_level(level, doc=doc)
    wall_type = query.find_type(DB.WallType, wall_type, doc=doc)
    wall = DB.Wall.Create(
        doc,
        DB.Line.CreateBound(
            to_xyz(start, level.Elevation), to_xyz(end, level.Elevation)
        ),
        wall_type.Id,
        level.Id,
        units.parse_length(height),
        units.parse_length(base_offset),
        False,
        structural,
    )
    if top_level is not None:
        wall.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE).Set(
            query.find_level(top_level, doc=doc).Id
        )
    return wall


def create_walls(
    points, wall_type, level=None, height=10.0, closed=True, top_level=None, doc=None
):
    """Create walls along a polyline, one wall per pair of consecutive points.

    Args:
        points (list): plan points as DB.XYZ or (x, y) tuples.
        wall_type (DB.WallType | str): wall type or its name.
        level (DB.Level | str, optional): base level, defaults as in create_wall.
        height (float | str, optional): unconnected height.
        closed (bool, optional): also join the last point to the first.
        top_level (DB.Level | str, optional): make the tops follow this level.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (list[DB.Wall]): walls, in the order of the points.
    """
    return [
        create_wall(start, end, wall_type, level, height, top_level, doc=doc)
        for start, end in _point_pairs(points, closed)
    ]


def create_floor(
    points, floor_type, level=None, offset=0.0, structural=False, doc=None
):
    """Create a floor on a closed outline.

    Args:
        points (list): outline plan points, in order, not repeating the first.
        floor_type (DB.FloorType | str): floor type or its name.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        offset (float | str, optional): height above the level.
        structural (bool, optional): structural floor.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.Floor): the floor.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create floors")
    level = query.find_level(level, doc=doc)
    floor_type = query.find_type(DB.FloorType, floor_type, doc=doc)
    if hasattr(DB.Floor, "Create"):
        loops = framework.List[DB.CurveLoop](
            [create_curve_loop(points, level.Elevation)]
        )
        floor = DB.Floor.Create(doc, loops, floor_type.Id, level.Id)
    else:
        floor = doc.Create.NewFloor(
            create_curve_array(points, level.Elevation), floor_type, level, structural
        )
    if offset:
        floor.get_Parameter(DB.BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM).Set(
            units.parse_length(offset)
        )
    return floor


def create_ceiling(points, ceiling_type, level=None, offset=8.0, doc=None):
    """Create a ceiling on a closed outline (Revit 2022 and later).

    Args:
        points (list): outline plan points.
        ceiling_type (DB.CeilingType | str): ceiling type or its name.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        offset (float | str, optional): height above the level.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.Ceiling): the ceiling.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create ceilings")
    level = query.find_level(level, doc=doc)
    ceiling_type = query.find_type(DB.CeilingType, ceiling_type, doc=doc)
    loops = framework.List[DB.CurveLoop]([create_curve_loop(points, level.Elevation)])
    ceiling = DB.Ceiling.Create(doc, loops, ceiling_type.Id, level.Id)
    ceiling.get_Parameter(DB.BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM).Set(
        units.parse_length(offset)
    )
    return ceiling


def _new_footprint_roof(footprint, level, roof_type, doc):
    method = doc.Create.GetType().GetMethod("NewFootPrintRoof")
    arguments = framework.Array[framework.System.Object](
        [footprint, level, roof_type, DB.ModelCurveArray()]
    )
    roof = method.Invoke(doc.Create, arguments)
    return roof, arguments[3]


def _nearest_edge(curve, edges):
    start, end = curve.GetEndPoint(0), curve.GetEndPoint(1)

    def distance(p, q):
        return ((p.X - q.X) ** 2 + (p.Y - q.Y) ** 2) ** 0.5

    best, best_distance = None, None
    for index, (a, b) in enumerate(edges):
        a, b = to_xyz(a), to_xyz(b)
        gap = min(
            distance(start, a) + distance(end, b), distance(start, b) + distance(end, a)
        )
        if best_distance is None or gap < best_distance:
            best, best_distance = index, gap
    return best


def create_footprint_roof(
    points, roof_type, level=None, slopes=None, offset=0.0, doc=None
):
    """Create a footprint roof with slopes on chosen edges.

    Args:
        points (list): eave outline plan points, overhangs included.
        roof_type (DB.RoofType | str): roof type or its name.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        slopes (dict, optional): edge index to pitch, where edge ``i`` runs
            from ``points[i]`` to ``points[i + 1]``. A pitch is anything
            units.parse_slope reads (``"8:12"``, ``"30deg"``, rise/run).
            Edges not listed don't define a slope.
        offset (float | str, optional): eave height above the level.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (tuple[DB.FootPrintRoof, list[DB.ModelCurve]]): the roof and the
        model curve of each footprint edge.

    Note:
        Calls NewFootPrintRoof through reflection with a pre-filled
        argument array, because IronPython 3.4 passes null for its out
        parameter and Revit rejects null.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create roofs")
    level = query.find_level(level, doc=doc)
    roof_type = query.find_type(DB.RoofType, roof_type, doc=doc)
    footprint = create_curve_array(points, level.Elevation)
    roof, model_curves = _new_footprint_roof(footprint, level, roof_type, doc)
    if offset:
        roof.get_Parameter(DB.BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM).Set(
            units.parse_length(offset)
        )
    edges = _point_pairs(points, closed=True)
    slopes = slopes or {}
    for model_curve in model_curves:
        pitch = slopes.get(_nearest_edge(model_curve.GeometryCurve, edges))
        roof.set_DefinesSlope(model_curve, pitch is not None)
        if pitch is not None:
            roof.set_SlopeAngle(model_curve, units.parse_slope(pitch))
    doc.Regenerate()
    return roof, list(model_curves)


def _check_roof_rise(roof, level, offset, expected_rise, doc):
    base = query.find_level(level, doc=doc).Elevation + units.parse_length(offset)
    measured = roof.get_BoundingBox(None).Max.Z - base
    if measured < expected_rise * 0.8 - 0.5 or measured > expected_rise * 1.25 + 2.5:
        raise PyRevitException(
            "Roof rise is {:.2f} ft but the pitch and span give {:.2f} ft: the "
            "slopes are on the wrong edges or the pitch is wrong.".format(
                measured, expected_rise
            )
        )


def create_gable_roof(
    x1, y1, x2, y2, roof_type, pitch, ridge="x", level=None, offset=0.0, doc=None
):
    """Create a rectangular gable roof and check its rise.

    Args:
        x1 (float | str): eave outline corner X, overhangs included.
        y1 (float | str): eave outline corner Y.
        x2 (float | str): opposite corner X.
        y2 (float | str): opposite corner Y.
        roof_type (DB.RoofType | str): roof type or its name.
        pitch (float | str): ``"8:12"``, ``"30deg"`` or rise/run.
        ridge (str, optional): ``"x"`` runs the ridge along X (the edges
            parallel to X are the eaves), ``"y"`` along Y.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        offset (float | str, optional): eave height above the level.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.FootPrintRoof): the roof.

    Raises:
        PyRevitException: when the built roof's rise doesn't match the
            pitch, which means the slopes landed on the wrong edges.
    """
    doc = doc or DOCS.doc
    points = rectangle_points(x1, y1, x2, y2)
    eaves = (0, 2) if ridge == "x" else (1, 3)
    roof, _ = create_footprint_roof(
        points, roof_type, level, dict((edge, pitch) for edge in eaves), offset, doc=doc
    )
    (ax, ay), (bx, by) = points[0], points[2]
    span = abs(by - ay) if ridge == "x" else abs(bx - ax)
    _check_roof_rise(roof, level, offset, span / 2.0 * units.parse_slope(pitch), doc)
    return roof


def create_hip_roof(x1, y1, x2, y2, roof_type, pitch, level=None, offset=0.0, doc=None):
    """Create a rectangular hip roof, the same pitch on all four edges; see create_gable_roof."""
    doc = doc or DOCS.doc
    points = rectangle_points(x1, y1, x2, y2)
    roof, _ = create_footprint_roof(
        points,
        roof_type,
        level,
        dict((edge, pitch) for edge in range(4)),
        offset,
        doc=doc,
    )
    (ax, ay), (bx, by) = points[0], points[2]
    span = min(abs(by - ay), abs(bx - ax))
    _check_roof_rise(roof, level, offset, span / 2.0 * units.parse_slope(pitch), doc)
    return roof


def create_shed_roof(
    x1, y1, x2, y2, roof_type, pitch, low_side="south", level=None, offset=0.0, doc=None
):
    """Create a rectangular shed roof sloping down toward one side, and check its rise.

    Args:
        x1 (float | str): eave outline corner X, overhangs included.
        y1 (float | str): eave outline corner Y.
        x2 (float | str): opposite corner X.
        y2 (float | str): opposite corner Y.
        roof_type (DB.RoofType | str): roof type or its name.
        pitch (float | str): ``"4:12"``, ``"15deg"`` or rise/run.
        low_side (str, optional): south, east, north or west.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        offset (float | str, optional): height of the low eave above the level.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.FootPrintRoof): the roof.
    """
    doc = doc or DOCS.doc
    edge = {"south": 0, "east": 1, "north": 2, "west": 3}[low_side]
    points = rectangle_points(x1, y1, x2, y2)
    roof, _ = create_footprint_roof(
        points, roof_type, level, {edge: pitch}, offset, doc=doc
    )
    (ax, ay), (bx, by) = points[0], points[2]
    span = abs(by - ay) if low_side in ("south", "north") else abs(bx - ax)
    _check_roof_rise(roof, level, offset, span * units.parse_slope(pitch), doc)
    return roof


def place_hosted_instance(symbol, host, point, level=None, sill_height=None, doc=None):
    """Place a door, window or other hosted family on a host such as a wall.

    Args:
        symbol (DB.FamilySymbol | str): family type or its name; activated
            when needed.
        host (DB.Element): host element, usually a wall.
        point (DB.XYZ | tuple): plan point on the host's location line.
        level (DB.Level | str, optional): level, defaults to the host's level.
        sill_height (float | str, optional): sill height for windows.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.FamilyInstance): the instance.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "place doors and windows")
    symbol = _activate(query.find_family_symbol(symbol, doc=doc), doc)
    level = (
        query.find_level(level, doc=doc)
        if level is not None
        else doc.GetElement(host.LevelId)
    )
    instance = doc.Create.NewFamilyInstance(
        to_xyz(point, level.Elevation),
        symbol,
        host,
        level,
        DB.Structure.StructuralType.NonStructural,
    )
    if sill_height is not None:
        instance.get_Parameter(DB.BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM).Set(
            units.parse_length(sill_height)
        )
    return instance


def place_family_instance(
    symbol, point, level=None, structural_type=None, rotation=0.0, doc=None
):
    """Place a level-based family instance such as furniture, fixtures or columns.

    Args:
        symbol (DB.FamilySymbol | str): family type or its name; activated
            when needed.
        point (DB.XYZ | tuple): plan insertion point.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        structural_type (DB.Structure.StructuralType, optional): defaults to
            NonStructural.
        rotation (float, optional): rotation in degrees around the insertion
            point.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.FamilyInstance): the instance.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "place family instances")
    symbol = _activate(query.find_family_symbol(symbol, doc=doc), doc)
    level = query.find_level(level, doc=doc)
    location = to_xyz(point, level.Elevation)
    instance = doc.Create.NewFamilyInstance(
        location,
        symbol,
        level,
        structural_type or DB.Structure.StructuralType.NonStructural,
    )
    if rotation:
        axis = DB.Line.CreateBound(location, location + DB.XYZ.BasisZ)
        DB.ElementTransformUtils.RotateElement(
            doc, instance.Id, axis, rotation * 3.141592653589793 / 180.0
        )
    return instance


def create_column(symbol, point, level=None, top_level=None, structural=True, doc=None):
    """Place a column from ``level`` up to ``top_level``; see place_family_instance."""
    doc = doc or DOCS.doc
    column = place_family_instance(
        symbol,
        point,
        level,
        DB.Structure.StructuralType.Column
        if structural
        else DB.Structure.StructuralType.NonStructural,
        doc=doc,
    )
    if top_level is not None:
        column.get_Parameter(DB.BuiltInParameter.FAMILY_TOP_LEVEL_PARAM).Set(
            query.find_level(top_level, doc=doc).Id
        )
    return column


def create_room(
    point, level=None, name=None, number=None, require_enclosed=True, doc=None
):
    """Place a room at a plan point.

    Args:
        point (DB.XYZ | DB.UV | tuple): plan point inside the room.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        name (str, optional): room name.
        number (str, optional): room number.
        require_enclosed (bool, optional): raise when the room isn't
            enclosed. Placing rooms right after the walls is a cheap check
            for gaps in a layout.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.Architecture.Room): the room.

    Raises:
        PyRevitException: when ``require_enclosed`` and the point isn't
            enclosed by room-bounding elements.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create rooms")
    level = query.find_level(level, doc=doc)
    if isinstance(point, DB.UV):
        uv = point
    else:
        xyz = to_xyz(point)
        uv = DB.UV(xyz.X, xyz.Y)
    room = doc.Create.NewRoom(level, uv)
    if name:
        room.Name = name
    if number:
        room.Number = str(number)
    doc.Regenerate()
    if require_enclosed and room.Area <= 0:
        raise PyRevitException(
            "Room {!r} at ({:.2f}, {:.2f}) is not enclosed: a wall or separation "
            "line around it is missing or doesn't meet its neighbour.".format(
                name or "", uv.U, uv.V
            )
        )
    return room


def create_room_separation_lines(points, level=None, view=None, closed=False, doc=None):
    """Create room separation lines, to divide an open plan without walls.

    Args:
        points (list): plan points of the polyline.
        level (DB.Level | str, optional): level, defaults as in create_wall.
        view (DB.ViewPlan, optional): plan view to create them in, defaults
            to a floor plan of the level.
        closed (bool, optional): also join the last point to the first.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (list[DB.ModelCurve]): the separation lines.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create room separation lines")
    level = query.find_level(level, doc=doc)
    view = view or query.find_plan_view(level, doc=doc)
    plane = DB.Plane.CreateByNormalAndOrigin(
        DB.XYZ.BasisZ, DB.XYZ(0, 0, level.Elevation)
    )
    sketch_plane = DB.SketchPlane.Create(doc, plane)
    curves = create_curve_array(points, level.Elevation, closed)
    return list(doc.Create.NewRoomBoundaryLines(sketch_plane, curves, view))


def create_model_lines(points, level=None, closed=False, doc=None):
    """Create model lines along a polyline at a level's elevation.

    Returns:
        (list[DB.ModelCurve]): the model lines.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create model lines")
    level = query.find_level(level, doc=doc)
    plane = DB.Plane.CreateByNormalAndOrigin(
        DB.XYZ.BasisZ, DB.XYZ(0, 0, level.Elevation)
    )
    sketch_plane = DB.SketchPlane.Create(doc, plane)
    return [
        doc.Create.NewModelCurve(
            DB.Line.CreateBound(
                to_xyz(start, level.Elevation), to_xyz(end, level.Elevation)
            ),
            sketch_plane,
        )
        for start, end in _point_pairs(points, closed)
    ]


def _view_family_type(family, doc):
    for view_type in DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType):
        if view_type.ViewFamily == family:
            return view_type
    raise PyRevitException("The document has no {} view type.".format(family))


def unique_view_name(view_name, doc=None):
    """Return ``view_name``, or ``"view_name (2)"`` and so on if it is taken."""
    doc = doc or DOCS.doc
    taken = set(view.Name for view in DB.FilteredElementCollector(doc).OfClass(DB.View))
    candidate, counter = view_name, 2
    while candidate in taken:
        candidate = "{} ({})".format(view_name, counter)
        counter += 1
    return candidate


def _name_view(view, view_name, template, doc):
    view.Name = unique_view_name(view_name, doc=doc)
    if template:
        view.ViewTemplateId = query.find_view(template, doc=doc).Id


def create_plan_view(
    level=None, view_name=None, plan_type="floor", template=None, doc=None
):
    """Create a floor, ceiling or structural plan of a level.

    Args:
        level (DB.Level | str, optional): level, defaults as in create_wall.
        view_name (str, optional): name, made unique; defaults to
            ``"<level> - <plan_type>"``.
        plan_type (str, optional): floor, ceiling or structural.
        template (str | DB.View, optional): view template to apply.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.ViewPlan): the view.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create views")
    level = query.find_level(level, doc=doc)
    if plan_type not in _PLAN_VIEW_FAMILIES:
        raise PyRevitException(
            "plan_type must be floor, ceiling or structural, not {!r}.".format(
                plan_type
            )
        )
    view = DB.ViewPlan.Create(
        doc, _view_family_type(_PLAN_VIEW_FAMILIES[plan_type], doc).Id, level.Id
    )
    _name_view(
        view, view_name or "{} - {}".format(level.Name, plan_type), template, doc
    )
    return view


def create_model_3d_view(
    view_name=None,
    direction="southeast",
    elements=None,
    model_only=True,
    template=None,
    doc=None,
):
    """Create a new isometric 3D view framed on elements or the whole model.

    Unlike create_3d_view, which reuses a view with the same name, this
    always creates a view (with a unique name), hides annotation and fits a
    section box.

    Args:
        view_name (str, optional): name, made unique; defaults to "3D".
        direction (str, optional): where the viewer stands: southeast,
            southwest, northeast, northwest, south, north, east, west, top.
        elements (list, optional): elements to frame with the section box;
            defaults to query.get_model_elements().
        model_only (bool, optional): hide levels, grids and annotation,
            whose extents otherwise dwarf the model in the view.
        template (str | DB.View, optional): view template to apply.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.View3D): the view.
    """
    from pyrevit.revit.db import update

    doc = doc or DOCS.doc
    _require_transaction(doc, "create views")
    view = DB.View3D.CreateIsometric(
        doc, _view_family_type(DB.ViewFamily.ThreeDimensional, doc).Id
    )
    _name_view(view, view_name or "3D", template, doc)
    if model_only:
        update.hide_non_model_categories(view, doc=doc)
    update.orient_3d_view(view, direction)
    update.set_section_box(view, elements, doc=doc)
    return view


def create_section_view(
    start,
    end,
    view_name=None,
    bottom=None,
    top=None,
    depth=10.0,
    template=None,
    doc=None,
):
    """Create a section along a plan line, looking to the left of start -> end.

    A line drawn west to east looks north.

    Args:
        start (DB.XYZ | tuple): section line start.
        end (DB.XYZ | tuple): section line end.
        view_name (str, optional): name, made unique; defaults to "Section".
        bottom (float | str, optional): bottom elevation, defaults to 1 ft
            below the lowest level.
        top (float | str, optional): top elevation, defaults to 10 ft above
            the highest level.
        depth (float | str, optional): far clip distance.
        template (str | DB.View, optional): view template to apply.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.ViewSection): the view.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create views")
    start, end = to_xyz(start), to_xyz(end)
    elevations = sorted(
        level.Elevation for level in DB.FilteredElementCollector(doc).OfClass(DB.Level)
    ) or [0.0]
    bottom = units.parse_length(bottom) if bottom is not None else elevations[0] - 1.0
    top = units.parse_length(top) if top is not None else elevations[-1] + 10.0
    along = DB.XYZ(end.X - start.X, end.Y - start.Y, 0.0)
    if along.IsZeroLength():
        raise PyRevitException("The section's start and end are the same point.")
    half_length = along.GetLength() / 2.0
    direction = along.Normalize()
    transform = DB.Transform.Identity
    transform.Origin = DB.XYZ((start.X + end.X) / 2.0, (start.Y + end.Y) / 2.0, 0.0)
    transform.BasisX = direction
    transform.BasisY = DB.XYZ.BasisZ
    transform.BasisZ = direction.CrossProduct(DB.XYZ.BasisZ)
    box = DB.BoundingBoxXYZ()
    box.Transform = transform
    box.Min = DB.XYZ(-half_length, bottom, -units.parse_length(depth))
    box.Max = DB.XYZ(half_length, top, 0.0)
    view = DB.ViewSection.CreateSection(
        doc, _view_family_type(DB.ViewFamily.Section, doc).Id, box
    )
    _name_view(view, view_name or "Section", template, doc)
    return view


def create_elevation_view(
    side="south", view_name=None, plan=None, offset=10.0, template=None, doc=None
):
    """Create an exterior elevation of the whole model seen from one side.

    Args:
        side (str, optional): south, north, east or west.
        view_name (str, optional): name, made unique; defaults to
            ``"<Side> Elevation"``.
        plan (DB.ViewPlan | str, optional): plan to host the marker, defaults
            to a floor plan of the lowest level.
        offset (float | str, optional): distance of the marker outside the
            model's extents.
        template (str | DB.View, optional): view template to apply.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.ViewSection): the elevation view.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create views")
    if side not in ELEVATION_SIDES:
        raise PyRevitException(
            "side must be one of {}.".format(", ".join(sorted(ELEVATION_SIDES)))
        )
    if plan is None:
        lowest = sorted(
            DB.FilteredElementCollector(doc).OfClass(DB.Level),
            key=lambda l: l.Elevation,
        )[0]
        plan = query.find_plan_view(lowest, doc=doc)
    else:
        plan = query.find_view(plan, doc=doc)
    box = query.get_elements_bounding_box(query.get_model_elements(doc=doc))
    if box is None:
        raise PyRevitException("The model has no elements to elevate.")
    dx, dy = ELEVATION_SIDES[side]
    reach = (
        abs(box.Max.X - box.Min.X) * abs(dx) + abs(box.Max.Y - box.Min.Y) * abs(dy)
    ) / 2.0 + units.parse_length(offset)
    center_x, center_y = (box.Min.X + box.Max.X) / 2.0, (box.Min.Y + box.Max.Y) / 2.0
    marker = DB.ElevationMarker.CreateElevationMarker(
        doc,
        _view_family_type(DB.ViewFamily.Elevation, doc).Id,
        DB.XYZ(center_x + dx * reach, center_y + dy * reach, 0.0),
        plan.Scale,
    )
    wanted = DB.XYZ(dx, dy, 0.0)
    for index in range(4):
        view = marker.CreateElevation(doc, plan.Id, index)
        if view.ViewDirection.IsAlmostEqualTo(wanted):
            _name_view(
                view, view_name or "{} Elevation".format(side.title()), template, doc
            )
            return view
        doc.Delete(view.Id)
    raise PyRevitException("Couldn't create a {}-facing elevation.".format(side))


# drawings --------------------------------------------------------------------

SHEET_ANCHORS = ("top_left", "top_right", "bottom_left", "bottom_right", "center")


def create_dimension(view, references, axis="x", position=0.0, doc=None):
    """Create a linear dimension through references in a plan view.

    Args:
        view (DB.View): view to draw the dimension in.
        references (list[DB.Reference]): at least two references, such as
            face references from query.get_face_references.
        axis (str, optional): ``"x"`` measures along X with the dimension line
            at ``Y = position``; ``"y"`` measures along Y at ``X = position``.
        position (float | str, optional): where the dimension line sits.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.Dimension): the dimension.

    Raises:
        PyRevitException: with fewer than two references, or an unknown axis.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create dimensions")
    if len(references) < 2:
        raise PyRevitException("A dimension needs at least two references.")
    if axis not in ("x", "y"):
        raise PyRevitException("axis must be 'x' or 'y', not {!r}.".format(axis))
    box = query.get_elements_bounding_box(
        query.get_model_elements(doc=doc), padding=20.0
    )
    position = units.parse_length(position)
    if axis == "x":
        line = DB.Line.CreateBound(
            DB.XYZ(box.Min.X, position, 0), DB.XYZ(box.Max.X, position, 0)
        )
    else:
        line = DB.Line.CreateBound(
            DB.XYZ(position, box.Min.Y, 0), DB.XYZ(position, box.Max.Y, 0)
        )
    reference_array = DB.ReferenceArray()
    for reference in references:
        reference_array.Append(reference)
    return doc.Create.NewDimension(view, line, reference_array)


def _tag_point(element, offset):
    location = element.Location
    if isinstance(location, DB.LocationPoint):
        point = location.Point
    elif isinstance(location, DB.LocationCurve):
        point = location.Curve.Evaluate(0.5, True)
    else:
        box = element.get_BoundingBox(None)
        point = (box.Min + box.Max).Divide(2.0)
    facing = getattr(element, "FacingOrientation", None)
    if offset and facing is not None:
        point = point + facing.Multiply(offset)
    return point


def tag_elements(view, elements, offset=0.0, tag_type=None, leader=False, doc=None):
    """Tag elements by category in a view.

    Args:
        view (DB.View): view to tag in.
        elements (list[DB.Element]): elements to tag.
        offset (float | str, optional): move each tag this far along the
            element's facing direction (doors and windows); negative moves
            it the other way, into the room.
        tag_type (DB.FamilySymbol | str, optional): tag type or its name;
            defaults to the category's default tag.
        leader (bool, optional): draw a leader.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (list[DB.IndependentTag]): the tags.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "tag elements")
    tag_type = (
        query.find_family_symbol(tag_type, doc=doc) if tag_type is not None else None
    )
    offset = units.parse_length(offset)
    tags = []
    for element in elements:
        tag = DB.IndependentTag.Create(
            doc,
            view.Id,
            DB.Reference(element),
            leader,
            DB.TagMode.TM_ADDBY_CATEGORY,
            DB.TagOrientation.Horizontal,
            _tag_point(element, offset),
        )
        if tag_type is not None:
            tag.ChangeTypeId(tag_type.Id)
        tags.append(tag)
    return tags


def create_room_tags(view, rooms=None, tag_type=None, doc=None):
    """Tag rooms at their location points in a plan view.

    Args:
        view (DB.ViewPlan): plan view.
        rooms (list[DB.Architecture.Room], optional): rooms to tag, defaults
            to the placed rooms visible in the view.
        tag_type (DB.FamilySymbol | str, optional): room tag type or its name,
            such as ``"Room Tag With Area"``.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (list[DB.Architecture.RoomTag]): the tags.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "tag rooms")
    if rooms is None:
        rooms = [
            room
            for room in DB.FilteredElementCollector(doc, view.Id).OfCategory(
                DB.BuiltInCategory.OST_Rooms
            )
            if room.Location is not None
        ]
    tag_type = (
        query.find_family_symbol(tag_type, category="OST_RoomTags", doc=doc)
        if tag_type is not None
        else None
    )
    tags = []
    for room in rooms:
        point = room.Location.Point
        tag = doc.Create.NewRoomTag(
            DB.LinkElementId(room.Id), DB.UV(point.X, point.Y), view.Id
        )
        if tag_type is not None:
            tag.ChangeTypeId(tag_type.Id)
        tags.append(tag)
    return tags


def create_schedule(
    category,
    fields,
    view_name=None,
    sort_by=None,
    totals=None,
    itemized=True,
    grand_total=True,
    doc=None,
):
    """Create a schedule of a category with the named fields.

    Args:
        category (str | DB.BuiltInCategory | DB.Category): category, such as
            ``"OST_Rooms"``.
        fields (list[str]): field names in column order, as shown in Revit's
            schedule properties (``"Number"``, ``"Name"``, ``"Area"``).
        view_name (str, optional): schedule name, made unique.
        sort_by (list[str], optional): field names to sort by, in order.
        totals (list[str], optional): numeric fields to total.
        itemized (bool, optional): list every element instead of grouping.
        grand_total (bool, optional): show a grand total row with a count.
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.ViewSchedule): the schedule.

    Raises:
        PyRevitException: when a field name isn't schedulable for the
            category; the message lists the available fields.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "create schedules")
    category = query.get_category(category, doc=doc)
    if category is None:
        raise PyRevitException("No such category.")
    schedule = DB.ViewSchedule.CreateSchedule(doc, category.Id)
    if view_name:
        schedule.Name = unique_view_name(view_name, doc=doc)
    definition = schedule.Definition
    available = dict(
        (field.GetName(doc), field) for field in definition.GetSchedulableFields()
    )
    wanted = list(fields) + [
        name for name in (sort_by or []) + (totals or []) if name not in fields
    ]
    missing = [name for name in wanted if name not in available]
    if missing:
        raise PyRevitException(
            "Fields not schedulable for {}: {}. Available: {}.".format(
                category.Name, ", ".join(missing), ", ".join(sorted(available))
            )
        )
    added = {}
    for name in fields:
        added[name] = definition.AddField(available[name])
    for name in sort_by or []:
        definition.AddSortGroupField(DB.ScheduleSortGroupField(added[name].FieldId))
    for name in totals or []:
        added[name].DisplayType = DB.ScheduleFieldDisplayType.Totals
    definition.IsItemized = itemized
    definition.ShowGrandTotal = grand_total
    definition.ShowGrandTotalTitle = grand_total
    definition.ShowGrandTotalCount = grand_total
    return schedule


def _sheet_area(sheet, doc):
    titleblock = (
        DB.FilteredElementCollector(doc, sheet.Id)
        .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
        .FirstElement()
    )
    if titleblock is not None:
        box = titleblock.get_BoundingBox(sheet)
        return box.Min, box.Max
    outline = sheet.Outline
    return (
        DB.XYZ(outline.Min.U, outline.Min.V, 0),
        DB.XYZ(outline.Max.U, outline.Max.V, 0),
    )


def place_on_sheet(sheet, view, anchor="top_left", margin=0.1, doc=None):
    """Place a view or schedule on a sheet, aligned to a corner of the title block.

    Args:
        sheet (DB.ViewSheet): sheet.
        view (DB.View | DB.ViewSchedule): view or schedule to place. A view
            can be on one sheet only; schedules can repeat.
        anchor (str, optional): top_left, top_right, bottom_left,
            bottom_right or center of the title block (the sheet outline
            when it has none).
        margin (float | str, optional): gap between the placed box and the
            title block edge, in sheet feet (0.1 ft is 1.2 in).
        doc (DB.Document, optional): document, defaults to the active one.

    Returns:
        (DB.Viewport | DB.ScheduleSheetInstance): the placed viewport or
        schedule instance.

    Raises:
        PyRevitException: when the view can't be added to the sheet, for
            example because it is already on another sheet.
    """
    doc = doc or DOCS.doc
    _require_transaction(doc, "place views on sheets")
    if anchor not in SHEET_ANCHORS:
        raise PyRevitException(
            "anchor must be one of {}.".format(", ".join(SHEET_ANCHORS))
        )
    margin = units.parse_length(margin)
    is_schedule = isinstance(view, DB.ViewSchedule)
    if is_schedule:
        placed = DB.ScheduleSheetInstance.Create(doc, sheet.Id, view.Id, DB.XYZ.Zero)
    else:
        if not DB.Viewport.CanAddViewToSheet(doc, sheet.Id, view.Id):
            raise PyRevitException(
                "View {!r} can't be placed on sheet {}; it may already be on a sheet.".format(
                    view.Name, sheet.SheetNumber
                )
            )
        placed = DB.Viewport.Create(doc, sheet.Id, view.Id, DB.XYZ.Zero)
    doc.Regenerate()
    if is_schedule:
        box = placed.get_BoundingBox(sheet)
        low, high = box.Min, box.Max
    else:
        outline = placed.GetBoxOutline()
        low, high = outline.MinimumPoint, outline.MaximumPoint
    area_low, area_high = _sheet_area(sheet, doc)
    width, height = high.X - low.X, high.Y - low.Y
    if anchor == "center":
        target_x = (area_low.X + area_high.X - width) / 2.0
        target_y = (area_low.Y + area_high.Y - height) / 2.0
    else:
        target_x = (
            area_low.X + margin
            if anchor.endswith("left")
            else area_high.X - margin - width
        )
        target_y = (
            area_high.Y - margin - height
            if anchor.startswith("top")
            else area_low.Y + margin
        )
    move = DB.XYZ(target_x - low.X, target_y - low.Y, 0)
    if is_schedule:
        placed.Point = placed.Point + move
    else:
        placed.SetBoxCenter(placed.GetBoxCenter() + move)
    doc.Regenerate()
    return placed
