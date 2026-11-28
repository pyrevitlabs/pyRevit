# -*- coding: utf-8 -*-
"""Keep only elements with painted faces, from the selection or a picked rectangle."""

from pyrevit import script

import selectionpick

logger = script.get_logger()


def has_painted_faces(element):
    try:
        return element.GetMaterialIds(True).Count > 0
    except Exception as err:
        logger.debug("{} | {}".format(element.Id, err))
        return False


if __name__ == "__main__":
    selectionpick.keep_matching(has_painted_faces)
