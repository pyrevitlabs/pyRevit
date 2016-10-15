import sys
import os.path as op

import pyRevit.config as cfg
import pyRevit.output as output_window
import pyRevit.session as this_session
from pyRevit.logger import logger
from pyRevit.utils import Timer

# todo: move to RPL
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

t = Timer()

output_window.set_width(1100)
logger.debug('Running on: {0}'.format(sys.version))
logger.debug('Home Directory is: {0}'.format(cfg.HOME_DIR))

this_session.load()

logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
