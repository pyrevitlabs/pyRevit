"""Database objects creation functions."""
import sys

from pyrevit import HOST_APP, DOCS, PyRevitException
from pyrevit import framework
from pyrevit.framework import clr
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB
from pyrevit.revit.db import query
from pyrevit.compat import get_elementid_value_func


#pylint: disable=W0703,C0302,C0103
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
    def __init__(self, overwriteParameterValues=True):
        self._overwriteParameterValues = overwriteParameterValues

    def OnFamilyFound(self, familyInUse, overwriteParameterValues): #pylint: disable=W0613
        """A method called when the family was found in the target document."""
        overwriteParameterValues.Value = self._overwriteParameterValues
        return True

    def OnSharedFamilyFound(self,
                            sharedFamily, #pylint: disable=W0613
                            familyInUse, #pylint: disable=W0613
                            source, #pylint: disable=W0613
                            overwriteParameterValues): #pylint: disable=W0613
        source.Value = DB.FamilySource.Family
        overwriteParameterValues.Value = self._overwriteParameterValues
        return True


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    """Handle copy and paste errors."""

    def OnDuplicateTypeNamesFound(self, args):  #pylint: disable=unused-argument
        """Use destination model types if duplicate."""
        return DB.DuplicateTypeAction.UseDestinationTypes


def create_param_from_definition(param_def,
                                 category_list,
                                 builtin_param_group,
                                 type_param=False,
                                 allow_vary_betwen_groups=False, #pylint: disable=unused-argument
                                 doc=None):
    doc = doc or DOCS.doc
    # verify and create category set
    if category_list:
        category_set = query.get_category_set(category_list, doc=doc)
    else:
        category_set = query.get_all_category_set(doc=doc)

    if not category_set:
        raise PyRevitException('Can not create category set.')

    # create binding
    if type_param:
        new_binding = \
            HOST_APP.app.Create.NewTypeBinding(category_set)
    else:
        new_binding = \
            HOST_APP.app.Create.NewInstanceBinding(category_set)

    # FIXME: set allow_vary_betwen_groups
    # param_def.SetAllowVaryBetweenGroups(doc, allow_vary_betwen_groups)
    # insert the binding
    doc.ParameterBindings.Insert(param_def,
                                 new_binding,
                                 builtin_param_group)
    return True


def create_shared_param(param_id_or_name,
                        category_list,
                        builtin_param_group,
                        type_param=False,
                        allow_vary_betwen_groups=False,
                        doc=None):
    doc = doc or DOCS.doc
    # get define shared parameters
    # this is where we grab the ExternalDefinition for the parameter
    msp_list = query.get_defined_sharedparams()
    param_def = None
    for msp in msp_list:
        if msp == param_id_or_name:
            param_def = msp.param_def
    if not param_def:
        raise PyRevitException('Can not find shared parameter.')

    # now create the binding for this definition
    return create_param_from_definition(
        param_def,
        category_list,
        builtin_param_group=builtin_param_group,
        type_param=type_param,
        allow_vary_betwen_groups=allow_vary_betwen_groups,
        doc=doc)



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


def create_revision(description=None, by=None, to=None, date=None,
                    alphanum=False, nonum=False, doc=None):
    new_rev = DB.Revision.Create(doc or DOCS.doc)
    new_rev.Description = description
    new_rev.IssuedBy = by or ''
    new_rev.IssuedTo = to or ''
    if alphanum:
        new_rev.NumberType = DB.RevisionNumberType.Alphanumeric
    if nonum:
        new_rev.NumberType = coreutils.get_enum_none(DB.RevisionNumberType)
    new_rev.RevisionDate = date or ''
    return new_rev


def copy_elements(element_ids, src_doc, dest_doc):
    cp_options = DB.CopyPasteOptions()
    cp_options.SetDuplicateTypeNamesHandler(CopyUseDestination())

    if element_ids:
        DB.ElementTransformUtils.CopyElements(
            src_doc,
            framework.List[DB.ElementId](element_ids),
            dest_doc, None, cp_options
            )

    return True


def copy_revisions(revisions, src_doc, dest_doc):
    if revisions is None:
        all_src_revs = query.get_revisions(doc=src_doc)
    else:
        all_src_revs = revisions

    for src_rev in all_src_revs:
        # get an updated list of revisions
        if any([query.compare_revisions(x, src_rev)
                for x in query.get_revisions(doc=dest_doc)]):
            mlogger.debug('Revision already exists: %s %s',
                          src_rev.RevisionDate, src_rev.Description)
        else:
            mlogger.debug('Creating revision: %s %s',
                          src_rev.RevisionDate, src_rev.Description)
            create_revision(description=src_rev.Description,
                            by=src_rev.IssuedBy,
                            to=src_rev.IssuedTo,
                            date=src_rev.RevisionDate,
                            doc=dest_doc)


def copy_all_revisions(src_doc, dest_doc):
    copy_revisions(None, src_doc=src_doc, dest_doc=dest_doc)


def copy_viewtemplates(viewtemplates, src_doc, dest_doc):
    if viewtemplates is None:
        all_viewtemplates = query.get_all_view_templates(doc=src_doc)
    else:
        all_viewtemplates = viewtemplates

    vtemp_ids = [x.Id for x in all_viewtemplates]
    copy_elements(vtemp_ids, src_doc=src_doc, dest_doc=dest_doc)


def create_sheet(sheet_num, sheet_name,
                 titleblock_id=DB.ElementId.InvalidElementId, doc=None):
    doc = doc or DOCS.doc
    mlogger.debug('Creating sheet: %s - %s', sheet_num, sheet_name)
    mlogger.debug('Titleblock id is: %s', titleblock_id)
    newsheet = DB.ViewSheet.Create(doc, titleblock_id)
    newsheet.Name = sheet_name
    newsheet.SheetNumber = sheet_num
    return newsheet


def create_3d_view(view_name, isometric=True, doc=None):
    doc = doc or DOCS.doc
    nview = query.get_view_by_name(view_name, doc=doc)
    if not nview:
        default_3dview_type = \
            doc.GetDefaultElementTypeId(DB.ElementTypeGroup.ViewType3D)
        if isometric:
            nview = DB.View3D.CreateIsometric(doc, default_3dview_type)
        else:
            nview = DB.View3D.CreatePerspective(doc, default_3dview_type)

    if HOST_APP.is_newer_than('2019', or_equal=True):
        nview.Name = view_name
    else:
        nview.ViewName = view_name

    nview.CropBoxActive = False
    nview.CropBoxVisible = False
    if nview.CanToggleBetweenPerspectiveAndIsometric():
        if isometric:
            nview.ToggleToIsometric()
        else:
            nview.ToggleToPerspective()
    return nview


def create_revision_sheetset(revisions,
                             name_format='Revision {}',
                             match_any=True,
                             doc=None):
    doc = doc or DOCS.doc
    # get printed printmanager
    printmanager = doc.PrintManager
    printmanager.PrintRange = DB.PrintRange.Select
    viewsheetsetting = printmanager.ViewSheetSetting

    # collect data
    sheetsnotsorted = DB.FilteredElementCollector(doc)\
                        .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                        .WhereElementIsNotElementType()\
                        .ToElements()

    sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)
    viewsheetsets = DB.FilteredElementCollector(doc)\
                      .OfClass(DB.ViewSheetSet)\
                      .WhereElementIsNotElementType()\
                      .ToElements()

    allviewsheetsets = {vss.Name: vss for vss in viewsheetsets}
    revnums = [str(query.get_rev_number(x)) for x in revisions]
    sheetsetname = name_format.format(', '.join(revnums))

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
        viewsheetsetting.CurrentViewSheetSet = \
            allviewsheetsets[sheetsetname]
        viewsheetsetting.Delete()

    viewsheetsetting.CurrentViewSheetSet.Views = myviewset
    viewsheetsetting.SaveAs(sheetsetname)
    return myviewset


def load_family(family_file, doc=None):
    doc = doc or DOCS.doc
    mlogger.debug('Loading family from: %s', family_file)
    ret_ref = clr.Reference[DB.Family]()
    return doc.LoadFamily(family_file, FamilyLoaderOptionsHandler(), ret_ref)


def enable_worksharing(levels_workset_name='Shared Levels and Grids',
                       default_workset_name='Workset1',
                       doc=None):
    doc = doc or DOCS.doc
    if not doc.IsWorkshared:
        if doc.CanEnableWorksharing:
            doc.EnableWorksharing(levels_workset_name, default_workset_name)
        else:
            raise PyRevitException('Worksharing can not be enabled. '
                                   '(CanEnableWorksharing is False)')


def create_workset(workset_name, doc=None):
    doc = doc or DOCS.doc
    if not doc.IsWorkshared:
        raise PyRevitException('Document is not workshared.')

    return DB.Workset.Create(doc, workset_name)


def create_filledregion(filledregion_name, fillpattern_element, doc=None):
    doc = doc or DOCS.doc
    filledregion_types = DB.FilteredElementCollector(doc) \
                           .OfClass(DB.FilledRegionType)
    for filledregion_type in filledregion_types:
        if query.get_name(filledregion_type) == filledregion_name:
            raise PyRevitException('Filled Region matching \"{}\" already '
                                   'exists.'.format(filledregion_name))
    source_filledregion = filledregion_types.FirstElement()
    new_filledregion = source_filledregion.Duplicate(filledregion_name)
    if HOST_APP.is_newer_than(2019, or_equal=True) : 
        new_filledregion.ForegroundPatternId = fillpattern_element.Id
    else: 
        new_filledregion.FillPatternId = fillpattern_element.Id
    return new_filledregion


def create_text_type(name,
                     font_name=None,
                     font_size=0.01042,
                     tab_size=0.02084,
                     bold=False,
                     italic=False,
                     underline=False,
                     width_factor=1.0,
                     doc=None):
    doc = doc or DOCS.doc
    tnote_typeid = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
    tnote_type = doc.GetElement(tnote_typeid)
    spec_tnote_type = tnote_type.Duplicate(name)
    if font_name:
        spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_FONT].Set(font_name)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_SIZE].Set(font_size)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_TAB_SIZE].Set(tab_size)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_STYLE_BOLD]\
        .Set(1 if bold else 0)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_STYLE_ITALIC]\
        .Set(1 if italic else 0)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_STYLE_UNDERLINE]\
        .Set(1 if underline else 0)
    spec_tnote_type.Parameter[DB.BuiltInParameter.TEXT_WIDTH_SCALE]\
        .Set(width_factor)
    return spec_tnote_type


def create_param_value_filter(filter_name,
                              param_id,
                              param_values,
                              evaluator,
                              match_any=True,
                              case_sensitive=False,
                              exclude=False,
                              category_list=None,
                              doc=None):
    doc = doc or DOCS.doc

    if HOST_APP.is_newer_than(2019, or_equal=True):
        rules = None
    else:
        rules = framework.List[DB.FilterRule]()
    param_prov = DB.ParameterValueProvider(param_id)

    # decide how to combine the rules
    logical_merge = \
        DB.LogicalOrFilter if match_any else DB.LogicalAndFilter

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
                rule = DB.FilterStringRule(param_prov,
                                        str_eval(),
                                        pvalue)
            else:
                rule = DB.FilterStringRule(param_prov,
                                        str_eval(),
                                        pvalue,
                                        case_sensitive)
        # if num_eval is for str, e.g. "contains", or "startswith"
        # convert numeric values to str
        elif isinstance(num_eval, DB.FilterStringRuleEvaluator):
            if isinstance(pvalue, (int, float)):
                if HOST_APP.is_newer_than(2022):
                    rule = DB.FilterStringRule(param_prov,
                                            num_eval(),
                                            str(pvalue))
                else:
                    rule = DB.FilterStringRule(param_prov,
                                            num_eval(),
                                            str(pvalue),
                                            False)
            elif isinstance(pvalue, DB.ElementId):
                p_id = str(get_elementid_value(pvalue))
                if HOST_APP.is_newer_than(2022):
                    rule = DB.FilterStringRule(param_prov,
                                            num_eval(),
                                            p_id)
                else:
                    rule = DB.FilterStringRule(param_prov,
                                            num_eval(),
                                            p_id,
                                            False)
        # if value is int, eval is expected to be numeric
        elif isinstance(pvalue, int):
            rule = DB.FilterIntegerRule(param_prov,
                                        num_eval(),
                                        pvalue)
        # if value is float, eval is expected to be numeric
        elif isinstance(pvalue, float):
            rule = DB.FilterDoubleRule(param_prov,
                                       num_eval(),
                                       pvalue,
                                       sys.float_info.epsilon)
        # if value is element id, eval is expected to be numeric
        elif isinstance(pvalue, DB.ElementId):
            rule = DB.FilterElementIdRule(param_prov,
                                          num_eval(),
                                          pvalue)
        if exclude:
            rule = DB.FilterInverseRule(rule)

        if HOST_APP.is_newer_than(2019, or_equal=True):
            if rules:
                rules = logical_merge(rules, DB.ElementParameterFilter(rule))
            else:
                rules = DB.ElementParameterFilter(rule)
        else:
            rules.Add(rule)

    # collect applicable categories
    if category_list:
        category_set = query.get_category_set(category_list, doc=doc)
    else:
        category_set = query.get_all_category_set(doc=doc)

    # filter the applicable categories
    filter_cats = []
    for cat in category_set:
        if DB.ParameterFilterElement.AllRuleParametersApplicable(
                doc,
                framework.List[DB.ElementId]([cat.Id]),
                rules
            ):
            filter_cats.append(cat.Id)

    # create filter
    return DB.ParameterFilterElement.Create(
        doc,
        filter_name,
        framework.List[DB.ElementId](filter_cats),
        rules
        )
