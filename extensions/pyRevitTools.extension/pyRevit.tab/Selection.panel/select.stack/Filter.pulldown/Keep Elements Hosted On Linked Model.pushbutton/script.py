# -*- coding: utf-8 -*-
"""Keep only elements hosted on a linked model, from the selection or a picked rectangle."""

from pyrevit import script
from pyrevit import DB

import selectionpick

logger = script.get_logger()


def is_hosted_on_link(element):
    try:
        return isinstance(element.Host, DB.RevitLinkInstance)
    except Exception as err:
        logger.debug("{} | {}".format(element.Id, err))
        return False


if __name__ == "__main__":
    selectionpick.keep_matching(is_hosted_on_link)
