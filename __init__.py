import sys
import os.path as op

import pyRevit.config as cfg                        # import basic configurations.
import pyRevit.output as output_window              # handles output termina window
from pyRevit.logger import logger                   # import logger to log messages to pyRevit log.
from pyRevit.utils import Timer                     # import Timer from standard utils to log the load  time.

# now import session to start loading pyRvit.
import pyRevit.session as this_session

# todo: move to RPL
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

# initialize timer
t = Timer()

# set output window size.
output_window.set_width(1100)

# log python version and home directory info.
logger.debug('Running on: {0}'.format(sys.version))
logger.debug('Home Directory is: {0}'.format(cfg.HOME_DIR))

# load pyRevit session.
this_session.load()

# log load time
logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
