"""Unit conversion utilities for Revit."""

import math
import re

from pyrevit import DOCS, HOST_APP
from pyrevit import DB
from pyrevit import PyRevitException

_FEET_INCHES = re.compile(
    r"^\s*(?:(?P<feet>-?\d+(?:\.\d+)?)\s*')?\s*-?\s*"
    r"(?:(?P<inches>\d+(?:\.\d+)?)?\s*(?:(?P<num>\d+)\s*/\s*(?P<den>\d+))?\s*\")?\s*$"
)
_METRIC = re.compile(r"^\s*(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m)\s*$")
_METRIC_TO_FEET = {"mm": 304.8, "cm": 30.48, "m": 0.3048}
_SLOPE_RATIO = re.compile(
    r"^\s*(?P<rise>\d+(?:\.\d+)?)\s*(?::|/|\s+in\s+)\s*(?P<run>\d+(?:\.\d+)?)\s*$"
)
_SLOPE_DEGREES = re.compile(r"^\s*(?P<deg>\d+(?:\.\d+)?)\s*deg(?:rees)?\s*$")


def get_unit_info(spec_type_id, doc=None):
    """Return unit information for a spec in document units.

    Args:
        spec_type_id (DB.SpecTypeId): spec type identifier
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        (tuple): unit, unit label, symbol, symbol label
    """
    if HOST_APP.is_older_than(2022):
        raise PyRevitException("get_unit_info() requires Revit 2022 or newer.")

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


def parse_length(value):
    """Convert a length written the way drawings write it to feet.

    Args:
        value (float | int | str): feet as a number, or a string such as
            ``32'-6"``, ``32' 6 1/2"``, ``6"``, ``12'``, ``900mm``, ``90cm``
            or ``2.5m``.

    Returns:
        (float): length in feet, Revit's internal length unit.

    Raises:
        PyRevitException: when the string is not a length in a known format.

    Note:
        Independent of the document's units, so it gives the same answer
        in any project and needs no open document.
    """
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    metric = _METRIC.match(text)
    if metric:
        return float(metric.group("value")) / _METRIC_TO_FEET[metric.group("unit")]
    imperial = _FEET_INCHES.match(text)
    if imperial and ("'" in text or '"' in text):
        feet = float(imperial.group("feet") or 0.0)
        inches = float(imperial.group("inches") or 0.0)
        if imperial.group("num"):
            inches += float(imperial.group("num")) / float(imperial.group("den"))
        sign = -1.0 if text.startswith("-") else 1.0
        return sign * (abs(feet) + inches / 12.0)
    try:
        return float(text)
    except ValueError:
        raise PyRevitException(
            "Can't read length {!r}. Use feet as a number, 32'-6\", 6\", "
            "900mm or 2.5m.".format(value)
        )


def parse_slope(value):
    """Convert a roof pitch to rise over run, the value Revit's slope APIs take.

    Args:
        value (float | int | str): ``"8:12"``, ``"8/12"`` or ``"8 in 12"``
            (0.667), ``"30deg"`` (tan of 30 degrees), or a rise/run number.

    Returns:
        (float): rise over run.

    Raises:
        PyRevitException: when the string is not a pitch in a known format.

    Important:
        ``FootPrintRoof.set_SlopeAngle`` and the ``ROOF_SLOPE`` parameter
        take rise over run, not degrees or radians. Passing 33.69 for an
        8:12 roof builds a roof hundreds of feet tall.
    """
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    ratio = _SLOPE_RATIO.match(text)
    if ratio:
        return float(ratio.group("rise")) / float(ratio.group("run"))
    degrees = _SLOPE_DEGREES.match(text)
    if degrees:
        return math.tan(math.radians(float(degrees.group("deg"))))
    raise PyRevitException(
        "Can't read pitch {!r}. Use '8:12', '30deg' or a rise/run number.".format(value)
    )
