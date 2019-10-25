#pylint: disable=import-error,invalid-name
from pyrevit import revit, DB
from pyrevit.coreutils import logger

mlogger = logger.get_logger(__name__)

def is_placable(view):
    """Returns True if a viewport can be placed more than once"""
    if view and view.ViewType and view.ViewType in [DB.ViewType.Schedule,
                                                    DB.ViewType.DraftingView,
                                                    DB.ViewType.Legend,
                                                    DB.ViewType.CostReport,
                                                    DB.ViewType.LoadsReport,
                                                    DB.ViewType.ColumnSchedule,
                                                    DB.ViewType.PanelSchedule]:
        return True
    return False


def update_if_placed(vport, exst_vps):
    """Updates type and location of existing viewport"""
    for exst_vp in exst_vps:
        if vport.ViewId == exst_vp.ViewId:
            exst_vp.SetBoxCenter(vport.GetBoxCenter())
            exst_vp.ChangeTypeId(vport.GetTypeId())
            return True
    return False


def copy_viewport(src_vp, trg_sheet, existing_vps=(), existing_schedules=()):
    if isinstance(src_vp, DB.Viewport):
        src_view = revit.doc.GetElement(src_vp.ViewId)
        # check if viewport already exists
        # and update location and type
        if update_if_placed(src_vp, existing_vps):
            return
        # if not, create a new viewport
        elif is_placable(src_view):
            new_vp = \
                DB.Viewport.Create(revit.doc,
                                   trg_sheet.Id,
                                   src_vp.ViewId,
                                   src_vp.GetBoxCenter())

            new_vp.ChangeTypeId(src_vp.GetTypeId())
        else:
            logger.warning('Skipping %s. This view type '
                           'can not be placed on '
                           'multiple sheets.',
                           revit.query.get_name(src_view))
    elif isinstance(src_vp, DB.ScheduleSheetInstance):
        # check if schedule already exists
        # and update location
        for exist_sched in existing_schedules:
            if src_vp.ScheduleId == exist_sched.ScheduleId:
                exist_sched.Point = src_vp.Point
                break
        # if not, place the schedule
        else:
            DB.ScheduleSheetInstance.Create(revit.doc,
                                            trg_sheet.Id,
                                            src_vp.ScheduleId,
                                            src_vp.Point)
