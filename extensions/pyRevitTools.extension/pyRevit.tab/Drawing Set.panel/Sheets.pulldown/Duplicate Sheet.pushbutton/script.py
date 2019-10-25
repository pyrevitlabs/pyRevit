"""Duplicates selected sheet N-times. 
Takes Sheet parameters, TitleBlock with parameters, Legends and Detail views,
increments sheet number. Selects newly created sheets in the end."""
#pylint: disable=import-error,invalid-name,broad-except,missing-docstring
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script
import sheet_tools_utils

logger = script.get_logger()

# taken from 'Match properties' tool
def match_sheet_prop(target, src_props):
    """Match given properties on target instance or type"""
    for pkv in src_props:
        logger.debug("Applying %s", pkv.name)
        # find parameter
        dparam = target.LookupParameter(pkv.name)
        if dparam and pkv.datatype == dparam.StorageType:
            try:
                revit.update.update_param_by_prop(dparam, pkv)
            except Exception as setex:
                logger.warning(
                    "Error applying value to: %s | %s",
                    pkv.name, setex)
                continue
        else:
            logger.debug("Parameter \"%s\"not found on target.", pkv.name)


def is_placable_viewport(viewport):
    if isinstance(viewport, DB.ScheduleSheetInstance):
        view = revit.doc.GetElement(viewport.ScheduleId)
    else:
        view = revit.doc.GetElement(viewport.ViewId)
    return sheet_tools_utils.is_placable(view)


def is_param_not_sheet_number(param):
    if isinstance(param.Definition, DB.InternalDefinition):
        return int(param.Definition.BuiltInParameter) not in [
            int(DB.BuiltInParameter.SHEET_NUMBER),
            int(DB.BuiltInParameter.VIEWER_SHEET_NUMBER)]
    return True


def collect_taken_sheet_numbers():
    all_sheets = DB.FilteredElementCollector(revit.doc) \
                 .OfClass(DB.ViewSheet) \
                 .WhereElementIsNotElementType() \
                 .ToElements()
    return [s.SheetNumber for s in all_sheets]


def get_title_block_ids(sheet):
    return DB.FilteredElementCollector(revit.doc, sheet.Id) \
        .OfCategory(DB.BuiltInCategory.OST_TitleBlocks) \
        .WhereElementIsNotElementType() \
        .ToElementIds()


def get_placable_viewports(sheet):
    sheet_viewports = [revit.doc.GetElement(x)\
                       for x in sheet.GetAllViewports()]
    all_sheeted_schedules = DB.FilteredElementCollector(revit.doc)\
                            .OfClass(DB.ScheduleSheetInstance)\
                            .ToElements()
    sheet_viewports.extend([x for x in all_sheeted_schedules \
                            if x.OwnerViewId == sheet.Id])
    return [vp for vp in sheet_viewports if is_placable_viewport(vp)]


#main
src_sheet = forms.select_sheets(title='Select source Sheet', multiple=False,
                                use_selection=True)
if not src_sheet:
    script.exit()
# ask for count of copies
count = None
while count is None:
    count_str = forms.ask_for_string(default='1', prompt='Enter count:',
                                     title='Duplicate Sheet')
    if count_str is None:
        script.exit()
    try:
        count = int(count_str)
    # pylint: disable=bare-except
    except:
        forms.alert('Count must be integer number')

# collect sheet instance properties
src_sheet_params = revit.query.get_param_defs(src_sheet,
                                              include_type=False,
                                              filterfunc= \
                                                  is_param_not_sheet_number)
src_sheet_props = []
for src_sheet_param in src_sheet_params:
    src_sheet_props.append(revit.query.get_prop_value_by_def(src_sheet,
                                                             src_sheet_param))
src_viewports = get_placable_viewports(src_sheet)
src_title_block_ids = get_title_block_ids(src_sheet)
src_number = src_sheet.get_Parameter(DB.BuiltInParameter.SHEET_NUMBER) \
                            .AsString()
taken_numbers = set(collect_taken_sheet_numbers())
last_number = None

# create duplicates
created_sheets = []
with revit.Transaction('Duplicate Sheet'):
    for i in range(count):
        logger.debug(i)
        # with revit.Transaction('Duplicate Sheet') as t:
        try:
            # create sheet, copy viewports and title blocks
            if src_sheet.IsPlaceholder:
                new_sheet = DB.ViewSheet.CreatePlaceholder(revit.doc)
            else:
                new_sheet = DB.ViewSheet.Create(revit.doc,
                                                DB.ElementId.InvalidElementId)
            logger.debug("new_sheet.Id: {}".format(new_sheet.Id.IntegerValue))
           
            # set sheet properties
            match_sheet_prop(new_sheet, src_sheet_props)
            logger.debug("match_sheet_prop done")
            
            # try to set closest sheet number (e.g. source=A101, new=A102)
            new_number_param = new_sheet.get_Parameter(
                DB.BuiltInParameter.SHEET_NUMBER)
            new_number_auto = new_number_param.AsString()
            logger.debug("new_number_auto:{}".format(new_number_auto))
            new_number = last_number or src_number
            while new_number in taken_numbers:
                new_number = coreutils.increment_str(new_number)
            if new_number != new_number_auto:
                new_sheet.get_Parameter(DB.BuiltInParameter.SHEET_NUMBER) \
                    .Set(new_number)
                logger.debug("new_sheet set number:{}".format(new_number))
            last_number = new_number
            
            # copy title blocks
            DB.ElementTransformUtils.CopyElements(src_sheet,
                                                  src_title_block_ids,
                                                  new_sheet,
                                                  DB.Transform.Identity,
                                                  DB.CopyPasteOptions())
            logger.debug("copy title blocks done")
            
            # copy 'placeable' viewports
            for src_vp in src_viewports:
                sheet_tools_utils.copy_viewport(src_vp, new_sheet)
            logger.debug("copy title viewports done")
            
            taken_numbers.add(last_number)
            created_sheets.append(new_sheet)
        except Exception as exc:
            logger.error(exc)

# select or activate sheets
if len(created_sheets) == 1:
    revit.uidoc.active_view = created_sheets[0]
elif len(created_sheets) > 1:
    revit.get_selection().set_to([s.Id for s in created_sheets])
forms.alert("{} sheets created.".format(len(created_sheets)))
