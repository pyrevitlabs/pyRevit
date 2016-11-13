import sys

from pyrevit.logger import get_logger                   # import logger to log messages to pyrevit log.
logger = get_logger(__commandname__)

import pyrevit.config as cfg                        # import basic configurations.
from pyrevit.utils import Timer                     # import Timer from standard utils to log the load  time.

from pyrevit.userconfig import user_settings      # handles user settings

import pyrevit.session as session              # import session to start loading pyRvit.


__doc__ = 'Searches the script folders and create buttons for the new script or newly installed extensions.'


# initialize timer
t = Timer()

# log python version, home directory, config file and loader script location.
logger.info('Running on: {0}'.format(sys.version))
logger.info('Home Directory is: {0}'.format(cfg.HOME_DIR))
logger.info('Config file is: {}'.format(user_settings.config_file))

# re-load pyrevit session.
logger.info('Reloading....')
session.load()

# log load time
logger.info('Load time: {}'.format(t.get_time_hhmmss()))

