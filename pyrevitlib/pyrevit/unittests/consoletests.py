from unittest import TestCase
from pyrevit.coreutils.console.output import output_window


class TestConsoleWindow(TestCase):
    def setUp(self):
        self._console = output_window

    def test_progressbar(self):
        """Output window progress bar test"""
        from time import sleep
        for i in range(100):
            sleep(0.01)
            self._console.update_progress(i+1, 100)
        return True
