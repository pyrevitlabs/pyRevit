from pyrevit.loader.sessionmgr import execute_command


__context__ = 'zerodoc'


commandlist = \
    ["pyRevitDevToolspyRevitDevDebugUnitTestsTestRPW",
     "pyRevitToolspyRevitSelectionselectSelectListSelectionasClickableLinks"]

for cmd in commandlist:
    for i in range(5):
        execute_command(cmd)
