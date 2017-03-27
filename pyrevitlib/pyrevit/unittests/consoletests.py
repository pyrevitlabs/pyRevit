from unittest import TestCase
from pyrevit.coreutils.console.output import output_window

# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons


class TestConsoleWindow(TestCase):
    def setUp(self):
        self._console = output_window

    def test_progressbar(self):
        """Output window progress bar test"""
        from time import sleep
        for i in range(50):
            sleep(0.01)
            self._console.update_progress(i+1, 50)

        res = TaskDialog.Show('pyrevit', 'Did you see the progress bar?',
                              TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No)
        self.assertEqual(str(res), 'Yes')
