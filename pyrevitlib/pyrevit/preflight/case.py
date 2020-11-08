"""Base Preflight test class that defines the minimum interface."""
# pylama:ignore=D401


class PreflightTestCase(object):
    """Base class for preflight tests."""

    def setUp(self):
        """Hook method for setting up the test before exercising it."""
        pass

    def startTest(self):
        """Hook method for exercising the test."""
        pass

    def tearDown(self):
        """Hook method for deconstructing the test after testing it."""
        pass

    def doCleanups(self):
        """Execute all cleanup functions. Normally called after tearDown."""
        pass
