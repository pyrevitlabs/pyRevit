from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit.db import ensure


def clear_sheet_revisions(sheet):
    sheet.SetAdditionalRevisionIds(List[DB.ElementId]([]))


def delete_elements(element_list, doc=None):
    doc = doc or HOST_APP.doc
    element_ids = ensure.ensure_element_ids(element_list)
    return doc.Delete(List[DB.ElementId](element_ids))


def delete_revision(rvt_rev, doc=None):
    doc = doc or HOST_APP.doc
    return doc.Delete(rvt_rev.Id)
