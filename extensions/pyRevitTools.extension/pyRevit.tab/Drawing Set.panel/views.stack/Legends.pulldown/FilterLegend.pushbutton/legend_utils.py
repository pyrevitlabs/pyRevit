# -*- coding: utf-8 -*-
"""Shared drawing helpers for the Filter Legend tool."""

from pyrevit import DB
from pyrevit.framework import List


def create_text_note(
    doc,
    view,
    x,
    y,
    text,
    text_type_id,
    horizontal_align=DB.HorizontalTextAlignment.Left,
):
    """Create a single-line, left-aligned TextNote at (x, y) in the view.

    TextNote.Create's `position` argument is documented to land at the
    *top-left corner of the note's bounding box only for left-aligned
    text* -- that's the default, but it's a property of the note, not a
    guarantee of the API call. A project/template could change what
    "new text note" defaults to, which would silently break every (x, y)
    we ever pass in. So the alignment is pinned explicitly here instead
    of trusted implicitly, keeping the "position == top-left" contract
    true regardless of project/template.

    Args:
        doc: Document
        view: destination View (must accept detail-level annotations,
            e.g. a Legend view)
        x: X coordinate in feet
        y: Y coordinate in feet (top of the note, given left alignment)
        text: string content (empty string if falsy)
        text_type_id: ElementId of the TextNoteType to use
        horizontal_align: DB.HorizontalTextAlignment to enforce (default
            Left, which is what every position calculation here assumes)

    Returns:
        TextNote: the created element
    """
    origin = DB.XYZ(x, y, 0.0)
    note = DB.TextNote.Create(doc, view.Id, origin, text or "", text_type_id)
    doc.Regenerate()  # needs to be called before TextNote can be queried for data
    if note.HorizontalAlignment != horizontal_align:
        note.HorizontalAlignment = horizontal_align
    return note


def create_swatch_region(doc, view, x, y, width, height):
    """Create a small rectangular FilledRegion used as a color swatch.

    Uses the first available FilledRegionType in the document purely as a
    boundary/host element -- its actual visual appearance is overridden
    per-instance afterwards via View.SetElementOverrides, so the specific
    type picked here does not matter.

    Args:
        doc: Document
        view: destination View
        x: bottom-left X coordinate in feet
        y: bottom-left Y coordinate in feet
        width: swatch width in feet (> 0)
        height: swatch height in feet (> 0)

    Returns:
        FilledRegion: the created element

    Raises:
        ValueError: if no FilledRegionType exists in the project
    """
    frt_id = (
        DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType).FirstElementId()
    )
    if frt_id is None or frt_id == DB.ElementId.InvalidElementId:
        raise ValueError("No FilledRegionType found in the project.")

    p1 = DB.XYZ(x, y, 0.0)
    p2 = DB.XYZ(x + width, y, 0.0)
    p3 = DB.XYZ(x + width, y + height, 0.0)
    p4 = DB.XYZ(x, y + height, 0.0)

    loop = DB.CurveLoop()
    loop.Append(DB.Line.CreateBound(p1, p2))
    loop.Append(DB.Line.CreateBound(p2, p3))
    loop.Append(DB.Line.CreateBound(p3, p4))
    loop.Append(DB.Line.CreateBound(p4, p1))

    return DB.FilledRegion.Create(doc, frt_id, view.Id, List[DB.CurveLoop]([loop]))


def text_note_vertical_extent(note, view):
    """Measure a TextNote's *actual*, as-rendered vertical footprint.

    Font size, leading/line-spacing, and any text-background margin are
    all controlled by the TextNoteType, which varies per project. Rather
    than assume a fixed row height matches whatever type/size a given
    project happens to use, we measure the real bounding box of the note
    we just created and align everything else (swatch position, next
    row's Y) against that.

    Args:
        note: a just-created TextNote (must belong to `view`)
        view: the view the note was created in

    Returns:
        tuple: (top_y, bottom_y, height) in feet, or None if Revit can't
            report a bounding box for this note/view (e.g. hidden)
    """
    bbox = note.get_BoundingBox(view)

    if bbox is None:
        return None
    top_y = max(bbox.Min.Y, bbox.Max.Y)
    bottom_y = min(bbox.Min.Y, bbox.Max.Y)
    return top_y, bottom_y, top_y - bottom_y


def text_note_horizontal_extent(note, view):
    """Measure a TextNote's actual, as-rendered horizontal footprint.

    Mirrors text_note_vertical_extent, but for width. Character widths
    depend on the TextNoteType's font/size, which varies per project,
    so the real bounding box is measured rather than assumed.

    Args:
        note: a just-created TextNote (must belong to `view`)
        view: the view the note was created in

    Returns:
        tuple: (left_x, right_x, width) in feet, or None if Revit can't
            report a bounding box for this note/view.
    """
    bbox = note.get_BoundingBox(view)
    if bbox is None:
        return None
    left_x = min(bbox.Min.X, bbox.Max.X)
    right_x = max(bbox.Min.X, bbox.Max.X)
    return left_x, right_x, right_x - left_x


def autofit_column_widths(doc, view, notes_by_column, base_offsets, min_gap=0.0):
    """Widen any column whose rendered text overflows its configured
    width, shifting every column after it right to compensate.

    Must be called after *every* row (header + data) has been created --
    only then is the widest note in each column known. Moves notes in
    place via ElementTransformUtils rather than deleting/recreating
    them, so per-instance state (overrides etc.) is preserved.

    Args:
        doc: Document
        view: the Legend view the notes live in
        notes_by_column: list of lists of TextNote, one inner list per
            column, left to right, e.g. [name_notes, param_notes,
            value_notes]. Each inner list holds every note placed in
            that column across all rows.
        base_offsets: list of the X offsets (feet) each column was
            originally created at -- same length/order as
            notes_by_column.
        min_gap: minimum horizontal gap (feet) to leave after the
            widest note in a column before the next column starts.
            Only applied when that column actually overflows its
            configured width.

    Returns:
        list: the new X offsets actually applied, same length as
            base_offsets (offsets[0] is always unchanged -- nothing to
            the left of the first column to push into).
    """
    col_widths = []
    for notes in notes_by_column:
        widest = 0.0
        for note in notes:
            extent = text_note_horizontal_extent(note, view)
            if extent is not None:
                widest = max(widest, extent[2])
        col_widths.append(widest)

    new_offsets = [base_offsets[0]]
    for i in range(len(base_offsets) - 1):
        configured_width = base_offsets[i + 1] - base_offsets[i]
        needed_width = max(configured_width, col_widths[i] + min_gap)
        new_offsets.append(new_offsets[i] + needed_width)

    for i, notes in enumerate(notes_by_column):
        delta = new_offsets[i] - base_offsets[i]
        if abs(delta) < 1e-9:
            continue
        translation = DB.XYZ(delta, 0.0, 0.0)
        ids = List[DB.ElementId]([note.Id for note in notes])
        DB.ElementTransformUtils.MoveElements(doc, ids, translation)

    return new_offsets


def create_legend_row(
    doc,
    view,
    y_top,
    text_type_id,
    columns,
    swatch_col_width=None,
    swatch_height=None,
    min_row_height=0.0,
):
    """Create one row of left-aligned TextNotes, optionally with a color
    swatch, and report how far the next row's top should be offset.

    All text columns are placed with their top at `y_top`. The row's
    real height is then measured from the first note's bounding box
    (every note in a row shares the same text type/size, so its height
    is representative), and the swatch -- if any -- is vertically
    *centered* on that measured text, rather than assumed to already
    line up with it. This is what keeps swatch and text aligned no
    matter which TextNoteType/font a given project uses.

    Args:
        doc: Document
        view: destination Legend view
        y_top: Y coordinate (feet) of the row's top edge
        text_type_id: ElementId of the TextNoteType to use for this row
        columns: list of (x, text) tuples, one per text column, left to
            right
        swatch_col_width: width in feet of the swatch column, or None to
            skip drawing a swatch for this row (e.g. a header row)
        swatch_height: desired swatch height in feet; defaults to the
            measured text height if not given
        min_row_height: minimum vertical advance regardless of measured
            text/swatch height (pass the user's configured row height
            here so short text/small fonts don't collapse row spacing)

    Returns:
        tuple: (notes, swatch_or_None, row_height) -- row_height is how
            far (in feet, positive) the next row's y_top should move
            down from this one
    """
    notes = [
        create_text_note(doc, view, x, y_top, text, text_type_id) for x, text in columns
    ]

    extent = text_note_vertical_extent(notes[0], view)
    if extent is not None:
        top_y, bottom_y, text_height = extent
    else:
        # Fall back to the configured minimum if Revit can't report a
        # bounding box for some reason -- keeps the tool from crashing,
        # at the cost of using the assumed height for just this row.
        top_y, bottom_y, text_height = y_top, y_top - min_row_height, min_row_height

    row_height = max(text_height, min_row_height)

    swatch = None
    if swatch_col_width is not None:
        swatch_h = swatch_height if swatch_height is not None else row_height
        center_y = (top_y + bottom_y) / 2.0
        swatch = create_swatch_region(
            doc, view, 0.0, center_y - swatch_h / 2.0, swatch_col_width, swatch_h
        )
        row_height = max(row_height, swatch_h)

    return notes, swatch, row_height


def unique_view_name(doc, base_name, existing_names=None):
    """Return a view name that does not collide with any existing view.

    Appends " (2)", " (3)", ... until unique, instead of EF-Tools' habit
    of stacking "*" characters onto the name.

    Args:
        doc: Document
        base_name: preferred name
        existing_names: optional pre-fetched set of existing view names
            (pass this in when calling in a loop to avoid re-querying
            the document every time)

    Returns:
        str: a unique view name
    """
    if existing_names is None:
        existing_names = set(
            v.Name
            for v in DB.FilteredElementCollector(doc)
            .OfCategory(DB.BuiltInCategory.OST_Views)
            .WhereElementIsNotElementType()
            .ToElements()
        )

    name = base_name
    counter = 2
    while name in existing_names:
        name = "{0} ({1})".format(base_name, counter)
        counter += 1
    return name
