"""Saves current selection memory as a Selection Filter."""
#pylint: disable=import-error,invalid-name,broad-except
import os.path as op
import pickle as pl

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import script

logger = script.get_logger()

proj_info = revit.query.get_project_info()
data_file = script.get_document_data_file("SelList", "pym")
logger.debug(data_file)

if op.exists(data_file):
    if proj_info.name:
        filter_name = \
            'SavedSelection_' + proj_info.name + '_' + coreutils.timestamp()
    else:
        filter_name = \
            'SavedSelection_' + coreutils.timestamp()

    with open(data_file, 'r') as f:
        cursel = pl.load(f)

    with revit.Transaction('pySaveSelection'):
        selection_filter = \
            DB.SelectionFilterElement.Create(
                revit.doc,
                coreutils.cleanup_filename(filter_name)
                )
        for elid in cursel:
            selection_filter.AddSingle(DB.ElementId(int(elid)))
