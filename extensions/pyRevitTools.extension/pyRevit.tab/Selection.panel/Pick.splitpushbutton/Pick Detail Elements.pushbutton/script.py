# -*- coding: utf-8 -*-
"""Pick only 2D detail elements by drawing a rectangle."""

from pyrevit import DB

import selectionpick


def is_ungrouped_detail_element(element):
    # only allow view-specific (detail) elements
    # that are not part of a group
    return element.ViewSpecific and element.GroupId == DB.ElementId.InvalidElementId


if __name__ == "__main__":
    selectionpick.select_picked(is_ungrouped_detail_element)
