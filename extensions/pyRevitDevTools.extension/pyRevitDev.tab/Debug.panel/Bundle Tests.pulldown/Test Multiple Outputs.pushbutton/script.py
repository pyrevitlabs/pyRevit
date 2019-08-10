"""Test opening multiple output windows."""
#pylint: disable=import-error,line-too-long
from pyrevit.loader.sessionmgr import execute_command

__context__ = 'zerodoc'

for cmd in ["pyrevitdevtools-pyrevitdev-debug-misctests-testrpw",
            "pyrevittools-pyrevit-selection-select-select-listselectionasclickablelinks"]:
    for i in range(5):
        execute_command(cmd)
