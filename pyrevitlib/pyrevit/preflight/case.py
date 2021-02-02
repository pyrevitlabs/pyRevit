"""Base Preflight test class that defines the minimum interface."""
# pylama:ignore=D401


class PreflightTestCase(object):
    """Base class for preflight tests."""

    def setUp(self, doc, output):
        """Hook method for setting up the test before exercising it."""
        pass

    def startTest(self, doc, output):
        """Hook method for exercising the test."""
        pass

    def tearDown(self, doc, output):
        """Hook method for deconstructing the test after testing it."""
        pass

    def doCleanups(self, doc, output):
        """Execute all cleanup functions. Normally called after tearDown."""
        pass
