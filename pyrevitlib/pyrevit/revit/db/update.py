"""Helper functions to update info and elements in Revit."""
import os.path as op

from pyrevit import HOST_APP, DOCS
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit.db import query
from pyrevit.compat import get_elementid_value_func


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
    doc = doc or DOCS.doc
    get_elementid_value = get_elementid_value_func()
    # make sure revisions is a list
    if not isinstance(revisions, list):
        revisions = [revisions]
    updated_sheets = []
    if revisions:
        # get sheets if not available
        for sheet in sheets or query.get_sheets(doc=doc):
            addrevs = set([get_elementid_value(x)
                           for x in sheet.GetAdditionalRevisionIds()])
            for rev in revisions:
                # skip issued revisions
                if not rev.Issued:
                    if state:
                        addrevs.add(get_elementid_value(rev.Id))
                    elif get_elementid_value(rev.Id) in addrevs:
                        addrevs.remove(get_elementid_value(rev.Id))
            rev_elids = [DB.ElementId(x) for x in addrevs]
            sheet.SetAdditionalRevisionIds(List[DB.ElementId](rev_elids))
            updated_sheets.append(sheet)
    return updated_sheets


def update_revision_alphanumeric(token_list, prefix='', postfix='', doc=None):
    doc = doc or DOCS.doc
    alphalist = List[str]()
    for token in token_list:
        alphalist.Add(str(token))
    alpha_cfg = DB.AlphanumericRevisionSettings(alphalist, prefix, postfix)
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.SetAlphanumericRevisionSettings(alpha_cfg)


def update_revision_numeric(starting_int, prefix='', postfix='', doc=None):
    doc = doc or DOCS.doc
    num_cfg = DB.NumericRevisionSettings(starting_int, prefix, postfix)
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.SetNumericRevisionSettings(num_cfg)


def update_revision_numbering(per_sheet=False, doc=None):
    doc = doc or DOCS.doc
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.RevisionNumbering = \
        DB.RevisionNumbering.PerSheet if per_sheet else \
        DB.RevisionNumbering.PerProject


def update_param_value(rvt_param, value):
    if not rvt_param.IsReadOnly:
        if rvt_param.StorageType == DB.StorageType.String:
            rvt_param.Set(str(value) if value else "")
        else:
            rvt_param.SetValueString(str(value))


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
    doc = doc or DOCS.doc
    DB.WorksetTable.RenameWorkset(doc, workset.Id, new_name)


def update_linked_keynotes(doc=None):
    doc = doc or DOCS.doc
    ktable = DB.KeynoteTable.GetKeynoteTable(doc)
    ktable.Reload(None)


# https://forum.dynamobim.com/t/load-assemblycodetable-keynotetable/23944/2
def set_keynote_file(keynote_file, doc=None):
    doc = doc or DOCS.doc
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


def set_crop_region(view, curve_loops):
    """Sets crop region to a view.

    Args:
        view (DB.View): view to change
        curve_loops (list[DB.CurveLoop]): list of curve loops
    """
    if not isinstance(curve_loops, list):
        curve_loops = [curve_loops]

    crop_active_saved = view.CropBoxActive
    view.CropBoxActive = True
    crsm = view.GetCropRegionShapeManager()
    for cloop in curve_loops:
        if HOST_APP.is_newer_than(2015):
            crsm.SetCropShape(cloop)
        else:
            crsm.SetCropRegionShape(cloop)
    view.CropBoxActive = crop_active_saved


def set_active_workset(workset_id, doc=None):
    """Set active workset.

    Args:
        workset_id (DB.WorksetId): target workset id
        doc (DB.Document, optional): target document. defaults to active
    """
    doc = doc or DOCS.doc
    if doc.IsWorkshared:
        workset_table = doc.GetWorksetTable()
        workset_table.SetActiveWorksetId(workset_id)
