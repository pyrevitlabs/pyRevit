"""This is a quick look at a typical pyRevit script and the utilities that are available to it."""

__title__ = 'Sample\nCommand'
__author__ = 'Ehsan Iran-Nejad'


from pyrevit.coreutils import prepare_html_str
import scriptutils as su
import markdown

def print_code(code_str):
    nbsp = '&nbsp;'
    code_div = """<div style="font-family:courier new;border-style: solid;border-width:0 0 0 5;border-color:#87b012;background:#ececec;color:#3e3d3d;line-height: 150%;padding:10;margin:10 0 10 0">{}</div>"""
    print(prepare_html_str(code_div.format(code_str.replace('    ', nbsp*4))))


def print_md(md_str):
    print(prepare_html_str(markdown.markdown(md_str)))


# ----------------------------------------------------------------------------------------------------------------------
print_md("""### Basics:
This is a quick look at a typical pyRevit script and the utilities that are available to it.""")

print_md("#### Basic script parameters:")
print_code("""\"\"\"You can place the docstring (tooltip) at the top of the script file. This serves both as python docstring
and also button tooltip in pyRevit. You should use triple quotes for standard python docstrings.\"\"\"""")


print("You can also explicitly define the tooltip for this script file, independent of the docstring defined at the top.")

print_code("__doc__ = 'This is the text for the button tooltip associated with this script.'")


print("""If you'd like the UI button to have a custom name different from the script name, you can define this variable.
For example, the __title__ parameter is defined as shown below for this script.
""")

print_code("__title__ = 'Sample\\nCommand'")


print("You can define the script author as shown below. This will show up on the button tooltip.")
print_code("__author__ = 'Ehsan Iran-Nejad'")

# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("#### Logging:")
print("""
For all logging, the 'scriptutils' module defines the default logger for each script. Here is how to use it:
""")

print_code("""from scriptutils import logger
logger.info('Test Log Level :ok_hand_sign:')""")
print 'This is how it looks like when printed in the output window:'
su.logger.info('Test Log Level :ok_hand_sign:')
print '\n\n'

print_code("""logger.warning('Test Log Level')""")
print 'This is how it looks like when printed in the output window:'
su.logger.warning('Test Log Level')
print '\n\n'

print_code("""logger.critical('Test Log Level')""")
print 'This is how it looks like when printed in the output window:'
su.logger.critical('Test Log Level')
print '\n\n'


print("""
As you see, critical and warning messages are printed in colour for clarity.


Another logging function is available for logging DEBUG messages. Normally these messages are not printed.
you can hold CTRL and click on a command button to put that command in DEBUG mode and see all its debug messages""")

print_code("logger.debug('Yesss! Here is the debug message')")
print("Now try CTRL-clicking this button you should see a DEBUG message printed here:")
su.logger.debug('Yesss! Here is the debug message')

# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("#### Shift-Clicking: Script Configuration:")
print("""You can create a script called 'config.py' in your button bundle.
SHIFT-clicking on a ui button will run the configuration script.
Try Shift clicking on the Match tool in pyRevit > Modify panel and see the configuration window.""")
print_code("config.py\nscript.py")
print("""If you don't define the configuration script, you can check the value of __shiftclick__ in your scripts
to change script behaviour""")
print_code("""if __shiftclick__:
    do_task_A()
else:
    do_task_B()""")


# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("#### Script Information:")
print("""'scriptutils' module also provides a class to access the running script information and utilities:
""")

print_code("""from scriptutils import this_script

# script name
this_script.info.name""")

print_code("""# script ui title (value set by __title__)
this_script.info.ui_title""")
print_code("""# script unique name, generally used to create IExternalCommand class names
this_script.info.unique_name""")
print_code("""# script unique name, generally used to create IExternalCommandAvailability class names
this_script.info.unique_avail_name""")
print_code("""# script's command context (set by __context__)
this_script.info.cmd_context""")

print_code("""# script's tooltip (set by script docstring or __doc__)
this_script.info.doc_string""")
print_code("""# script's author (set by __author__)
this_script.info.author""")

print_code("""# script file address
this_script.info.script_file""")
print_code("""# script configuration file address
this_script.info.config_script_file""")
print_code("""# script default icon file
this_script.info.icon_file""")

print_code("""# script's library path if the script bundle includes a library
this_script.info.library_path""")

print_code("""# Accessing the running pyRevit version
this_script.pyrevit_version""")

# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("#### Custom User Configuration for Scripts:")
print("""Each script can save and load configuration pyRevit's user configuration file:
""")
print_code("""from scriptutils import this_script

# set a new config parameter: firstparam
this_script.config.firstparam = True

# saving configurations
this_script.save_config()

# read the config parameter value
if this_script.config.firstparam:
    do_task_A()""")


# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("#### Using temporary files easily:")
print_code('this_script.data_filename')

# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("""#### Controlling Output Window:
Each script can control its own output window:""")
print_code("""from scriptutils import this_script

this_script.output.set_height(600)
this_script.output.get_title()
this_script.output.set_title('Beautiful title')""")

# ----------------------------------------------------------------------------------------------------------------------
print('\n\n\n')
print_md("#### Misc:")

# __commandname__
# __commandpath__
# __assmcustomattrs__
# __window__
# __file__
#
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
# print 'File: {}'.format(__file__)
# print 'Forced Debug: {}'.format(__forceddebugmode__)
# print 'Message: {}'.format(__message__)
# print 'Result: {}'.format(__result__)
#
#
# # smart button template ------------------------------------------------------------------------------------------------
# def __selfinit__(script_cmp, commandbutton, __rvt__):
#     pass




# print_md("""
# # Heading
#
# ## Sub-heading
#
# ### Another deeper heading
#
# Paragraphs are separated
# by a blank line.
#
# Two spaces at the end of a line leave a
# line break.
#
# Text attributes _italic_, *italic*, __bold__, **bold**, `monospace`.
#
# Horizontal rule:
#
# ---
#
# Bullet list:
#
#   * apples
#   * oranges
#   * pears
#
# Numbered list:
#
#   1. apples
#   2. oranges
#   3. pears
#
# A [very important link](http://example.com).
#
# """)
