__window__.Width = 1100
# __window__.Close()

#temp: will take care of this part in RPL
import sys
import os.path as op
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

import logging

from pyRevit.timer import Timer
from pyRevit.loader import PyRevitUISession

from pyRevit.logger import logger
logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)

__doc__ = 'Searches the script folders and create buttons for the new script or newly installed extensions.'

t = Timer()

session = PyRevitUISession()
logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
