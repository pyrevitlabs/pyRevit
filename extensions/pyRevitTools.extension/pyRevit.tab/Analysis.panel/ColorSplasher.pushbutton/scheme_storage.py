# -*- coding: utf-8 -*-
"""Color Splasher's color scheme stored on the view it colors.

Thin, tool-specific wrapper around the generic
pyrevit.coreutils.extensible_storage helper (see that module for the
underlying Extensible Storage mechanics). It is the in-model
counterpart of a .cschn scheme file: the same ordered value -> color
entries, so a scheme loads by value or by position either way.

A view holds a single scheme; saving replaces it. Only this file needs
to change if the stored scheme ever needs more data (e.g. the category
and parameter it was made for): add a field to the schema class and
pass it through save_view_scheme.
"""

from System import Int32

from pyrevit.coreutils import extensible_storage


class _ColorSplasherSchemeSchema(extensible_storage.BaseSchema):
    guid = "adb65cfb-92cc-4610-b356-8511afdc2599"
    schema_name = "pyRevitColorSplasherScheme"
    vendor_id = "clsp"
    array_fields = {"ValueNames": str, "Colors": Int32}


_storage = extensible_storage.ElementDataStorage(_ColorSplasherSchemeSchema)


def _pack_rgb(color):
    red, green, blue = color
    return (red << 16) | (green << 8) | blue


def _unpack_rgb(packed):
    return (packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF


def save_view_scheme(view, entries):
    """Store ``entries`` as the color scheme of ``view``, replacing any earlier one.

    Args:
        view: DB.View the scheme belongs to
        entries: iterable of (value_name, (red, green, blue)), in window order

    Must be called inside an open transaction.
    """
    entries = list(entries)
    _storage.set_data(
        view,
        ValueNames=[name for name, _ in entries],
        Colors=[_pack_rgb(color) for _, color in entries],
    )


def get_view_scheme(view):
    """Return the color scheme stored on ``view``.

    Returns:
        list of (value_name, (red, green, blue)) in saved order, or None
            if the view has no scheme -- including when the schema has
            never been used in this document.
    """
    data = _storage.get_data(view)
    if data is None:
        return None
    colors = [_unpack_rgb(packed) for packed in data["Colors"]]
    return list(zip(data["ValueNames"], colors))


def has_view_scheme(view):
    """bool: whether ``view`` has a stored color scheme."""
    return _storage.has_data(view)
