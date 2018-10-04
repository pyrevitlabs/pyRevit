from unittest import TestCase

from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons   #pylint: disable=E0401

from pyrevit.compat import safe_strtype
from pyrevit.output import get_output


class TestOutputWindow(TestCase):
    def setUp(self):
        self._output = get_output()

    def test_progressbar(self):
        """Output window progress bar test"""
        from time import sleep
        for i in range(50):
            sleep(0.01)
            self._output.update_progress(i+1, 50)

        res = TaskDialog.Show('pyrevit', 'Did you see the progress bar?',
                              TaskDialogCommonButtons.Yes |
                              TaskDialogCommonButtons.No)
        self.assertEqual(safe_strtype(res), 'Yes')
