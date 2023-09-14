"""Selection utilities."""
from pyrevit.revit.db import query


def select_mirrored(elements):
    """Select only mirrored elements from the given elements."""
    return [x for x in elements
            if hasattr(x, "Mirrored") and x.Mirrored]
