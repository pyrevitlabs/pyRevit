"""Helper functions to update info and elements in Revit."""

from pyrevit import HOST_APP, PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit.framework import List
from pyrevit import revit, DB


def update_sheet_revisions(revisions, sheets, state=True, doc=None):
    doc or HOST_APP.doc

    # get revisions if not set
    revisions = revisions or revit.query.get_revisions()
    if type(revisions) is not list:
        revisions = [revisions]
    # get sheets if not available
    sheets = sheets or revit.query.get_sheets()

    cloudedsheets = []
    updated_sheets = []
    for s in sheets:
        for r in revisions:
            revs = set([x.IntegerValue for x in s.GetAllRevisionIds()])
            addrevs = set([x.IntegerValue
                           for x in s.GetAdditionalRevisionIds()])
            cloudrevs = revs - addrevs
            if r.Id.IntegerValue in cloudrevs:
                cloudedsheets.append(s)
                continue

            if state:
                addrevs.add(r.Id.IntegerValue)
            elif r.Id.IntegerValue in addrevs:
                addrevs.remove(r.Id.IntegerValue)

            rev_elids = [DB.ElementId(x) for x in addrevs]
            s.SetAdditionalRevisionIds(List[DB.ElementId](rev_elids))
            updated_sheets.append(s)

    return updated_sheets
