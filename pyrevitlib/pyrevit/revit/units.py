"""Unit conversion utilities for Revit."""

from pyrevit import HOST_APP
from pyrevit import DB


def format_area(area_value, doc=None):
    """Return formatted area value in document units.

    Args:
        area_value (float): area value
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        str: formatted value
    """
    doc = doc or HOST_APP.doc
    return DB.UnitFormatUtils.Format(units=doc.GetUnits(),
                                     unitType=DB.UnitType.UT_Area,
                                     value=area_value,
                                     maxAccuracy=False,
                                     forEditing=False)
