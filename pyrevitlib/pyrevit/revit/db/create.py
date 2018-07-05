from pyrevit import HOST_APP, PyRevitException
from pyrevit.framework import clr
from pyrevit.coreutils.logger import get_logger
from pyrevit import DB
from pyrevit.revit import query


logger = get_logger(__name__)


# http://www.revitapidocs.com/2018.1/5da8e3c5-9b49-f942-02fc-7e7783fe8f00.htm
class FamilyLoaderOptionsHandler(DB.IFamilyLoadOptions):
    def OnFamilyFound(self, familyInUse, overwriteParameterValues):
        """A method called when the family was found in the target document."""
        return True

    def OnSharedFamilyFound(self,
                            sharedFamily,
                            familyInUse,
                            source,
                            overwriteParameterValues):
        source = DB.FamilySource.Family
        overwriteParameterValues = True
        return True


def create_shared_param(param_id_or_name, category_list, builtin_param_group,
                        type_param=False, allow_vary_betwen_groups=False,
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
        new_rev.NumberType = DB.RevisionNumberType.None #noqa
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
            logger.debug('Revision already exists: {} {}'
                         .format(src_rev.RevisionDate,
                                 src_rev.Description))
        else:
            logger.debug('Creating revision: {} {}'
                         .format(src_rev.RevisionDate,
                                 src_rev.Description))
            create_revision(description=src_rev.Description,
                            by=src_rev.IssuedBy,
                            to=src_rev.IssuedTo,
                            date=src_rev.RevisionDate,
                            doc=dest_doc)


def create_sheet(sheet_num, sheet_name,
                 titleblock_id=DB.ElementId.InvalidElementId, doc=None):
    doc = doc or HOST_APP.doc
    newsheet = DB.ViewSheet.Create(doc, titleblock_id)
    newsheet.Name = sheet_name
    newsheet.SheetNumber = sheet_num
    return newsheet


def create_3d_view(view_name, isometric=True, doc=None):
    doc = doc or HOST_APP.doc
    nview = query.get_view_by_name(view_name)
    if not nview:
        default_3dview_type = \
            doc.GetDefaultElementTypeId(DB.ElementTypeGroup.ViewType3D)
        if isometric:
            nview = DB.View3D.CreateIsometric(doc, default_3dview_type)
        else:
            nview = DB.View3D.CreatePerspective(doc, default_3dview_type)
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
    for sheet in sheets:
        revs = sheet.GetAllRevisionIds()
        sheet_revids = [x.IntegerValue for x in revs]
        if all([x.Id.IntegerValue in sheet_revids
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
    logger.debug('Loading family from: {}'.format(family_file))
    ret_ref = clr.Reference[DB.Family]()
    return doc.LoadFamily(family_file, FamilyLoaderOptionsHandler(), ret_ref)
