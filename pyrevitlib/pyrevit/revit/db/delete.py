"""Database elements deletion functions."""
from pyrevit import DOCS
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit.db import query
from pyrevit.revit.db import ensure


def clear_sheet_revisions(sheet):
    sheet.SetAdditionalRevisionIds(List[DB.ElementId]([]))


def delete_elements(element_list, doc=None):
    doc = doc or DOCS.doc
    element_ids = ensure.ensure_element_ids(element_list)
    return doc.Delete(List[DB.ElementId](element_ids))


def delete_revision(rvt_rev, doc=None):
    doc = doc or DOCS.doc
    return doc.Delete(rvt_rev.Id)


def reset_subcategories(doc=None, purgable=False, filterfunc=None):
    # get subcategories
    cats_to_delete = query.get_subcategories(doc=doc,
                                             purgable=purgable,
                                             filterfunc=filterfunc)
    doc.Delete(List[DB.ElementId]([x.Id for x in cats_to_delete]))
    del cats_to_delete
