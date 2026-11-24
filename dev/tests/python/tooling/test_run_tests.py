"""Contracts for repository test selection and coverage accounting."""

import tempfile
import unittest
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET

import pytest

from dev.tests import run_tests
import conftest

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Unit"


@pytest.mark.level("Integration")
@pytest.mark.parametrize(
    "second_module, expected_status",
    [
        ("", 4),
        (
            '@pytest.mark.environment("Revit")\ndef test_hosted():\n'
            '    raise AssertionError("must not execute")\n',
            4,
        ),
        ("def test_second():\n    assert True\n", 0),
    ],
    ids=["empty-module", "all-revit-module", "both-eligible"],
)
def test_each_explicit_python_module_requires_eligible_cases(
    second_module, expected_status
):
    """A populated neighbor must not hide an empty or entirely hosted suite."""
    with tempfile.TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        (tmp_path / "conftest.py").write_text(
            Path(conftest.__file__).read_text(encoding="utf-8"), encoding="utf-8"
        )
        metadata = 'import pytest\nTEST_ENVIRONMENT = "HostFree"\nTEST_LEVEL = "Unit"\n'
        first = tmp_path / "test_first.py"
        second = tmp_path / "test_second.py"
        first.write_text(
            metadata + "def test_first():\n    assert True\n", encoding="utf-8"
        )
        second.write_text(metadata + second_module, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(first), str(second)],
            cwd=tmp_path,
            env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == expected_status, result.stdout + result.stderr
        if expected_status:
            assert "test_second.py" in result.stderr
            assert "no eligible cases" in result.stderr


class SelectionTests(unittest.TestCase):
    """Ensure discovery fails closed before importing hosted modules."""

    def test_windows_document_casing_does_not_duplicate_coverage(self):
        """MSBuild references can spell one Windows source path with different casing."""
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory)
            for suite, filename, hit in (
                ("first", "Source.cs", 1),
                ("second", "source.cs", 0),
            ):
                report = results / suite / "net48" / "run" / "coverage.json"
                report.parent.mkdir(parents=True)
                report.write_text(
                    json.dumps(
                        {
                            "Example.dll": {
                                str(run_tests.ROOT / "dev/example" / filename): {
                                    "Example": {
                                        "Method": {"Lines": {"1": hit}, "Branches": []}
                                    }
                                }
                            }
                        }
                    ),
                    encoding="utf-8",
                )
            with patch(
                "dev.tests.run_tests.os.path.normcase", side_effect=str.casefold
            ):
                measured = run_tests.collect_coverage(results)
            self.assertEqual(1, measured["dotnet/Example/net48"]["lines"])
            self.assertEqual(1, measured["dotnet/Example/net48"]["line"])

    def test_skipped_result_is_rejected_even_when_counters_omit_it(self):
        """NUnit can emit NotExecuted results without incrementing its skip counter."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skipped.trx"
            path.write_text(
                '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">'
                '<Results><UnitTestResult outcome="Passed"/>'
                '<UnitTestResult outcome="NotExecuted"/></Results>'
                '<ResultSummary><Counters total="2" executed="1" failed="0" notExecuted="0"/>'
                "</ResultSummary></TestRun>",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "did not pass"):
                run_tests.validate_trx(path)

    def test_shell_suite_runs_once_per_engine_with_separate_reports(self):
        """Both IronPython engines run, and neither overwrites the other's evidence."""
        project = {
            "path": "dev/pyRevitLabs/tests/pyRevitLabs.PyRevit.Shell.Tests/"
            "pyRevitLabs.PyRevit.Shell.Tests.csproj",
            "framework": "net10.0-windows",
            "tests": [{"Environment": "HostFree"}],
            "engines": ["IPY2712PR", "IPY342"],
        }
        self.assertEqual(["IPY2712PR", "IPY342"], run_tests.engine_variants(project))
        self.assertEqual(
            [None],
            run_tests.engine_variants({"path": "Other.Tests.csproj", "engines": []}),
        )
        calls = []

        def fake_command(arguments):
            calls.append(arguments)
            reports = Path(arguments[arguments.index("--results-directory") + 1])
            (reports / "run").mkdir(parents=True, exist_ok=True)
            (reports / "run" / "coverage.cobertura.xml").write_text("<coverage/>")
            (reports / "run" / "coverage.json").write_text("{}")
            (reports / "results.trx").write_text(
                '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">'
                '<Results><UnitTestResult outcome="Passed"/></Results>'
                '<ResultSummary><Counters total="1" executed="1" failed="0"/>'
                "</ResultSummary></TestRun>",
                encoding="utf-8",
            )

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(run_tests, "command", side_effect=fake_command),
        ):
            results = Path(directory)
            outcomes = [
                run_tests.run_dotnet(project, results, engine)
                for engine in run_tests.engine_variants(project)
            ]
            self.assertTrue(
                (results / "pyRevitLabs.PyRevit.Shell.Tests.IPY2712PR").is_dir()
            )
            self.assertTrue(
                (results / "pyRevitLabs.PyRevit.Shell.Tests.IPY342").is_dir()
            )
        self.assertIn("-p:IronPythonVersion=IPY2712PR", calls[0])
        self.assertIn("-p:IronPythonVersion=IPY342", calls[1])
        self.assertEqual(["IPY2712PR", "IPY342"], [o["engine"] for o in outcomes])

    def _run_fake_dotnet(self, tests, executed, reports=("coverage.cobertura.xml",)):
        project = {
            "path": "Example.Tests.csproj",
            "framework": "net8.0",
            "tests": tests,
        }

        def fake_command(arguments):
            directory = Path(arguments[arguments.index("--results-directory") + 1])
            (directory / "run").mkdir(parents=True, exist_ok=True)
            for report in reports:
                (directory / "run" / report).write_text("{}")
            (directory / "results.trx").write_text(
                '<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">'
                "<Results>"
                + '<UnitTestResult outcome="Passed"/>'
                * executed
                + "</Results><ResultSummary>"
                f'<Counters total="{executed}" executed="{executed}" failed="0"/>'
                "</ResultSummary></TestRun>",
                encoding="utf-8",
            )

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(run_tests, "command", side_effect=fake_command),
        ):
            return run_tests.run_dotnet(project, Path(directory))

    def test_fewer_executed_than_cataloged_host_free_tests_fails(self):
        """A trait drift cannot silently drop tests that discovery classified."""
        tests = [{"Environment": "HostFree"}] * 3 + [{"Environment": "Revit"}]
        with self.assertRaisesRegex(
            ValueError, r"Example\.Tests net8\.0: executed 2 .* 3 host-free"
        ):
            self._run_fake_dotnet(tests, 2, ("coverage.cobertura.xml", "coverage.json"))
        outcome = self._run_fake_dotnet(
            tests, 4, ("coverage.cobertura.xml", "coverage.json")
        )
        self.assertEqual("4", outcome["executed"])

    def test_missing_json_coverage_report_fails(self):
        """Coverage aggregation reads coverage.json, so it is required evidence."""
        with self.assertRaisesRegex(ValueError, "coverage.json"):
            self._run_fake_dotnet([{"Environment": "HostFree"}], 1)

    def test_engine_dependent_suites_declare_both_engines(self):
        """The shell and IronPython forms suites must keep passing on both engines."""
        for name in (
            "pyRevitLabs.PyRevit.Shell.Tests",
            "pyRevitLabs.PyRevit.Forms.IronPython.Tests",
        ):
            project = ET.parse(
                run_tests.ROOT / f"dev/pyRevitLabs/tests/{name}/{name}.csproj"
            )
            self.assertEqual(
                ["IPY2712PR", "IPY342"],
                run_tests.declared_engines(
                    name, project.findtext(".//PyRevitTestEngines")
                ),
            )

    def test_unknown_declared_engine_fails_with_the_allowed_engines(self):
        """A typo in a project's engine list cannot drop or rename an engine run."""
        self.assertEqual([], run_tests.declared_engines("Example.Tests", ""))
        with self.assertRaisesRegex(
            ValueError, r"Example\.Tests.*\['IPY343'\].*\['IPY2712PR', 'IPY342'\]"
        ):
            run_tests.declared_engines("Example.Tests", "IPY2712PR;IPY343")

    def test_project_evaluations_run_concurrently_in_discovery_order(self):
        """Discovery pays one evaluation latency per pass, not one per project."""
        outer = threading.Barrier(2, timeout=5)
        inner = threading.Barrier(4, timeout=5)

        def fake_evaluate(path, framework=None):
            (inner if framework else outer).wait()
            if framework:
                return {
                    "Properties": {
                        "AssemblyName": f"{path.stem}.{framework}",
                        "DefineConstants": f";{framework.upper()};",
                        "PyRevitTestEngines": "IPY342"
                        if path.stem == "Second.Tests"
                        else "",
                    },
                    "Items": {"Compile": [{"FullPath": f"{path.stem}.cs"}]},
                }
            return {
                "Properties": {
                    "IsTestProject": "true",
                    "TargetFrameworks": "net48;net8.0",
                    "TargetFramework": "",
                },
                "Items": {"PackageReference": []},
            }

        paths = [Path("First.Tests.csproj"), Path("Second.Tests.csproj")]
        with (
            patch.object(
                run_tests,
                "first_party_files",
                side_effect=lambda root, *_: paths if root.name == "dev" else [],
            ),
            patch.object(run_tests, "evaluate_project", side_effect=fake_evaluate),
        ):
            projects = run_tests.find_dotnet_projects()
        self.assertEqual(
            [
                ("First.Tests.csproj", "net48", "First.Tests.net48", ["NET48"]),
                ("First.Tests.csproj", "net8.0", "First.Tests.net8.0", ["NET8.0"]),
                ("Second.Tests.csproj", "net48", "Second.Tests.net48", ["NET48"]),
                ("Second.Tests.csproj", "net8.0", "Second.Tests.net8.0", ["NET8.0"]),
            ],
            [
                (p["path"], p["framework"], p["assembly"], p["defines"])
                for p in projects
            ],
        )
        self.assertEqual(
            [[], [], ["IPY342"], ["IPY342"]], [p["engines"] for p in projects]
        )

    def test_csharp_selection_requires_a_built_product(self):
        """A fresh checkout fails fast with the build command, not with skipped cases."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "dotnet run -c Release -- ci"):
                run_tests.require_built_product(root)
            (root / "bin/netfx").mkdir(parents=True)
            (root / "bin/netcore/engines").mkdir(parents=True)
            run_tests.require_built_product(root)

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

    def test_annotated_classification_is_read(self):
        """Annotated module defaults classify a suite like plain assignments."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_annotated.py"
            path.write_text(
                'TEST_ENVIRONMENT: str = "HostFree"\nTEST_LEVEL: str = "Unit"\n',
                encoding="utf-8",
            )
            self.assertEqual(
                {"Environment": "HostFree", "Level": "Unit"},
                run_tests.python_metadata(path),
            )

    def test_invalid_classification_reports_the_found_value(self):
        """The error names the offending value, not only the expected field."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_invalid.py"
            path.write_text(
                'TEST_ENVIRONMENT = "Hostfree"\nTEST_LEVEL = "Unit"\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "found 'Hostfree'"):
                run_tests.python_metadata(path)

    def test_coverage_drop_fails_per_module(self):
        """A strong module cannot mask a second module's regression."""
        baseline = {"parser": {"line": 0.8, "branch": 0.6}}
        with self.assertRaisesRegex(ValueError, "parser"):
            run_tests.check_baselines(
                {"parser": {"line": 0.79, "branch": 0.7}}, baseline
            )

    def test_every_coverage_failure_is_reported_at_once(self):
        """One run lists all regressions instead of stopping at the first."""
        baseline = {
            "first": {"line": 0.8, "branch": 0.6},
            "second": {"line": 0.5, "branch": 0.5},
            "gone": {"line": 0.1, "branch": 0.1},
        }
        measured = {
            "first": {"line": 0.7, "branch": 0.6},
            "second": {"line": 0.5, "branch": 0.4},
        }
        with self.assertRaises(ValueError) as raised:
            run_tests.check_baselines(measured, baseline)
        message = str(raised.exception)
        for expected in ("first line", "second branch", "Missing coverage for gone"):
            self.assertIn(expected, message)

    def test_missing_module_coverage_fails(self):
        """Missing evidence cannot silently remove an established module."""
        with self.assertRaisesRegex(ValueError, "Missing coverage"):
            run_tests.check_baselines({}, {"parser": {"line": 0.8, "branch": 0.6}})

    def test_captured_output_excludes_stderr_warnings(self):
        """MSBuild warnings on stderr cannot corrupt the JSON read from stdout."""
        script = "import sys; print('{}'); print('warning', file=sys.stderr)"
        self.assertEqual(
            "{}\n", run_tests.command([sys.executable, "-c", script], capture=True)
        )
        with self.assertRaisesRegex(RuntimeError, "warning"):
            run_tests.command(
                [sys.executable, "-c", script + "; sys.exit(1)"], capture=True
            )

    def test_timeout_names_the_command(self):
        """A hung command fails with its arguments instead of a raw traceback."""
        with self.assertRaisesRegex(RuntimeError, "Timed out after 0.5s: .*sleep"):
            run_tests.command(
                [sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.5
            )

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

    def test_class_cannot_downgrade_a_revit_module(self):
        """A class default is held to the same guard as a method marker."""
        item = SimpleNamespace(
            module=SimpleNamespace(TEST_ENVIRONMENT="Revit", TEST_LEVEL="Integration"),
            cls=SimpleNamespace(TEST_ENVIRONMENT="HostFree"),
            nodeid="hosted",
            get_closest_marker=lambda name: None,
        )
        with self.assertRaises(pytest.UsageError):
            conftest.classification(item)

    def test_non_literal_classification_names_the_file(self):
        """A computed tag fails with the module path, not a bare AST message."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_computed.py"
            path.write_text(
                'TEST_ENVIRONMENT = "Host" + "Free"\nTEST_LEVEL = "Unit"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "test_computed.py.*literal"):
                run_tests.python_metadata(path)

    def test_project_evaluations_never_exceed_the_cpu_count(self):
        """Each evaluation is an MSBuild process, so the pool stays bounded."""
        lock = threading.Lock()
        running = peak = 0

        def fake_evaluate(path, framework=None):
            nonlocal running, peak
            with lock:
                running += 1
                peak = max(peak, running)
            time.sleep(0.05)
            with lock:
                running -= 1
            return {
                "Properties": {
                    "IsTestProject": "false",
                    "TargetFrameworks": "",
                    "TargetFramework": "",
                },
                "Items": {"PackageReference": []},
            }

        paths = [Path(f"Tests{index}.csproj") for index in range(8)]
        with (
            patch.object(run_tests.os, "cpu_count", return_value=2),
            patch.object(
                run_tests,
                "first_party_files",
                side_effect=lambda root, *_: paths if root.name == "dev" else [],
            ),
            patch.object(run_tests, "evaluate_project", side_effect=fake_evaluate),
            self.assertRaises(ValueError),
        ):
            run_tests.find_dotnet_projects()
        self.assertEqual(2, peak)

    def test_baseline_update_replaces_only_the_selected_language(self):
        """Renamed modules drop out; the other language's floors are untouched."""
        baseline = {
            "python/old.py": {"line": 0.5},
            "python/kept.py": {"line": 0.5},
            "dotnet/A/net48": {"line": 0.4},
            "dotnet-linked/B/net48": {"line": 0.3},
        }
        measured = {"python/kept.py": {"line": 0.61}, "python/new.py": {"line": 0.7}}
        self.assertEqual(
            {
                "python/kept.py": {"line": 0.61},
                "python/new.py": {"line": 0.7},
                "dotnet/A/net48": {"line": 0.4},
                "dotnet-linked/B/net48": {"line": 0.3},
            },
            run_tests.updated_baselines(baseline, measured, "python"),
        )
        self.assertEqual(
            {"python/kept.py": {"line": 0.61}},
            run_tests.updated_baselines(
                baseline, {"python/kept.py": {"line": 0.61}}, "all"
            ),
        )

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

    def test_excluded_coverage_files_are_shared_with_the_collector(self):
        """Files excluded from instrumentation are also excluded from aggregation."""
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory)
            path = results / "project/net8.0/run/coverage.json"
            path.parent.mkdir(parents=True)
            method = {"Example": {"Method": {"Lines": {"1": 1}, "Branches": []}}}
            path.write_text(
                json.dumps(
                    {
                        "Example.dll": {
                            str(run_tests.ROOT / relative): method
                            for relative in (
                                "dev/a/obj/Generated.cs",
                                "dev/a/tests/Fixture.cs",
                                "dev/a/Product.cs",
                            )
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                1, run_tests.collect_coverage(results)["dotnet/Example/net8.0"]["lines"]
            )

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

    def test_first_party_folders_named_like_dependencies_are_discovered(self):
        """Only the vendored repository paths are skipped, not any folder named modules."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "extensions/Tab/lib/modules/test_kept.py",
                "extensions/Tab/lib/bin/test_kept_bin.py",
                "dev/modules/vendor/test_vendored.py",
                "extensions/.venv/test_env.py",
                "dev/project/bin/test_built.py",
            ):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text("", encoding="utf-8")
            (root / "dev/project/project.csproj").write_text("", encoding="utf-8")
            found = {
                path.relative_to(root).as_posix()
                for path in run_tests.first_party_files(root, "test_*.py", root)
            }
            self.assertEqual(
                {
                    "extensions/Tab/lib/modules/test_kept.py",
                    "extensions/Tab/lib/bin/test_kept_bin.py",
                },
                found,
            )

    def test_python_inventory_lists_each_module_once(self):
        """A module matching both naming patterns is inventoried and run once."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "extensions").mkdir()
            (root / "dev").mkdir()
            (root / "pyrevitlib/pyrevit/unittests").mkdir(parents=True)
            metadata = 'TEST_ENVIRONMENT = "HostFree"\nTEST_LEVEL = "Unit"\n'
            for name in ("test_both_tests.py", "other_tests.py", "test_plain.py"):
                (root / "extensions" / name).write_text(metadata, encoding="utf-8")
            with patch.object(run_tests, "ROOT", root):
                paths = [
                    Path(suite["path"]).name for suite in run_tests.discover_python()
                ]
            self.assertEqual(
                ["other_tests.py", "test_both_tests.py", "test_plain.py"], sorted(paths)
            )

    def test_strict_skip_policy_applies_only_when_the_runner_requests_it(self):
        """Ad hoc pytest runs may skip; the shared runner must reject skips."""
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            (tmp_path / "conftest.py").write_text(
                Path(conftest.__file__).read_text(encoding="utf-8"), encoding="utf-8"
            )
            (tmp_path / "test_skips.py").write_text(
                "import pytest\nTEST_ENVIRONMENT = 'HostFree'\nTEST_LEVEL = 'Unit'\n"
                "@pytest.mark.skip\ndef test_skipped():\n    pass\n"
                "def test_ran():\n    assert True\n",
                encoding="utf-8",
            )
            environment = {
                key: value
                for key, value in os.environ.items()
                if key != run_tests.STRICT_SKIPS_ENV
            }
            environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            statuses = []
            for extra in ({}, {run_tests.STRICT_SKIPS_ENV: "1"}):
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q", "test_skips.py"],
                    cwd=tmp_path,
                    env={**environment, **extra},
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                statuses.append(result.returncode)
            self.assertEqual([0, 1], statuses)

    def test_locked_requirements_pin_every_hash_and_marker(self):
        """Dependency installation is hash-verified from the lock file."""
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "Pipfile.lock"
            lock.write_text(
                json.dumps(
                    {
                        "develop": {
                            "pytest": {
                                "version": "==9.0.2",
                                "hashes": ["sha256:aa", "sha256:bb"],
                                "markers": "python_version >= '3.10'",
                            },
                            "pluggy": {"version": "==1.7.0", "hashes": ["sha256:cc"]},
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                "pytest==9.0.2 ; python_version >= '3.10' --hash=sha256:aa --hash=sha256:bb\n"
                "pluggy==1.7.0 --hash=sha256:cc\n",
                run_tests.locked_requirements(lock),
            )

    def test_unpinned_lock_entry_names_the_package(self):
        """A lock entry without a version fails clearly instead of with a KeyError."""
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "Pipfile.lock"
            lock.write_text(
                json.dumps({"develop": {"tool": {"git": "https://example.invalid"}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "tool"):
                run_tests.locked_requirements(lock)


class GateTests(unittest.TestCase):
    """Pin the pass/fail control flow that main() delegates."""

    BASELINE = {
        "python/a.py": {"line": 0.5, "branch": 0.5},
        "dotnet/A/net48": {"line": 0.5, "branch": 0.5},
    }

    def test_language_filter_only_checks_the_selected_floors(self):
        """A Python-only run is not failed by the unmeasured C# modules."""
        measured = {"python/a.py": {"line": 0.5, "branch": 0.5}}
        self.assertIsNone(
            run_tests.gate_coverage(measured, self.BASELINE, "python", False)
        )
        with self.assertRaisesRegex(ValueError, "Missing coverage for dotnet/A"):
            run_tests.gate_coverage(measured, self.BASELINE, "all", False)

    def test_regression_fails_unless_updating(self):
        """Updating returns new floors without checking; checking rejects drops."""
        measured = {"python/a.py": {"line": 0.1, "branch": 0.5}}
        with self.assertRaisesRegex(ValueError, "python/a.py line"):
            run_tests.gate_coverage(measured, self.BASELINE, "python", False)
        self.assertEqual(
            {**self.BASELINE, **measured},
            run_tests.gate_coverage(measured, self.BASELINE, "python", True),
        )

    def test_new_module_needs_a_reviewed_baseline(self):
        """A measured module without a floor fails a normal run."""
        measured = {
            "python/a.py": {"line": 0.5, "branch": 0.5},
            "python/new.py": {"line": 1, "branch": 1},
        }
        with self.assertRaisesRegex(ValueError, "need reviewed baselines"):
            run_tests.gate_coverage(measured, self.BASELINE, "python", False)

    def _run_python(self, suites, tests):
        def fake_command(arguments, environment):
            self.assertEqual({run_tests.STRICT_SKIPS_ENV: "1"}, environment)
            calls.append(arguments)
            report = next(a for a in arguments if str(a).startswith("--junitxml="))
            Path(report.split("=", 1)[1]).write_text(
                f'<testsuites><testsuite tests="{tests}"/></testsuites>',
                encoding="utf-8",
            )

        calls = []
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(run_tests, "command", side_effect=fake_command),
        ):
            run_tests.run_python(suites, Path(directory) / "python")
        return calls

    def test_python_run_passes_only_host_free_suites(self):
        """Revit suites are inventoried but never handed to pytest."""
        calls = self._run_python(
            [
                {"path": "test_free.py", "Environment": "HostFree"},
                {"path": "test_hosted.py", "Environment": "Revit"},
            ],
            1,
        )
        self.assertIn("test_free.py", calls[0])
        self.assertNotIn("test_hosted.py", calls[0])

    def test_python_run_rejects_empty_selections(self):
        """No host-free suite, or zero selected tests, never passes."""
        with self.assertRaisesRegex(ValueError, "No host-free Python suites"):
            self._run_python([{"path": "t.py", "Environment": "Revit"}], 1)
        with self.assertRaisesRegex(ValueError, "zero tests"):
            self._run_python([{"path": "t.py", "Environment": "HostFree"}], 0)
