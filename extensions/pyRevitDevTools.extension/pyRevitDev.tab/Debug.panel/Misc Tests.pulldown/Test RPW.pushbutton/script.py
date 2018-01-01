from pyrevit.coreutils import Timer

# measure import time
timer = Timer()
import rpw
from rpw import db, DB, extras
from rpw import __version__
endtime = timer.get_time()
print('rpw load time: {} seconds'.format(endtime))
print('rpw version: {}'.format(__version__))
