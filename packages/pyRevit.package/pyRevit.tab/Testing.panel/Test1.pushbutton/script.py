import sys

from pyrevit.logger import get_logger
logger = get_logger(__commandname__)


# html test ------------------------------------------------------------------------------------------------------------
logger.info(':beer_mug: Everything went well!')
logger.info("Python is :thumbs_up: :banana:")
print "\n<a href='http://www.google.com'>Clickable link Google</a>"

from html import HTML
h = HTML()

t = h.table(border='1', newlines=False)
for i in range(2):
    r = t.tr
    r.td('column 1')
    r.td('column 2')

print t

# testing output window ------------------------------------------------------------------------------------------------
from pyrevit.output import output_window as ow

print '\n\n' + '-'*100 + '\nTESTING OUTPUT WINDOW\n' + '-'*100
ow.set_height(600)
print ow.get_title()
ow.set_title('Beautiful title')

# ow.set_font('Verdana', 8)
# ow.set_word_wrap(False)
# ow.show_both_scrollbars()

# testing scriptutils --------------------------------------------------------------------------------------------------
from pyrevit.loader.components import GenericCommand
import pyrevit.scriptutils as su
this_script = su.get_script_info(__file__)  # type: GenericCommand

print '\n\n' + '-'*100 + '\nTESTING SCRIPT UTILS\n' + '-'*100
print this_script.name
print this_script.author
print this_script.cmd_options
print this_script.config_script_file
print this_script.directory
print this_script.doc_string
print this_script.icon_file
print this_script.library_path
print this_script.ui_title

# testing params -------------------------------------------------------------------------------------------------------
import pyrevit.config as cfg

print '\n\n' + '-'*100 + '\nTESTING PARAMS\n' + '-'*100

print __builtins__['__name__']
print globals()['__name__']
print locals()['__name__']

print cfg.LOADER_ASM_DIR

print '\nPATHS:'
for path in sys.path:
    print path

__title__ = 'Test\nScript'
__doc__ = "test tootip"
__author__ = "test author"
__cmdoptions__ = ['op1', 'op2', 'op3']
__min_req_revit_ver__ = '2015'
__min_req_pyrevit_ver__ = (3, 0, 0)

# __assembly__ = ''
# __commandclass = ''

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


# exception output -----------------------------------------------------------------------------------------------------
raise Exception('Testing exception output report')


# smart button template ------------------------------------------------------------------------------------------------
def __selfinit__(script_cmp, commandbutton, user_settings, __rvt__):
    pass
