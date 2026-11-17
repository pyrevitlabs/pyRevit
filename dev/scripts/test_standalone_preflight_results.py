"""Exercise structured preflight results and their export without a Revit host (#1267)."""

import codecs
import csv
import importlib.util
import io
import json
import logging
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PREFLIGHT_ROOT = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit", "preflight")
TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


results = _load_module(
    "_test_preflight_results", os.path.join(PREFLIGHT_ROOT, "results.py")
)


def _load_preflight_package():
    """Load the real preflight package with only pyrevit host modules replaced."""
    pyrevit = types.ModuleType("pyrevit")
    logger = types.ModuleType("pyrevit.coreutils.logger")
    logger.get_logger = logging.getLogger
    extensions = types.ModuleType("pyrevit.extensions")
    extensions.COMP_CHECK_POSTFIX = "_check.py"
    extensions.extensionmgr = MagicMock()
    extensions.extpackages = MagicMock()
    package = types.ModuleType("pyrevit.preflight")
    package.__path__ = [PREFLIGHT_ROOT]
    package.results = results
    modules = {
        "pyrevit": pyrevit,
        "pyrevit.coreutils": MagicMock(),
        "pyrevit.coreutils.logger": logger,
        "pyrevit.extensions": extensions,
        "pyrevit.preflight": package,
        "pyrevit.preflight.results": results,
    }
    with patch.dict(sys.modules, modules):
        case = _load_module(
            "pyrevit.preflight.case", os.path.join(PREFLIGHT_ROOT, "case.py")
        )
        sys.modules["pyrevit.preflight.case"] = case
        preflight = _load_module(
            "_test_preflight_package", os.path.join(PREFLIGHT_ROOT, "__init__.py")
        )
    return case, preflight


class FakeElementId(object):
    """Mimics ``ElementId`` on Revit 2024+ (``Value``) and earlier (``IntegerValue``)."""

    def __init__(self, value=None, integer_value=None):
        if value is not None:
            self.Value = value
        if integer_value is not None:
            self.IntegerValue = integer_value


class FakeElement(object):
    """Mimics an element, which carries its id in ``Id``."""

    def __init__(self, element_id):
        self.Id = element_id


class FakeDocument(object):
    """Mimics the document properties a run records."""

    Title = "Tower A - Architecture"
    PathName = "C:\\Projects\\Tower A\\Tower A - Architecture.rvt"


class ElementIdValueTests(unittest.TestCase):
    """Element ids are read the same way on every supported Revit version."""

    def test_plain_integer(self):
        self.assertEqual(results.element_id_value(42), 42)

    def test_revit_2024_and_newer_value(self):
        self.assertEqual(results.element_id_value(FakeElementId(value=2**40)), 2**40)

    def test_revit_before_2024_integer_value(self):
        self.assertEqual(results.element_id_value(FakeElementId(integer_value=7)), 7)

    def test_value_is_preferred_over_deprecated_integer_value(self):
        element_id = FakeElementId(value=2**40, integer_value=-1)
        self.assertEqual(results.element_id_value(element_id), 2**40)

    def test_element_is_read_through_its_id(self):
        element = FakeElement(FakeElementId(value=9))
        self.assertEqual(results.element_id_value(element), 9)

    def test_element_value_is_not_mistaken_for_its_id(self):
        dimension = FakeElement(FakeElementId(value=314))
        dimension.Value = 3.5
        self.assertEqual(results.element_id_value(dimension), 314)

    def test_boolean_is_rejected(self):
        with self.assertRaises(TypeError):
            results.element_id_value(True)

    def test_text_is_rejected_even_when_numeric(self):
        with self.assertRaises(TypeError):
            results.element_id_value("123")

    def test_unreadable_object_is_rejected(self):
        with self.assertRaises(TypeError):
            results.element_id_value(object())


class FindingTests(unittest.TestCase):
    """Findings validate on creation, so a broken check fails while it runs."""

    def test_defaults_report_a_warning_failure(self):
        finding = results.Finding("refplanes.unnamed", "Reference plane has no name")
        self.assertEqual(finding.status, results.STATUS_FAIL)
        self.assertEqual(finding.severity, results.SEVERITY_WARNING)
        self.assertTrue(finding.failed)
        self.assertEqual(finding.element_ids, [])
        self.assertEqual(finding.data, {})

    def test_element_ids_are_unique_and_keep_reporting_order(self):
        finding = results.Finding(
            "r", "m", element_ids=[3, FakeElementId(value=1), 3, FakeElement(1), 2]
        )
        self.assertEqual(finding.element_ids, [3, 1, 2])

    def test_to_dict(self):
        finding = results.Finding(
            "schedules.not-on-sheet",
            "Schedule is not placed on a sheet",
            severity=results.SEVERITY_INFO,
            element_ids=[5],
            data={"schedule": "Door Schedule"},
        )
        self.assertEqual(
            finding.to_dict(),
            {
                "rule": "schedules.not-on-sheet",
                "status": "fail",
                "severity": "info",
                "message": "Schedule is not placed on a sheet",
                "element_ids": [5],
                "data": {"schedule": "Door Schedule"},
            },
        )

    def test_data_is_copied(self):
        data = {"count": 1}
        finding = results.Finding("r", "m", data=data)
        data["count"] = 2
        self.assertEqual(finding.data, {"count": 1})

    def test_invalid_values_are_rejected(self):
        invalid = [
            dict(rule="", message="m"),
            dict(rule="   ", message="m"),
            dict(rule=None, message="m"),
            dict(rule="r", message=""),
            dict(rule="r", message="m", status="failed"),
            dict(rule="r", message="m", severity="critical"),
            dict(rule="r", message="m", data=["not", "a", "dict"]),
            dict(rule="r", message="m", data={"value": object()}),
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    results.Finding(**kwargs)


def _result(*findings, **kwargs):
    result = results.CheckResult(
        check=kwargs.get("check", "Schedules not on sheets"),
        check_id="pyRevitTools/schedules_not_on_sheet.ModelChecker",
        extension="pyRevitTools",
        document_title=kwargs.get("document_title", "Tower A"),
        document_path="C:\\Projects\\Tower A.rvt",
        started=0.0,
    )
    result.finish(findings, ended=1.25)
    return result


class CheckResultTests(unittest.TestCase):
    """Run status and summary never present an unreported check as clean."""

    def test_run_without_findings_is_not_reported(self):
        self.assertEqual(_result().status, results.STATUS_NOT_REPORTED)

    def test_all_passing_findings_pass(self):
        result = _result(results.Finding("r", "ok", status=results.STATUS_PASS))
        self.assertEqual(result.status, results.STATUS_PASS)

    def test_any_failure_fails(self):
        result = _result(
            results.Finding("r", "ok", status=results.STATUS_PASS),
            results.Finding("r", "bad", severity=results.SEVERITY_INFO),
        )
        self.assertEqual(result.status, results.STATUS_FAIL)

    def test_summary_counts(self):
        result = _result(
            results.Finding("a", "ok", status=results.STATUS_PASS, element_ids=[1]),
            results.Finding(
                "b", "bad", severity=results.SEVERITY_ERROR, element_ids=[1, 2]
            ),
            results.Finding("c", "bad", element_ids=[3]),
        )
        self.assertEqual(
            result.summary(),
            {
                "findings": 3,
                "passed": 1,
                "failed": 2,
                "elements": 3,
                "failed_by_severity": {"info": 0, "warning": 1, "error": 1},
            },
        )

    def test_add_rejects_anything_but_a_finding(self):
        with self.assertRaises(TypeError):
            _result().add({"rule": "r"})

    def test_duration_is_never_negative(self):
        result = results.CheckResult("c", started=10.0)
        result.finish(ended=5.0)
        self.assertEqual(result.duration, 0.0)

    def test_to_dict_schema(self):
        data = _result(results.Finding("r", "m", element_ids=[1])).to_dict()
        self.assertEqual(data["schema_version"], results.SCHEMA_VERSION)
        self.assertEqual(data["started"], "1970-01-01T00:00:00Z")
        self.assertEqual(data["duration_s"], 1.25)
        self.assertEqual(data["status"], "fail")
        self.assertEqual(data["document"]["title"], "Tower A")
        self.assertEqual(
            data["check_id"], "pyRevitTools/schedules_not_on_sheet.ModelChecker"
        )
        self.assertEqual(len(data["findings"]), 1)

    def test_json_round_trips_and_escapes_non_ascii(self):
        result = _result(results.Finding("r", "Bürogebäude: Wand ohne Typ"))
        text = result.to_json()
        self.assertTrue(all(ord(char) < 128 for char in text))
        self.assertEqual(json.loads(text), result.to_dict())

    def test_csv_rows_one_per_element_and_one_without_elements(self):
        result = _result(
            results.Finding("a", "two", element_ids=[1, 2]),
            results.Finding("b", "none"),
        )
        rows = result.csv_rows()
        self.assertEqual([row[-1] for row in rows], ["1", "2", ""])
        self.assertEqual([row[6] for row in rows], ["a", "a", "b"])
        self.assertTrue(all(len(row) == len(results.CSV_COLUMNS) for row in rows))


class WriteTests(unittest.TestCase):
    """Results are written in the format the file extension names."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)
        patcher = patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(results.PATH_ENV_VAR, None)

    def _path(self, name):
        return os.path.join(self.folder, "nested", name)

    def test_json_replaces_the_file(self):
        path = self._path("result.json")
        results.write(_result(results.Finding("first", "m")), path)
        results.write(_result(results.Finding("second", "m")), path)
        with io.open(path, encoding="utf-8") as results_file:
            data = json.load(results_file)
        self.assertEqual([f["rule"] for f in data["findings"]], ["second"])

    def test_jsonl_appends_one_line_per_run(self):
        path = self._path("results.jsonl")
        results.write(_result(results.Finding("r", "m"), document_title="A"), path)
        results.write(_result(document_title="B"), path)
        with io.open(path, encoding="utf-8") as results_file:
            lines = results_file.read().splitlines()
        self.assertEqual(
            [json.loads(line)["document"]["title"] for line in lines], ["A", "B"]
        )

    def test_csv_writes_header_and_bom_once_and_reads_back(self):
        path = self._path("results.csv")
        tricky = 'Wall "Type 1", 200mm\nFire rated, Gebäude'
        results.write(_result(results.Finding("r", tricky, element_ids=[1, 2])), path)
        results.write(_result(results.Finding("r2", "plain")), path)
        with open(path, "rb") as raw_file:
            raw = raw_file.read()
        self.assertTrue(raw.startswith(codecs.BOM_UTF8))
        self.assertEqual(raw.count(codecs.BOM_UTF8), 1)
        with io.open(path, encoding="utf-8-sig", newline="") as results_file:
            rows = list(csv.reader(results_file))
        self.assertEqual(rows[0], list(results.CSV_COLUMNS))
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1][9], tricky)
        self.assertEqual([row[10] for row in rows[1:]], ["1", "2", ""])

    def test_unknown_extension_is_rejected(self):
        with self.assertRaises(ValueError):
            results.write(_result(), self._path("results.xlsx"))

    def test_nothing_is_written_when_off(self):
        self.assertIsNone(results.write(_result()))

    def test_environment_variable_selects_the_path(self):
        path = self._path("from-env.jsonl")
        os.environ[results.PATH_ENV_VAR] = "  %s  " % path
        self.assertEqual(results.write(_result()), path)
        self.assertTrue(os.path.isfile(path))

    def test_blank_environment_variable_is_off(self):
        os.environ[results.PATH_ENV_VAR] = "   "
        self.assertIsNone(results.report_path())


class PreflightTestCaseReportTests(unittest.TestCase):
    """Checks record findings through ``report`` without changing their hooks."""

    @classmethod
    def setUpClass(cls):
        cls.case, _ = _load_preflight_package()

    def test_report_records_in_order_and_returns_the_finding(self):
        check = self.case.PreflightTestCase()
        first = check.report("a", "first", element_ids=[FakeElementId(value=1)])
        check.report("b", "second", status=results.STATUS_PASS)
        self.assertEqual([f.rule for f in check.findings], ["a", "b"])
        self.assertIs(check.findings[0], first)
        self.assertEqual(first.element_ids, [1])

    def test_findings_belong_to_one_instance(self):
        first, second = self.case.PreflightTestCase(), self.case.PreflightTestCase()
        first.report("a", "m")
        self.assertEqual(second.findings, [])

    def test_subclass_with_own_init_can_report(self):
        class LegacyCheck(self.case.PreflightTestCase):
            def __init__(self):
                self.counter = 0

        check = LegacyCheck()
        check.report("a", "m")
        self.assertEqual(len(check.findings), 1)

    def test_invalid_report_raises(self):
        with self.assertRaises(ValueError):
            self.case.PreflightTestCase().report("a", "m", severity="fatal")


class RunPreflightCheckTests(unittest.TestCase):
    """``run_preflight_check`` returns the findings and writes them when asked."""

    def setUp(self):
        self.case, self.preflight = _load_preflight_package()
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)
        patcher = patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(results.PATH_ENV_VAR, None)

    def _check(self, check_type):
        check = MagicMock()
        check.name = "Unnamed reference planes"
        check.extension = "pyRevitTools"
        check.script_path = os.path.join(self.folder, "refplanes_check.py")
        check.check_case = check_type
        return check

    def _reporting_check_type(self):
        calls = []

        class ReportingCheck(self.case.PreflightTestCase):
            def setUp(self, doc, output):
                calls.append("setUp")

            def startTest(self, doc, output):
                calls.append("startTest")
                self.report("refplanes.unnamed", "No name", element_ids=[11, 12])

            def tearDown(self, doc, output):
                calls.append("tearDown")

            def doCleanups(self, doc, output):
                calls.append("doCleanups")

        return ReportingCheck, calls

    def test_returns_the_reported_findings(self):
        check_type, calls = self._reporting_check_type()
        result = self.preflight.run_preflight_check(
            self._check(check_type), FakeDocument(), MagicMock()
        )
        self.assertEqual(calls, ["setUp", "startTest", "tearDown", "doCleanups"])
        self.assertEqual(result.status, results.STATUS_FAIL)
        self.assertEqual(result.findings[0].element_ids, [11, 12])
        self.assertEqual(result.check_id, "pyRevitTools/refplanes.ReportingCheck")
        self.assertEqual(result.document_title, FakeDocument.Title)
        self.assertEqual(result.document_path, FakeDocument.PathName)

    def test_check_that_never_reports_is_not_reported(self):
        class SilentCheck(self.case.PreflightTestCase):
            def startTest(self, doc, output):
                output.print_md("printed only")

        result = self.preflight.run_preflight_check(
            self._check(SilentCheck), FakeDocument(), MagicMock()
        )
        self.assertEqual(result.status, results.STATUS_NOT_REPORTED)

    def test_writes_the_result_when_the_environment_variable_is_set(self):
        path = os.path.join(self.folder, "out", "results.json")
        os.environ[results.PATH_ENV_VAR] = path
        check_type, _ = self._reporting_check_type()
        self.preflight.run_preflight_check(
            self._check(check_type), FakeDocument(), MagicMock()
        )
        with io.open(path, encoding="utf-8") as results_file:
            self.assertEqual(json.load(results_file)["status"], "fail")

    def test_write_failure_is_logged_and_the_result_still_returned(self):
        blocker = os.path.join(self.folder, "not-a-folder")
        open(blocker, "w").close()
        os.environ[results.PATH_ENV_VAR] = os.path.join(blocker, "results.json")
        check_type, _ = self._reporting_check_type()
        with self.assertLogs(level="ERROR"):
            result = self.preflight.run_preflight_check(
                self._check(check_type), FakeDocument(), MagicMock()
            )
        self.assertEqual(result.status, results.STATUS_FAIL)

    def test_check_exception_propagates_and_nothing_is_written(self):
        path = os.path.join(self.folder, "results.json")
        os.environ[results.PATH_ENV_VAR] = path

        class BrokenCheck(self.case.PreflightTestCase):
            def startTest(self, doc, output):
                raise RuntimeError("broken check")

        with self.assertRaises(RuntimeError):
            self.preflight.run_preflight_check(
                self._check(BrokenCheck), FakeDocument(), MagicMock()
            )
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
