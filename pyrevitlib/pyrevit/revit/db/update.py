"""Helper functions to update info and elements in Revit."""

import os.path as op

from pyrevit import DOCS, PyRevitException
from pyrevit.framework import List
from pyrevit import DB
from pyrevit.revit.db import query
from pyrevit.compat import get_elementid_value_func


def set_name(element, new_name):
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
            addrevs = set(
                [get_elementid_value(x) for x in sheet.GetAdditionalRevisionIds()]
            )
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


def update_revision_alphanumeric(token_list, prefix="", postfix="", doc=None):
    doc = doc or DOCS.doc
    alphalist = List[str]()
    for token in token_list:
        alphalist.Add(str(token))
    alpha_cfg = DB.AlphanumericRevisionSettings(alphalist, prefix, postfix)
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.SetAlphanumericRevisionSettings(alpha_cfg)


def update_revision_numeric(starting_int, prefix="", postfix="", doc=None):
    doc = doc or DOCS.doc
    num_cfg = DB.NumericRevisionSettings(starting_int, prefix, postfix)
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.SetNumericRevisionSettings(num_cfg)


def update_revision_numbering(per_sheet=False, doc=None):
    doc = doc or DOCS.doc
    rev_cfg = DB.RevisionSettings.GetRevisionSettings(doc)
    rev_cfg.RevisionNumbering = (
        DB.RevisionNumbering.PerSheet if per_sheet else DB.RevisionNumbering.PerProject
    )


def update_param_value(rvt_param, value):
    if not rvt_param.IsReadOnly:
        if rvt_param.StorageType == DB.StorageType.String:
            rvt_param.Set(str(value) if value else "")
        else:
            rvt_param.SetValueString(str(value))


def toggle_category_visibility(view, subcat, hidden=None):
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
        mpath = DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(keynote_file)
        keynote_exres = DB.ExternalResourceReference.CreateLocalResource(
            doc,
            DB.ExternalResourceTypes.BuiltInExternalResourceTypes.KeynoteTable,
            mpath,
            DB.PathType.Absolute,
        )
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
        crsm.SetCropShape(cloop)
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


VIEW_DIRECTIONS = {
    "southeast": (-1.0, 1.0, -1.0),
    "southwest": (1.0, 1.0, -1.0),
    "northeast": (-1.0, -1.0, -1.0),
    "northwest": (1.0, -1.0, -1.0),
    "south": (0.0, 1.0, -0.6),
    "north": (0.0, -1.0, -0.6),
    "east": (-1.0, 0.0, -0.6),
    "west": (1.0, 0.0, -0.6),
    "top": (0.0, 0.0001, -1.0),
}


def attach_wall_tops(walls, target):
    """Attach the tops of walls to a roof, floor or ceiling when supported.

    Gable end walls attached to a roof follow its rake, so the gable needs
    no separate infill.

    Args:
        walls (DB.Wall | list[DB.Wall]): walls to attach.
        target (DB.Element): roof, floor or ceiling above the walls.

    Raises:
        PyRevitException: when the active Revit API does not expose wall
            attachment.
    """
    if isinstance(walls, DB.Wall):
        walls = [walls]
    for wall in walls:
        attach = getattr(wall, "AddAttachment", None)
        if attach is None:
            raise PyRevitException(
                "Wall attachment is unavailable in this Revit version. "
                "Use an untrimmed wall or model the gable end explicitly."
            )
        attach(target.Id, DB.AttachmentLocation.Top)
    target.Document.Regenerate()


def _view_orientation(forward, eye=None):
    forward = forward.Normalize()
    right = forward.CrossProduct(DB.XYZ.BasisZ)
    if right.IsZeroLength():
        right = DB.XYZ.BasisX
    up = right.Normalize().CrossProduct(forward).Normalize()
    return DB.ViewOrientation3D(eye or forward.Negate().Multiply(1000.0), up, forward)


def orient_3d_view(view3d, direction="southeast"):
    """Point a 3D view from a named direction.

    Args:
        view3d (DB.View3D): 3D view.
        direction (str, optional): where the viewer stands: southeast,
            southwest, northeast, northwest, south, north, east, west, top.
            Sides look down at about 35 degrees.
    """
    if direction not in VIEW_DIRECTIONS:
        raise PyRevitException(
            "direction must be one of {}.".format(", ".join(sorted(VIEW_DIRECTIONS)))
        )
    view3d.SetOrientation(_view_orientation(DB.XYZ(*VIEW_DIRECTIONS[direction])))


def set_3d_view_camera(view3d, eye, target):
    """Point a 3D view from ``eye`` toward ``target`` (points as DB.XYZ)."""
    view3d.SetOrientation(_view_orientation(target - eye, eye))


def set_section_box(view3d, elements=None, padding=2.0, doc=None):
    """Fit a 3D view's section box around elements and turn it on.

    Args:
        view3d (DB.View3D): 3D view.
        elements (list[DB.Element], optional): elements to frame, defaults to
            query.get_model_elements().
        padding (float, optional): clearance around the elements, in feet.
        doc (DB.Document, optional): document, defaults to the view's.

    Raises:
        PyRevitException: when none of the elements has a bounding box.
    """
    doc = doc or view3d.Document
    box = query.get_elements_bounding_box(
        elements or query.get_model_elements(doc=doc), padding=padding
    )
    if box is None:
        raise PyRevitException("Nothing to frame: no elements with a bounding box.")
    view3d.SetSectionBox(box)
    view3d.IsSectionBoxActive = True


def crop_view_to_elements(view, elements=None, padding=3.0, doc=None):
    """Crop a plan, section or elevation to elements and turn the crop on.

    Args:
        view (DB.View): view with a crop box.
        elements (list[DB.Element], optional): elements to show, defaults to
            query.get_model_elements().
        padding (float, optional): clearance around the elements, in feet.
        doc (DB.Document, optional): document, defaults to the view's.
    """
    doc = doc or view.Document
    box = query.get_elements_bounding_box(elements or query.get_model_elements(doc=doc))
    if box is None:
        raise PyRevitException("Nothing to crop to: no elements with a bounding box.")
    to_view = view.CropBox.Transform.Inverse
    corners = [
        to_view.OfPoint(DB.XYZ(x, y, z))
        for x in (box.Min.X, box.Max.X)
        for y in (box.Min.Y, box.Max.Y)
        for z in (box.Min.Z, box.Max.Z)
    ]
    crop = view.CropBox
    crop.Min = DB.XYZ(
        min(c.X for c in corners) - padding,
        min(c.Y for c in corners) - padding,
        crop.Min.Z,
    )
    crop.Max = DB.XYZ(
        max(c.X for c in corners) + padding,
        max(c.Y for c in corners) + padding,
        crop.Max.Z,
    )
    view.CropBox = crop
    view.CropBoxActive = True
    view.CropBoxVisible = False


def hide_non_model_categories(view, doc=None):
    """Hide every non-model category (levels, grids, annotation) in a view."""
    doc = doc or view.Document
    for category in doc.Settings.Categories:
        if category.CategoryType != DB.CategoryType.Model and view.CanCategoryBeHidden(
            category.Id
        ):
            view.SetCategoryHidden(category.Id, True)


def hide_categories(view, categories, doc=None):
    """Hide categories in a view.

    Args:
        view (DB.View): view.
        categories (list): categories as names, BuiltInCategory values or
            ``"OST_..."`` strings; anything query.get_category accepts.
        doc (DB.Document, optional): document, defaults to the view's.

    Raises:
        PyRevitException: when a category doesn't exist or can't be hidden
            in the view.
    """
    doc = doc or view.Document
    for value in categories:
        category = query.get_category(value, doc=doc)
        if category is None:
            raise PyRevitException("No category {!r}.".format(value))
        if not view.CanCategoryBeHidden(category.Id):
            raise PyRevitException(
                "Category {!r} can't be hidden in view {!r}.".format(
                    category.Name, view.Name
                )
            )
        view.SetCategoryHidden(category.Id, True)
