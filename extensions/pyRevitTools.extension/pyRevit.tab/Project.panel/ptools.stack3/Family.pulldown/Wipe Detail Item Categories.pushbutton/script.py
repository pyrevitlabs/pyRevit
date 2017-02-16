"""Tries to remove all sub-categories in current Detail Item family"""

from scriptutils import logger
from revitutils import doc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, BuiltInCategory, GraphicsStyleType
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


if doc.IsFamilyDocument:
    det_item_cat = doc.OwnerFamily.FamilyCategory

    if 'Detail Item' in det_item_cat.Name:
        with Transaction(doc, 'Wipe Detail Item Categories') as t:
            t.Start()

            for sub_cat in det_item_cat.SubCategories:
                logger.debug('Removing sub category: {}'.format(sub_cat.Name))
                try:
                    doc.Delete(sub_cat.Id)
                    pass
                except:
                    logger.warning('Can not delete sub category: {}'.format(sub_cat.Name))
                    continue

            t.Commit()
    else:
        TaskDialog.Show('pyRevit','Family must be of type Detail Item.')
else:
    TaskDialog.Show('pyRevit','This script works only on an active family editor.')
