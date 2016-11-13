from pyrevit.logger import logger
import pyrevit.config as cfg
import sys

print cfg.LOADER_ASM_DIR

print '\nPATHS:'
for path in sys.path:
    print path

print '\n\n'

__cmdoptions__ = ['op1', 'op2', 'op3']

__min_req_revit_ver__ = '2015'
__min_req_pyrevit_ver__ = (3, 0, 0)

print(__name__)

print('main script')
logger.debug('Forced debug mode is active')

#--------------------