"""Helper functions to update info and elements in Revit."""

from pyrevit import HOST_APP, PyRevitException
from pyrevit.compat import safe_strtype
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit import query


def update_sheet_revisions(revisions, sheets=None, state=True, doc=None):
    doc or HOST_APP.doc

    # make sure revisions is a list
    if not isinstance(revisions, list):
        revisions = [revisions]

    updated_sheets = []
    if revisions:
        # get sheets if not available
        for s in sheets or query.get_sheets(doc=doc):
            addrevs = set([x.IntegerValue
                           for x in s.GetAdditionalRevisionIds()])
            for r in revisions:
                # skip issued revisions
                if not r.Issued:
                    if state:
                        addrevs.add(r.Id.IntegerValue)
                    elif r.Id.IntegerValue in addrevs:
                        addrevs.remove(r.Id.IntegerValue)

            rev_elids = [DB.ElementId(x) for x in addrevs]
            s.SetAdditionalRevisionIds(List[DB.ElementId](rev_elids))
            updated_sheets.append(s)

    return updated_sheets


def update_revision_alphanumeric(token_list, prefix='', postfix='', doc=None):
    doc = doc or HOST_APP.doc
    alphalist = List[str]()
    for token in token_list:
        alphalist.Add(str(token))
    alpha_cfg = DB.AlphanumericRevisionSettings(alphalist, prefix, postfix)
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.SetAlphanumericRevisionSettings(alpha_cfg)


def update_revision_numeric(starting_int, prefix='', postfix='', doc=None):
    doc = doc or HOST_APP.doc
    num_cfg = DB.NumericRevisionSettings(starting_int, prefix, postfix)
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.SetNumericRevisionSettings(num_cfg)
