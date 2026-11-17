"""Base Preflight test class that defines the minimum interface."""
# pylama:ignore=D401

from pyrevit.preflight import results


class PreflightTestCase(object):
    """Base class for preflight tests.

    A check prints its report to the output window. It can also record what it
    found with `report`, which makes the run's result structured and exportable,
    see `pyrevit.preflight.results`.
    """

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

    @property
    def findings(self):
        """list[results.Finding]: findings reported so far, in reporting order."""
        findings = self.__dict__.get("_preflight_findings")
        if findings is None:
            findings = []
            self.__dict__["_preflight_findings"] = findings
        return findings

    def report(
        self,
        rule,
        message,
        status=results.STATUS_FAIL,
        severity=results.SEVERITY_WARNING,
        element_ids=None,
        data=None,
    ):
        """Records a finding of this check.

        Note:
            Report a ``results.STATUS_PASS`` finding when a rule finds nothing
            wrong. A run without findings is ``not_reported``, not clean.

        Args:
            rule (str): stable, untranslated id of the rule, such as
                ``"schedules.not-on-sheet"``.
            message (str): what was found, for a person reading the result.
            status (str): ``results.STATUS_FAIL`` (default) or ``results.STATUS_PASS``.
            severity (str): ``results.SEVERITY_WARNING`` (default),
                ``results.SEVERITY_INFO`` or ``results.SEVERITY_ERROR``.
            element_ids (Iterable): ids, ``ElementId`` objects or elements involved.
            data (dict): optional JSON serializable extra values.

        Returns:
            results.Finding: the recorded finding.

        Raises:
            ValueError: for invalid values, see `results.Finding`.
            TypeError: for an element id that cannot be read.
        """
        finding = results.Finding(
            rule,
            message,
            status=status,
            severity=severity,
            element_ids=element_ids,
            data=data,
        )
        self.findings.append(finding)
        return finding
