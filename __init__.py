import sys
import os.path as op

# todo: move to RPL
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

# now pyrevit module imports
import pyRevit.config as cfg
from pyRevit.logger import logger
import pyRevit.output as output
from pyRevit.utils import Timer
from pyRevit.usersettings import user_settings
# from pyRevit.ui import current_session

t = Timer()

output.set_width(1100)
logger.debug('Running on: {0}'.format(sys.version))
logger.debug('Home Directory is: {0}'.format(cfg.HOME_DIR))

# current_session.load()

logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
