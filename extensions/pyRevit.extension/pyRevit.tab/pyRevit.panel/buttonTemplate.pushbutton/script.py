import scriptutils as su

__doc__ = 'Shows the preferences window for pyrevit. You can customize how pyrevit loads and set some basic ' \
          'parameters here.'

__title__ = 'Sample\nCommand'


su.logger.critical('Test Log Level')
su.logger.warning('Test Log Level')
su.logger.info('Test Log Level :ok_hand_sign:')
su.logger.debug('Test Log Level')

print type(su.my_info)
print su.my_info
print su.my_info.name
print su.my_info.ui_title
print su.my_info.unique_name
print su.my_info.unique_avail_name
print su.my_info.doc_string
print su.my_info.author
print su.my_info.cmd_options
print su.my_info.cmd_context
print su.my_info.min_pyrevit_ver
print su.my_info.min_revit_ver
print su.my_info.cmd_options
print su.my_info.script_file
print su.my_info.config_script_file
print su.my_info.icon_file
print su.my_info.library_path
print su.my_info.syspath_search_paths


print type(su.my_config)
print su.my_config


print su.my_temp_file
print su.my_data_file


su.my_output.set_height(600)
print su.my_output.get_title()
su.my_output.set_title('Beautiful title')


su.PYREVIT_VERSION
su.PyRevitException


__commandname__
__commandpath__
__shiftclick__
__assmcustomattrs__
__window__
__file__


try:
    print('__execversion__ is {}'.format(__execversion__))
except:
    print('__execversion__ is not available')


print __builtins__['__name__']
print globals()['__name__']
print locals()['__name__']

print '\nPATHS:'
for path in sys.path:
    print path

__title__ = 'Master\nTests'
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
print 'Forced Debug: {}'.format(__forceddebugmode__)
print 'Message: {}'.format(__message__)
print 'Result: {}'.format(__result__)


# smart button template ------------------------------------------------------------------------------------------------
def __selfinit__(script_cmp, commandbutton, __rvt__):
    pass
