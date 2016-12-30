import scriptutils
from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app.run()

# import sys
# import scriptutils as su
#
# # __title__ = ''
#
# su.logger.critical('Test Log Level')
# su.logger.warning('Test Log Level')
# su.logger.info('Test Log Level :ok_hand_sign:')
# su.logger.debug('Test Log Level')
#
# print type(su.this_script.info)
# print su.this_script.info
# print su.this_script.info.name
# print su.this_script.info.ui_title
# print su.this_script.info.unique_name
# print su.this_script.info.unique_avail_name
# print su.this_script.info.doc_string
# print su.this_script.info.author
# print su.this_script.info.cmd_options
# print su.this_script.info.cmd_context
# print su.this_script.info.min_pyrevit_ver
# print su.this_script.info.min_revit_ver
# print su.this_script.info.cmd_options
# print su.this_script.info.script_file
# print su.this_script.info.config_script_file
# print su.this_script.info.icon_file
# print su.this_script.info.library_path
# print su.this_script.info.syspath_search_paths
#
#
# print type(su.this_script.config)
# print su.this_script.config
#
#
# print su.this_script.instance_data_file
#
#
# su.this_script.output.set_height(600)
# print su.this_script.output.get_title()
# su.this_script.output.set_title('Beautiful title')
#
#
# su.this_script.pyrevit_version
#
#
# __commandname__
# __commandpath__
# __shiftclick__
# __assmcustomattrs__
# __window__
# __file__
#
#
# try:
#     print('__execversion__ is {}'.format(__execversion__))
# except:
#     print('__execversion__ is not available')
#
#
# print __builtins__['__name__']
# print globals()['__name__']
# print locals()['__name__']
#
# print '\nPATHS:'
# for path in sys.path:
#     print path
#
# __title__ = 'Master\nTests'
# __doc__ = "test tootip"
# __author__ = "test author"
# __cmdoptions__ = ['op1', 'op2', 'op3']
# __min_req_revit_ver__ = '2015'
# __min_req_pyrevit_ver__ = (3, 0, 0)
#
# # __assembly__ = ''
# # __commandclass = ''
#
# print 'Name: {}'.format(__name__)
# print 'Host: {}'.format(__revit__)
# print 'Command Data: {}'.format(__commandData__)
# try:
#     print 'UI App: {}'.format(__uiControlledApplication__)
# except:
#     su.logger.error('UI App is Null.')
# print 'Selection: {}'.format(__elements__)
# print 'Window hndlr: {}'.format(__window__)
# print 'File: {}'.format(__file__)
# print 'Forced Debug: {}'.format(__forceddebugmode__)
# print 'Message: {}'.format(__message__)
# print 'Result: {}'.format(__result__)
#
#
# # smart button template ------------------------------------------------------------------------------------------------
# def __selfinit__(script_cmp, commandbutton, __rvt__):
#     pass
