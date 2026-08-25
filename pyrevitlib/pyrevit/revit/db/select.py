"""Selection utilities."""
from pyrevit.revit.db import query


def select_mirrored(elements, mirrored=True):
    """Select elements by mirrored state."""
    return [
        x for x in elements
        if hasattr(x, "Mirrored") and x.Mirrored == mirrored
    ]
