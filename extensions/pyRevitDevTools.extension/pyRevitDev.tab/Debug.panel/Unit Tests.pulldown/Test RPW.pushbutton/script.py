# import sys
# from pyrevit.coreutils.logger import get_logger
# logger = get_logger(__commandname__)

from pyrevit.coreutils import Timer

timer = Timer()

# import rpw
from rpw import db, DB, extras

endtime = timer.get_time()
print('rpw load time: {} seconds'.format(endtime))
