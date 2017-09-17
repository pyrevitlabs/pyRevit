"""Searches the script folders and create buttons
for the new script or newly installed extensions."""


__cleanengine__ = True
__context__ = 'zerodoc'


import scriptutils
from pyrevit.loader.sessionmgr import load_session
from pyrevit.loader.sessioninfo import get_session_uuid

this_script = scriptutils.get_script()
logger = scriptutils.get_logger()

# re-load pyrevit session.
logger.info('Reloading....')
load_session()

this_script.results.newsession = get_session_uuid()
