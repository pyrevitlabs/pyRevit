"""Unit conversion utilities for Revit."""

from pyrevit import DOCS, HOST_APP
from pyrevit import DB
from pyrevit import PyRevitException


def get_unit_info(spec_type_id, doc=None):
    """Return unit information for a spec in document units.

    Args:
        spec_type_id (DB.SpecTypeId): spec type identifier
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        (tuple): unit, unit label, symbol, symbol label
    """
    if HOST_APP.is_older_than(2022):
        raise PyRevitException(
            "get_unit_info() requires Revit 2022 or newer."
        )

    doc = doc or DOCS.doc

    format_options = doc.GetUnits().GetFormatOptions(spec_type_id)

    unit = format_options.GetUnitTypeId()
    unit_label = DB.LabelUtils.GetLabelForUnit(unit)

    symbol = format_options.GetSymbolTypeId()
    symbol_label = None
    if not symbol.Empty():
        symbol_label = DB.LabelUtils.GetLabelForSymbol(symbol)

    return unit, unit_label, symbol, symbol_label


def format_area(area_value, doc=None):
    """Return formatted area value in document units.

    Args:
        area_value (float): area value
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        (str): formatted value
    """
    doc = doc or DOCS.doc
    if HOST_APP.is_newer_than(2021):
        return DB.UnitFormatUtils.Format(
            units=doc.GetUnits(),
            specTypeId=DB.SpecTypeId.Area,
            value=area_value,
            forEditing=False,
        )
    else:
        return DB.UnitFormatUtils.Format(
            units=doc.GetUnits(),
            unitType=DB.UnitType.UT_Area,
            value=area_value,
            maxAccuracy=False,
            forEditing=False,
        )


def format_length(length_value, doc=None):
    """Return formatted length value in document units.

    Args:
        length_value (float): length value
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        (str): formatted value
    """
    doc = doc or DOCS.doc
    if HOST_APP.is_newer_than(2021):
        return DB.UnitFormatUtils.Format(
            units=doc.GetUnits(),
            specTypeId=DB.SpecTypeId.Length,
            value=length_value,
            forEditing=False,
        )
    else:
        return DB.UnitFormatUtils.Format(
            units=doc.GetUnits(),
            unitType=DB.UnitType.UT_Length,
            value=length_value,
            maxAccuracy=False,
            forEditing=False,
        )


def format_slope(slope_value, doc=None):
    """Return formatted slope value in document units.

    Args:
        slope_value (float): slope value
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        (str): formatted value
    """
    doc = doc or DOCS.doc
    if HOST_APP.is_newer_than(2021):
        return DB.UnitFormatUtils.Format(
            units=doc.GetUnits(),
            specTypeId=DB.SpecTypeId.Slope,
            value=slope_value,
            forEditing=False,
        )
    else:
        return DB.UnitFormatUtils.Format(
            units=doc.GetUnits(),
            unitType=DB.UnitType.UT_Slope,
            value=slope_value,
            maxAccuracy=False,
            forEditing=False,
        )


def _create_view_plane(view):
    """Get a plane parallel to a view.

    Args:
        view (DB.View): view to align plane

    Returns:
        DB.Plane: result plane
    """
    return DB.Plane.CreateByOriginAndBasis(
        view.Origin, view.RightDirection, view.UpDirection
    )


def project_to_viewport(xyz, view):
    """Project a point to viewport coordinates.

    Args:
        xyz (DB.XYZ): point to project
        view (DB.View): target view

    Returns:
        (DB.UV): [description]
    """
    plane = _create_view_plane(view)
    uv, _ = plane.Project(xyz)
    return uv


def project_to_world(uv, view):
    """Get view-based point (UV) back to model coordinates.

    Args:
        uv (DB.UV): point on a view
        view (DB.View): view to get coordinates from

    Returns:
        (DB.XYZ): point in world coordinates
    """
    plane = _create_view_plane(view)
    trf = DB.Transform.Identity
    trf.BasisX = plane.XVec
    trf.BasisY = plane.YVec
    trf.BasisZ = plane.Normal
    trf.Origin = plane.Origin
    return trf.OfPoint(DB.XYZ(uv.U, uv.V, 0))


def get_spec_name(forge_id):
    """Returns the measurable spec name for the given unit id.

    Args:
        forge_id (DB.ForgeTypeId): Unit id

    Returns:
        (str): Spec name
    """
    if HOST_APP.is_newer_than(2021) and DB.UnitUtils.IsMeasurableSpec(forge_id):
        return DB.UnitUtils.GetTypeCatalogStringForSpec(forge_id)
    return ""


def get_unit_name(forge_id):
    """Returns the unit name for the given unit id.

    Args:
        forge_id (DB.ForgeTypeId): Unit id

    Returns:
        (str): Unit name
    """
    if HOST_APP.is_newer_than(2021) and DB.UnitUtils.IsUnit(forge_id):
        return DB.UnitUtils.GetTypeCatalogStringForUnit(forge_id)
    return ""
