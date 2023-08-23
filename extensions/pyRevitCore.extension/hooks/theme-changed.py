# -*- coding: utf-8 -*-

from pyrevit import script
from pyrevit.loader import sessionmgr, sessioninfo

logger = script.get_logger()
results = script.get_results()

# re-load pyrevit session.
logger.info('Reloading....')
sessionmgr.reload_pyrevit()

results.newsession = sessioninfo.get_session_uuid()
