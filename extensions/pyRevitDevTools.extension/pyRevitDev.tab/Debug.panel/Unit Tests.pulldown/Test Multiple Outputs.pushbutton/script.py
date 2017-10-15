__context__ = 'zerodoc'


from pyrevit.loader.sessionmgr import execute_command

commandlist = ["pyRevitDevToolspyRevitDevDebugUnitTestsTestRPW",
               "pyRevitToolspyRevitSelectionselectSelectListSelectionasClickableLinks"]

for cmd in commandlist:
    for i in range(5):
        execute_command(cmd)
