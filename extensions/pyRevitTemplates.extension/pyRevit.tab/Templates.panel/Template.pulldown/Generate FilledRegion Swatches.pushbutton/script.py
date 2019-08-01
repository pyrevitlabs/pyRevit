"""Generate filledregion swatches in active view."""
#pylint: disable=E0401,C0103
from pyrevit.framework import List
from pyrevit import revit, DB


MAX_WIDTH = 16
DIRECTION = 1       # OR -1


def make_title(base_point, fr_type):
    tnote_typeid = \
        revit.doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
    DB.TextNote.Create(revit.doc,
                       revit.active_view.Id,
                       DB.XYZ(base_point.X, base_point.Y + 1, base_point.Z),
                       1/12.0,
                       revit.query.get_name(fr_type),
                       tnote_typeid
                      )


def make_filledregion_element(base_point, fr_type):
    cloop = DB.CurveLoop()
    cloop.Append(
        DB.Line.CreateBound(
            DB.XYZ(base_point.X, base_point.Y, base_point.Z),
            DB.XYZ(base_point.X + 1, base_point.Y, base_point.Z)
            )
    )
    cloop.Append(
        DB.Line.CreateBound(
            DB.XYZ(base_point.X + 1, base_point.Y, base_point.Z),
            DB.XYZ(base_point.X + 1, base_point.Y + DIRECTION, base_point.Z)
            )
    )
    cloop.Append(
        DB.Line.CreateBound(
            DB.XYZ(base_point.X + 1, base_point.Y + DIRECTION, base_point.Z),
            DB.XYZ(base_point.X, base_point.Y + DIRECTION, base_point.Z)
            )
    )
    cloop.Append(
        DB.Line.CreateBound(
            DB.XYZ(base_point.X, base_point.Y + DIRECTION, base_point.Z),
            DB.XYZ(base_point.X, base_point.Y, base_point.Z)
            )
    )

    DB.FilledRegion.Create(revit.doc,
                           fr_type.Id,
                           revit.active_view.Id,
                           List[DB.CurveLoop]([cloop]))


def make_swatch(index, fr_type):
    row = 0 + (index / MAX_WIDTH)
    col = index - (MAX_WIDTH * row)
    base_point = DB.XYZ(col, row * DIRECTION, 0)
    make_title(base_point, fr_type)
    make_filledregion_element(base_point, fr_type)


filledregion_types = revit.query.get_types_by_class(DB.FilledRegionType)
with revit.Transaction('Generate FilledRegion Swatched'):
    for idx, filledregion_type in enumerate(
            sorted(filledregion_types,
                   key=lambda x: revit.query.get_name(x))):
        make_swatch(idx, filledregion_type)
