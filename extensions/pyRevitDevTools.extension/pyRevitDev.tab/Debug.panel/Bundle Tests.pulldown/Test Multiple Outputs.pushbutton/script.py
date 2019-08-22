"""Test opening multiple output windows."""
#pylint: disable=import-error,line-too-long
from pyrevit.loader import sessionmgr

__context__ = 'zerodoc'

for cmd in ["pyrevitdevtools-pyrevitdev-debug-misctests-testrpw",
            "pyrevittools-pyrevit-selection-select-select-listselectionasclickablelinks"]:
    for i in range(5):
        sessionmgr.execute_command(cmd)
