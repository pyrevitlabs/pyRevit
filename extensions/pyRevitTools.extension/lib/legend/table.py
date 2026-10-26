# -*- coding: utf-8 -*-
"""Legend tables: a header row plus one color swatch and text row per entry.

    [swatch] [column 1] [column 2] ...

Callers only decide the texts and the swatch overrides; row heights are
measured from the rendered text and columns widen to fit their content.
"""

from pyrevit import DB
from pyrevit.coreutils import unique_name

from legend.drawing import autofit_column_widths, create_legend_row

DEFAULT_LAYOUT_MM = {
    "row_height": 5.0,
    "row_spacing": 2.0,
    "swatch_width": 8.0,
    "text_column_width": 60.0,
}

COLUMN_INSET_RATIO = 0.05


def _mm_to_feet(value):
    return DB.UnitUtils.ConvertToInternalUnits(value, DB.UnitTypeId.Millimeters)


class LegendLayout(object):
    """Text type and sizes of a legend table, lengths in feet.

    Note:
        Lengths are paper sizes; they only print at that size in a legend
        at scale 1, which ``create_legend_view`` sets.
    """

    def __init__(
        self, text_type_id, row_height, row_spacing, swatch_width, text_column_width
    ):
        self.text_type_id = text_type_id
        self.row_height = row_height
        self.row_spacing = row_spacing
        self.swatch_width = swatch_width
        self.text_column_width = text_column_width

    @classmethod
    def from_mm(cls, text_type_id, **lengths_mm):
        """Build a layout from millimeter lengths; missing ones use DEFAULT_LAYOUT_MM."""
        merged = dict(DEFAULT_LAYOUT_MM, **lengths_mm)
        lengths = {name: _mm_to_feet(value) for name, value in merged.items()}
        return cls(text_type_id, **lengths)

    def column_offsets(self, column_count):
        """X offsets of the text columns, right of the swatch column."""
        return [
            self.swatch_width + self.text_column_width * (index + COLUMN_INSET_RATIO)
            for index in range(column_count)
        ]


class LegendRow(object):
    """One data row: a text per column and the overrides painting its swatch.

    With ``overrides`` of None the swatch keeps its FilledRegionType's look.
    """

    def __init__(self, texts, overrides=None):
        self.texts = texts
        self.overrides = overrides


def create_legend_view(doc, template_legend, name, taken_names):
    """Duplicate ``template_legend`` as an empty, scale-1 legend.

    ``name`` is made unique against ``taken_names``, which is updated so
    several legends can be created in one run.

    Note:
        Must be called inside an open transaction.
    """
    legend = doc.GetElement(template_legend.Duplicate(DB.ViewDuplicateOption.Duplicate))
    legend.Scale = 1
    legend.Name = unique_name(name, taken_names)
    taken_names.add(legend.Name)
    return legend


def draw_legend_table(doc, view, layout, header, rows, region_type_id=None):
    """Draw a header row and one swatch row per entry, starting at the origin.

    Args:
        doc: Document
        view: Legend view to draw into
        layout: LegendLayout
        header: column titles, left to right; sets the column count
        rows: LegendRow per entry, each with one text per header column
        region_type_id: FilledRegionType for the swatches, see
            legend.drawing.create_swatch_region

    Returns:
        list[DB.ElementId]: every element drawn -- text notes column by
            column, then swatches -- for managed-element tracking.

    Note:
        Must be called inside an open transaction. On an exception the
        partially drawn elements are left for that transaction to roll back.
    """
    offsets = layout.column_offsets(len(header))
    notes_by_column = [[] for _ in offsets]
    swatches = []

    header_notes, _, header_height = create_legend_row(
        doc,
        view,
        0.0,
        layout.text_type_id,
        columns=list(zip(offsets, header)),
        min_row_height=layout.row_height,
    )
    _append_by_column(notes_by_column, header_notes)
    y_top = -(header_height + layout.row_spacing)

    for row in rows:
        notes, swatch, row_height = create_legend_row(
            doc,
            view,
            y_top,
            layout.text_type_id,
            columns=list(zip(offsets, row.texts)),
            swatch_col_width=layout.swatch_width,
            swatch_height=layout.row_height,
            min_row_height=layout.row_height,
            region_type_id=region_type_id,
        )
        _append_by_column(notes_by_column, notes)
        swatches.append(swatch)
        if row.overrides is not None:
            view.SetElementOverrides(swatch.Id, row.overrides)
        y_top -= row_height + layout.row_spacing

    autofit_column_widths(
        doc,
        view,
        notes_by_column=notes_by_column,
        base_offsets=offsets,
        min_gap=layout.text_column_width * COLUMN_INSET_RATIO,
    )
    note_ids = [note.Id for column in notes_by_column for note in column]
    return note_ids + [swatch.Id for swatch in swatches]


def _append_by_column(notes_by_column, row_notes):
    for column, note in zip(notes_by_column, row_notes):
        column.append(note)
