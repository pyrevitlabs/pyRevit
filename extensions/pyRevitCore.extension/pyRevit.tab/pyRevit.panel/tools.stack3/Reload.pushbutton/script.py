"""Reload pyRevit into new session."""

from pyrevit import script
from pyrevit.loader import sessionmgr
from pyrevit.loader import sessioninfo


__cleanengine__ = True
__context__ = 'zerodoc'
__doc__ = 'Searches the script folders and create buttons ' \
          'for the new script or newly installed extensions.'


logger = script.get_logger()
results = script.get_results()


# re-load pyrevit session.
logger.info('Reloading....')
sessionmgr.load_session()

results.newsession = sessioninfo.get_session_uuid()
