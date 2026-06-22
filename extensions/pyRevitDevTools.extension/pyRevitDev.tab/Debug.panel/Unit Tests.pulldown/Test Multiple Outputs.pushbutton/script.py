"""Test opening multiple output windows."""
#pylint: disable=import-error,line-too-long
from pyrevit.loader import sessionmgr


for cmd in ["pyrevitdevtools_pyrevitdev_debug_unittests_testprojectparameters",
            "pyrevittools_pyrevit_selection_select_select_listselectionasclickablelinks"]:
    for i in range(5):
        sessionmgr.execute_command(cmd)
