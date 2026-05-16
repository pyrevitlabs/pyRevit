"""Reload pyRevit into new session."""
# -*- coding=utf-8 -*-
#pylint: disable=import-error,invalid-name,broad-except

from pyrevit import script
from pyrevit.loader import sessionmgr
from pyrevit.loader import sessioninfo


logger = script.get_logger()
results = script.get_results()

# Re-load pyrevit session.
logger.info('Reloading....')
sessionmgr.reload_pyrevit()

results.newsession = sessioninfo.get_session_uuid()
