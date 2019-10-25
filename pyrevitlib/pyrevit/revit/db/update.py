"""Helper functions to update info and elements in Revit."""
import os.path as op

from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit.db import query


def set_name(element, new_name):
    # grab viewname correctly
    if isinstance(element, DB.View):
        if HOST_APP.is_newer_than('2019', or_equal=True):
            element.Name = new_name
        else:
            element.ViewName = new_name
    else:
        element.Name = new_name


def update_sheet_revisions(revisions, sheets=None, state=True, doc=None):
    doc = doc or HOST_APP.doc
    # make sure revisions is a list
    if not isinstance(revisions, list):
        revisions = [revisions]

    updated_sheets = []
    if revisions:
        # get sheets if not available
        for sheet in sheets or query.get_sheets(doc=doc):
            addrevs = set([x.IntegerValue
                           for x in sheet.GetAdditionalRevisionIds()])
            for rev in revisions:
                # skip issued revisions
                if not rev.Issued:
                    if state:
                        addrevs.add(rev.Id.IntegerValue)
                    elif rev.Id.IntegerValue in addrevs:
                        addrevs.remove(rev.Id.IntegerValue)

            rev_elids = [DB.ElementId(x) for x in addrevs]
            sheet.SetAdditionalRevisionIds(List[DB.ElementId](rev_elids))
            updated_sheets.append(sheet)

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


def update_revision_numbering(per_sheet=False, doc=None):
    doc = doc or HOST_APP.doc
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.RevisionNumbering = \
        DB.RevisionNumbering.PerSheet if per_sheet else \
        DB.RevisionNumbering.PerProject


def update_param_value(rvt_param, value):
    if not rvt_param.IsReadOnly:
        if rvt_param.StorageType == DB.StorageType.String:
            rvt_param.Set(str(value))
        else:
            rvt_param.SetValueString(str(value))


def update_param_by_prop(rvt_param, prop_key_value):
    if rvt_param.StorageType == DB.StorageType.Integer:
        rvt_param.Set(prop_key_value.value or 0)
    elif rvt_param.StorageType == DB.StorageType.Double:
        rvt_param.Set(prop_key_value.value or 0.0)
    elif rvt_param.StorageType == DB.StorageType.ElementId:
        rvt_param.Set(prop_key_value.value)
    else:
        rvt_param.Set(prop_key_value.value or "")


def toggle_category_visibility(view, subcat, hidden=None):
    if HOST_APP.is_older_than(2018):
        if hidden is None:
            hidden = not view.GetVisibility(subcat.Id)
        view.SetVisibility(subcat.Id, hidden)
    else:
        if hidden is None:
            hidden = not view.GetCategoryHidden(subcat.Id)
        view.SetCategoryHidden(subcat.Id, hidden)


def rename_workset(workset, new_name, doc=None):
    doc = doc or HOST_APP.doc
    DB.WorksetTable.RenameWorkset(doc, workset.Id, new_name)


def update_linked_keynotes(doc=None):
    doc = doc or HOST_APP.doc
    ktable = DB.KeynoteTable.GetKeynoteTable(doc)
    ktable.Reload(None)


# https://forum.dynamobim.com/t/load-assemblycodetable-keynotetable/23944/2
def set_keynote_file(keynote_file, doc=None):
    doc = doc or HOST_APP.doc
    if op.exists(keynote_file):
        mpath = \
            DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(keynote_file)
        keynote_exres = DB.ExternalResourceReference.CreateLocalResource(
            doc,
            DB.ExternalResourceTypes.BuiltInExternalResourceTypes.KeynoteTable,
            mpath,
            DB.PathType.Absolute)
        knote_table = DB.KeynoteTable.GetKeynoteTable(doc)
        knote_table.LoadFrom(keynote_exres, DB.KeyBasedTreeEntriesLoadResults())
