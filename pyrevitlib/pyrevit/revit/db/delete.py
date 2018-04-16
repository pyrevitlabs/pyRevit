from pyrevit import HOST_APP, PyRevitException
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit import query


def clear_sheet_revisions(sheet):
    sheet.SetAdditionalRevisionIds(List[DB.ElementId]([]))
