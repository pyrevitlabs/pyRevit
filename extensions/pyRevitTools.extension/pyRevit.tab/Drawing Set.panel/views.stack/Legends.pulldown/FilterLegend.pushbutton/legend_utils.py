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
