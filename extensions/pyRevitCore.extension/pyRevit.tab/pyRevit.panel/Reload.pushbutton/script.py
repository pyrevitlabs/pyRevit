"""Searches the script folders and create buttons for the new script or newly installed extensions."""

from scriptutils import logger
from pyrevit.loader.sessionmgr import load_session
from pyrevit.loader.sessioninfo import get_session_uuid

from scriptutils import this_script

# re-load pyrevit session.
logger.info('Reloading....')
load_session()

this_script.results.newsession = get_session_uuid()
