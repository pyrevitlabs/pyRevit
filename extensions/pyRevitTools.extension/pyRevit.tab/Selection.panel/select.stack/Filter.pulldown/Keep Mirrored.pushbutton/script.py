# -*- coding: utf-8 -*-
"""Keep only mirrored elements, or with Shift-click only non-mirrored ones."""

from pyrevit import script
from pyrevit import EXEC_PARAMS

import selectionpick

logger = script.get_logger()


def has_mirrored_state(element, mirrored):
    try:
        return element.Mirrored == mirrored
    except Exception as err:
        logger.debug("{} | {}".format(element.Id, err))
        return False


if __name__ == "__main__":
    keep_mirrored = not EXEC_PARAMS.config_mode
    selectionpick.keep_matching(
        lambda element: has_mirrored_state(element, keep_mirrored)
    )
