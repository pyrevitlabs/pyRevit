# -*- coding: utf-8 -*-
"""Keep only editable elements of the selection, or of a picked rectangle."""

from pyrevit import script
from pyrevit import revit, DB

import selectionpick

logger = script.get_logger()


def is_editable(element):
    if not revit.doc.IsWorkshared:
        return True
    try:
        status = DB.WorksharingUtils.GetCheckoutStatus(revit.doc, element.Id)
    except Exception as err:
        logger.debug("{} | {}".format(element.Id, err))
        return True
    return status in (
        DB.CheckoutStatus.NotOwned,
        DB.CheckoutStatus.OwnedByCurrentUser,
    )


if __name__ == "__main__":
    selectionpick.keep_matching(is_editable)
