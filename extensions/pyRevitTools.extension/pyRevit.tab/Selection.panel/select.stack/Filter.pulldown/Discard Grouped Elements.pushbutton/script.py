# -*- coding: utf-8 -*-
"""Discard grouped elements from the selection, or from a picked rectangle."""

from pyrevit import DB

import selectionpick


def is_not_grouped(element):
    return element.GroupId == DB.ElementId.InvalidElementId and not isinstance(
        element, DB.Group
    )


if __name__ == "__main__":
    selectionpick.keep_matching(is_not_grouped)
