"""Tries to remove all sub-categories in current Detail Item family."""

from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


logger = script.get_logger()


if revit.doc.IsFamilyDocument:
    det_item_cat = revit.doc.OwnerFamily.FamilyCategory

    if 'Detail Item' in det_item_cat.Name:
        with revit.Transaction('Wipe Detail Item Categories'):
            for sub_cat in det_item_cat.SubCategories:
                logger.debug('Removing sub category: {}'.format(sub_cat.Name))
                try:
                    revit.doc.Delete(sub_cat.Id)
                    pass
                except Exception:
                        logger.warning('Can not delete sub category: {}'
                                       .format(sub_cat.Name))
                        continue
    else:
        forms.alert('Family must be of type Detail Item.')
else:
    forms.alert('This script works only on an active family editor.')
