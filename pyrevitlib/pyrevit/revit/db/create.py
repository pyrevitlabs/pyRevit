from pyrevit import HOST_APP, PyRevitException
from pyrevit import framework
from pyrevit.framework import clr
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB
from pyrevit.revit import db
from pyrevit.revit.db import query


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# http://www.revitapidocs.com/2018.1/5da8e3c5-9b49-f942-02fc-7e7783fe8f00.htm
class FamilyLoaderOptionsHandler(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues): #pylint: disable=W0613
        """A method called when the family was found in the target document."""
        return True

    def OnSharedFamilyFound(self,
                            sharedFamily, #pylint: disable=W0613
                            familyInUse, #pylint: disable=W0613
                            source, #pylint: disable=W0613
                            overwriteParameterValues): #pylint: disable=W0613
        source = DB.FamilySource.Family
        overwriteParameterValues = True
        return True


def create_shared_param(param_id_or_name, category_list, builtin_param_group,
                        type_param=False, allow_vary_betwen_groups=False,  #pylint: disable=W0613
                        doc=None):
    doc = doc or HOST_APP.doc
    msp_list = query.get_defined_sharedparams()
    param_def = None
    for msp in msp_list:
        if msp == param_id_or_name:
            param_def = msp.param_def

    if not param_def:
        raise PyRevitException('Can not find shared parameter.')

    if category_list:
        category_set = query.get_category_set(category_list, doc=doc)
    else:
        category_set = query.get_all_category_set(doc=doc)

    if not category_set:
        raise PyRevitException('Can not create category set.')

    if type_param:
        new_binding = \
            HOST_APP.app.Create.NewTypeBinding(category_set)
    else:
        new_binding = \
            HOST_APP.app.Create.NewInstanceBinding(category_set)

    doc.ParameterBindings.Insert(param_def,
                                 new_binding,
                                 builtin_param_group)
    return True


def create_new_project(template=None, imperial=True):
    if template:
        return HOST_APP.app.NewProjectDocument(template)
    else:
        units = DB.UnitSystem.Imperial if imperial else DB.UnitSystem.Metric
        return HOST_APP.app.NewProjectDocument(units)


def create_revision(description=None, by=None, to=None, date=None,
                    alphanum=False, nonum=False, doc=None):
    new_rev = DB.Revision.Create(doc or HOST_APP.doc)
    new_rev.Description = description
    new_rev.IssuedBy = by or ''
    new_rev.IssuedTo = to or ''
    if alphanum:
        new_rev.NumberType = DB.RevisionNumberType.Alphanumeric
    if nonum:
        new_rev.NumberType = coreutils.get_enum_none(DB.RevisionNumberType)
    new_rev.RevisionDate = date or ''
    return new_rev


def copy_revisions(src_doc, dest_doc, revisions=None):
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


def create_sheet(sheet_num, sheet_name,
                 titleblock_id=DB.ElementId.InvalidElementId, doc=None):
    doc = doc or HOST_APP.doc
    mlogger.debug('Creating sheet: %s - %s', sheet_num, sheet_name)
    mlogger.debug('Titleblock id is: %s', titleblock_id)
    newsheet = DB.ViewSheet.Create(doc, titleblock_id)
    newsheet.Name = sheet_name
    newsheet.SheetNumber = sheet_num
    return newsheet


def create_3d_view(view_name, isometric=True, doc=None):
    doc = doc or HOST_APP.doc
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
    doc = doc or HOST_APP.doc
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
    for sheet in sheets:
        revs = sheet.GetAllRevisionIds()
        sheet_revids = [x.IntegerValue for x in revs]
        if check_func([x.Id.IntegerValue in sheet_revids
                       for x in revisions]):
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
    doc = doc or HOST_APP.doc
    mlogger.debug('Loading family from: %s', family_file)
    ret_ref = clr.Reference[DB.Family]()
    return doc.LoadFamily(family_file, FamilyLoaderOptionsHandler(), ret_ref)


def enable_worksharing(levels_workset_name='Shared Levels and Grids',
                       default_workset_name='Workset1',
                       doc=None):
    doc = doc or HOST_APP.doc
    if not doc.IsWorkshared:
        if doc.CanEnableWorksharing:
            doc.EnableWorksharing(levels_workset_name, default_workset_name)
        else:
            raise PyRevitException('Worksharing can not be enabled. '
                                '(CanEnableWorksharing is False)')


def create_workset(workset_name, doc=None):
    doc = doc or HOST_APP.doc
    if not doc.IsWorkshared:
        raise PyRevitException('Document is not workshared.') 

    return DB.Workset.Create(doc, workset_name)


def create_filledregion(filledregion_name, fillpattern_element, doc=None):
    doc = doc or HOST_APP.doc
    filledregion_types = DB.FilteredElementCollector(doc) \
                           .OfClass(DB.FilledRegionType)
    for filledregion_type in filledregion_types:
        if query.get_name(filledregion_type) == filledregion_name:
            raise PyRevitException('Filled Region matching \"{}\" already '
                                   'exists.'.format(filledregion_name))
    source_filledregion = filledregion_types.FirstElement()
    new_filledregion = source_filledregion.Duplicate(filledregion_name)
    new_filledregion.FillPatternId = fillpattern_element.Id
    return new_filledregion


def create_text_type(name,
                     font_name=None,
                     font_size=0.01042,
                     tab_size=0.02084,
                     bold=False,
                     italic=False,
                     underline=False,
                     with_factor=1.0,
                     doc=None):
    doc = doc or HOST_APP.doc
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
        .Set(1 if with_factor else 0)
    return spec_tnote_type
