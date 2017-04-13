"""Opens keynote source file used in this model."""

__author__ = 'Dan Mapes'
__contact__ = 'https://github.com/DMapes'

import os

from scriptutils import logger
from revitutils import doc

from Autodesk.Revit.DB import KeynoteTable, ModelPathUtils


kt = KeynoteTable.GetKeynoteTable(doc)
kt_ref = kt.GetExternalFileReference()
path = ModelPathUtils.ConvertModelPathToUserVisiblePath(kt_ref.GetAbsolutePath())
if not path:
    logger.error('No keynote file is assigned...File address is empty.')
else:
    os.system('start notepad "{0}"'.format(path))
