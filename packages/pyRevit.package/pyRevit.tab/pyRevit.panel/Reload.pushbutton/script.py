from pyrevit.logger import get_logger                   # import logger to log messages to pyrevit log.
logger = get_logger(__commandname__)

import pyrevit.session as session              # import session to start loading pyRvit.


__doc__ = 'Searches the script folders and create buttons for the new script or newly installed extensions.'

# re-load pyrevit session.
logger.info('Reloading....')
session.load()
