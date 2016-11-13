from pyrevit.logger import get_logger
logger = get_logger(__commandname__)

import pyrevit.config as cfg
import sys

print __builtins__['__name__']
print globals()['__name__']
print locals()['__name__']


print cfg.LOADER_ASM_DIR

print '\nPATHS:'
for path in sys.path:
    print path

print '\n\n'

__cmdoptions__ = ['op1', 'op2', 'op3']

__min_req_revit_ver__ = '2015'
__min_req_pyrevit_ver__ = (3, 0, 0)

print 'Name: {}'.format(__name__)

print 'Host: {}'.format(__revit__)
print 'Command Data: {}'.format(__commandData__)
try:
    print 'UI App: {}'.format(__uiControlledApplication__)
except:
    logger.error('UI App is Null.')

print 'Selection: {}'.format(__elements__)

print 'Window hndlr: {}'.format(__window__)
print 'File: {}'.format(__file__)
print 'Lib path: {}'.format(__libpath__)
print 'Forced Debug: {}'.format(__forceddebugmode__)

print 'Message: {}'.format(__message__)
print 'Result: {}'.format(__result__)

__doc__ = "test tootip"
__author__ = "test author"
__cmdoptions__ = ['Op1', 'Op2']


print('main script')
logger.debug('Forced debug mode is active')
raise Exception()


def selfInit(__rvt__, scriptaddress, commandbutton):
    pass
