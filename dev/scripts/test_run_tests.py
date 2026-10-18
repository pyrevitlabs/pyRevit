"""Contracts for repository test selection and coverage accounting."""

import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import run_tests
import conftest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


class SelectionTests(unittest.TestCase):
    """Ensure discovery fails closed before importing hosted modules."""

    def test_hosted_module_is_classified_without_import(self):
        """A hosted suite can be inspected without executing its imports."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_hosted.py"
            path.write_text(
                'TEST_ENVIRONMENT = "Revit"\nTEST_LEVEL = "Integration"\n'
                'raise RuntimeError("must not import")\n',
                encoding="utf-8",
            )
            self.assertEqual("Revit", run_tests.python_metadata(path)["Environment"])

    def test_missing_classification_is_an_error(self):
        """An ordinary new suite cannot disappear through missing metadata."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_missing.py"
            path.write_text("import unittest\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "TEST_ENVIRONMENT"):
                run_tests.python_metadata(path)

    def test_coverage_drop_fails_per_module(self):
        """A strong module cannot mask a second module's regression."""
        baseline = {"parser": {"line": 0.8, "branch": 0.6}}
        with self.assertRaisesRegex(ValueError, "parser"):
            run_tests.check_baselines(
                {"parser": {"line": 0.79, "branch": 0.7}}, baseline
            )

    def test_missing_module_coverage_fails(self):
        """Missing evidence cannot silently remove an established module."""
        with self.assertRaisesRegex(ValueError, "Missing coverage"):
            run_tests.check_baselines({}, {"parser": {"line": 0.8, "branch": 0.6}})

    def test_empty_trx_is_not_success(self):
        """A successful process with zero executed tests fails validation."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.trx"
            path.write_text(
                '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">'
                '<ResultSummary><Counters total="0" executed="0" failed="0"/>'
                "</ResultSummary></TestRun>",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "zero"):
                run_tests.validate_trx(path)

    def test_class_defaults_can_exclude_a_hosted_case(self):
        """A Revit class remains local within an otherwise host-free module."""
        item = SimpleNamespace(
            module=SimpleNamespace(TEST_ENVIRONMENT="HostFree", TEST_LEVEL="Unit"),
            cls=SimpleNamespace(TEST_ENVIRONMENT="Revit", TEST_LEVEL="Integration"),
            get_closest_marker=lambda name: None,
        )
        self.assertEqual(("Revit", "Integration"), conftest.classification(item))

    def test_method_cannot_downgrade_a_revit_fixture(self):
        """A local fixture cannot be selected through a host-free override."""
        item = SimpleNamespace(
            module=SimpleNamespace(TEST_ENVIRONMENT="Revit", TEST_LEVEL="Integration"),
            cls=None,
            nodeid="hosted",
            get_closest_marker=lambda name: (
                SimpleNamespace(args=("HostFree",)) if name == "environment" else None
            ),
        )
        with self.assertRaises(pytest.UsageError):
            conftest.classification(item)

    def test_coverage_merges_branch_identities_and_ignores_deployment_copies(self):
        """Two suites can cover opposite branches without double-counting artifacts."""
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory)
            for project, hits in (("first", 1), ("second", 0)):
                path = results / project / "net8.0" / "run" / "coverage.json"
                path.parent.mkdir(parents=True)
                data = {
                    "Example.dll": {
                        str(run_tests.ROOT / "dev/example/source.cs"): {
                            "Example": {
                                "Method": {
                                    "Lines": {"1": 1},
                                    "Branches": [
                                        {
                                            "Line": 1,
                                            "Offset": 0,
                                            "EndOffset": 1,
                                            "Path": 0,
                                            "Hits": hits,
                                        },
                                        {
                                            "Line": 1,
                                            "Offset": 0,
                                            "EndOffset": 2,
                                            "Path": 1,
                                            "Hits": 1 - hits,
                                        },
                                    ],
                                }
                            }
                        }
                    }
                }
                path.write_text(json.dumps(data), encoding="utf-8")
            duplicate = results / "first/net8.0/deployment/In/machine/coverage.json"
            duplicate.parent.mkdir(parents=True)
            duplicate.write_text(json.dumps(data), encoding="utf-8")
            measured = run_tests.collect_coverage(results)
            self.assertEqual({"dotnet/Example/net8.0"}, set(measured))
            self.assertEqual(1, measured["dotnet/Example/net8.0"]["branch"])
            self.assertEqual(2, measured["dotnet/Example/net8.0"]["branches"])

    def test_vendored_sources_never_count_as_product_coverage(self):
        """Referenced dependencies stay out of first-party module baselines."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project/net8.0/run/coverage.json"
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "Vendored.dll": {
                            str(run_tests.ROOT / "dev/modules/vendor/code.cs"): {}
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual({}, run_tests.collect_coverage(Path(directory)))
