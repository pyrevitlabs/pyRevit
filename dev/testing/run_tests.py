"""Discover first-party suites and run API-free tests with reproducible reports.

Classification is inspected before Python imports or C# fixture execution. Revit
tests are inventoried for local execution and are never run by this entry point.
"""

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
LEVELS = {"Unit", "Integration", "E2E", "Performance"}
ENVIRONMENTS = {"HostFree", "Revit"}
EXCLUDED = {"modules", "bin", "obj", ".git", ".venv", "site-packages"}
BASELINES = ROOT / "dev/testing/coverage-baselines.json"
TRX_NS = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}


def python_metadata(path):
    """Read literal module defaults without importing test dependencies."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "TEST_ENVIRONMENT",
                    "TEST_LEVEL",
                }:
                    values[target.id] = ast.literal_eval(node.value)
    for name, allowed in (("TEST_ENVIRONMENT", ENVIRONMENTS), ("TEST_LEVEL", LEVELS)):
        if values.get(name) not in allowed:
            raise ValueError(f"{path}: valid {name} is required")
    return {"Environment": values["TEST_ENVIRONMENT"], "Level": values["TEST_LEVEL"]}


def first_party_files(root, pattern):
    """Walk source trees without descending into dependencies or build outputs."""
    for directory, children, files in os.walk(root):
        children[:] = sorted(child for child in children if child not in EXCLUDED)
        for name in sorted(files):
            if Path(name).match(pattern):
                yield Path(directory) / name


def command(arguments, capture=False, timeout=1200):
    """Propagate subprocess failures and bound potentially hanging test runs."""
    result = subprocess.run(
        [str(argument) for argument in arguments],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        env={**os.environ, "DOTNET_CLI_UI_LANGUAGE": "en"},
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {arguments}\n{result.stdout or ''}"
        )
    return result.stdout


def evaluate_project(path, framework=None):
    """Evaluate MSBuild properties and compiled sources, including imports."""
    arguments = [
        "dotnet",
        "msbuild",
        path,
        "-getProperty:IsTestProject,TargetFramework,TargetFrameworks,AssemblyName,DefineConstants",
        "-getItem:Compile,PackageReference",
        "-p:Configuration=Release",
        "-m:1",
        "-nr:false",
    ]
    if framework:
        arguments.append(f"-p:TargetFramework={framework}")
        arguments.append("-target:AddImplicitDefineConstants")
    return json.loads(command(arguments, capture=True))


def discover_dotnet(results):
    """Discover adjacent test projects by evaluated IsTestProject metadata."""
    projects = []
    for root in (ROOT / "dev", ROOT / "build"):
        for path in first_party_files(root, "*.csproj"):
            data = evaluate_project(path)
            properties = data["Properties"]
            if properties["IsTestProject"].lower() != "true":
                if any(
                    item["Identity"] == "Microsoft.NET.Test.Sdk"
                    for item in data["Items"]["PackageReference"]
                ):
                    raise ValueError(
                        f"{path}: test SDK requires IsTestProject=true for discovery"
                    )
                continue
            frameworks = properties["TargetFrameworks"] or properties["TargetFramework"]
            for framework in frameworks.split(";"):
                evaluated = evaluate_project(path, framework)
                compiled = [item["FullPath"] for item in evaluated["Items"]["Compile"]]
                projects.append(
                    {
                        "path": str(path),
                        "framework": framework,
                        "assembly": evaluated["Properties"]["AssemblyName"],
                        "sources": compiled,
                        "defines": [
                            value
                            for value in evaluated["Properties"][
                                "DefineConstants"
                            ].split(";")
                            if value
                        ],
                    }
                )
    if not projects:
        raise ValueError("No first-party .NET test projects discovered")
    source_list = results / "sources.json"
    catalog_path = results / "dotnet-catalog.json"
    source_list.write_text(
        json.dumps(
            [
                {
                    "Project": project["path"],
                    "Framework": project["framework"],
                    "Sources": project["sources"],
                    "Defines": project["defines"],
                }
                for project in projects
            ]
        ),
        encoding="utf-8",
    )
    command(
        [
            "dotnet",
            "build",
            ROOT / "build/Build.csproj",
            "-c",
            "Release",
            "--nologo",
            "-m:1",
            "-nr:false",
        ]
    )
    command(
        [
            "dotnet",
            ROOT / "build/bin/Release/net10.0/pyRevit.Build.dll",
            "test-catalog",
            source_list,
            catalog_path,
        ]
    )
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for project in projects:
        project["tests"] = next(
            suite["Tests"]
            for suite in catalog
            if suite["Project"] == project["path"]
            and suite["Framework"] == project["framework"]
        )
        if not project["tests"]:
            raise ValueError(f"No classified tests: {project['path']}")
    return projects


def discover_python():
    """Inventory named Python tests without importing hosted suites."""
    roots = (ROOT / "dev", ROOT / "pyrevitlib/pyrevit/unittests", ROOT / "extensions")
    return [
        {"path": str(path), **python_metadata(path)}
        for root in roots
        for path in first_party_files(root, "test_*.py")
    ] + [
        {"path": str(path), **python_metadata(path)}
        for path in first_party_files(ROOT / "extensions", "*_tests.py")
    ]


def validate_trx(path):
    """Reject absent, empty, or failed runner evidence."""
    root = ET.parse(path).getroot()
    counters = root.find(".//t:Counters", TRX_NS)
    if counters is None or int(counters.get("executed", "0")) == 0:
        raise ValueError(f"{path}: zero executed tests")
    if int(counters.get("failed", "0")) or root.findall(
        ".//t:RunInfo[@outcome='Error']", TRX_NS
    ):
        raise ValueError(f"{path}: test run failed")
    if int(counters.get("notExecuted", "0")):
        raise ValueError(f"{path}: required host-free tests were skipped")
    if any(
        result.get("outcome") != "Passed"
        for result in root.findall(".//t:UnitTestResult", TRX_NS)
    ):
        raise ValueError(
            f"{path}: a selected test did not pass (including skipped cases)"
        )
    return dict(counters.attrib)


def run_dotnet(project, results):
    """Run all eligible classes through their native framework adapters."""
    if not any(test["Environment"] == "HostFree" for test in project["tests"]):
        return None
    directory = results / Path(project["path"]).stem / project["framework"]
    directory.mkdir(parents=True, exist_ok=True)
    settings = directory / "coverage.runsettings"
    settings.write_text(
        "<RunSettings><RunConfiguration><TestSessionTimeout>600000</TestSessionTimeout>"
        "</RunConfiguration><DataCollectionRunSettings><DataCollectors>"
        '<DataCollector friendlyName="XPlat Code Coverage"><Configuration>'
        "<Format>cobertura,json</Format><Include>[pyRevit*]*,[Build*]*</Include>"
        "<ExcludeByFile>**/dev/modules/**,**/obj/**,**/tests/**,**/pyRevitLabs.UnitTests/**</ExcludeByFile>"
        "<IncludeTestAssembly>true</IncludeTestAssembly>"
        "</Configuration></DataCollector></DataCollectors>"
        "</DataCollectionRunSettings></RunSettings>",
        encoding="utf-8",
    )
    command(
        [
            "dotnet",
            "test",
            project["path"],
            "-c",
            "Release",
            "-f",
            project["framework"],
            "-p:SkipPyRevitDeploy=true",
            "-p:PermitDeploy=true",
            "-p:DebugSymbols=true",
            "-p:DebugType=portable",
            "-m:1",
            "-nr:false",
            "--filter",
            "(Environment=HostFree|TestCategory=HostFree)&Environment!=Revit&TestCategory!=Revit",
            "--logger",
            "trx;LogFileName=results.trx",
            "--results-directory",
            directory,
            "--collect",
            "XPlat Code Coverage",
            "--settings",
            settings,
            "--blame-hang-timeout",
            "5m",
        ]
    )
    counters = validate_trx(directory / "results.trx")
    reports = list(directory.glob("*/coverage.cobertura.xml"))
    if not reports:
        raise ValueError(f"Missing coverage report: {directory}")
    return {"project": project["path"], "framework": project["framework"], **counters}


def check_baselines(measured, baseline):
    """Enforce separate line and branch floors for each measured module."""
    for module, expected in baseline.items():
        if module not in measured:
            raise ValueError(f"Missing coverage for {module}")
        for kind in ("line", "branch"):
            if measured[module][kind] + 0.000001 < expected[kind]:
                raise ValueError(
                    f"Coverage decreased: {module} {kind}: {measured[module][kind]} < {expected[kind]}"
                )


def collect_coverage(results):
    """Merge executed lines and branches across suites per module/framework."""
    modules = {}
    for path in results.glob("*/*/*/coverage.json"):
        framework = path.parent.parent.name
        for assembly, documents in json.loads(path.read_text(encoding="utf-8")).items():
            name = Path(assembly).stem
            kind = "dotnet-linked" if name.endswith(".Tests") else "dotnet"
            module = f"{kind}/{name}/{framework}"
            for filename, classes in documents.items():
                source = Path(filename)
                if not source.is_relative_to(ROOT):
                    continue
                relative = source.relative_to(ROOT).as_posix()
                if (
                    relative.startswith("dev/modules/")
                    or "/tests/" in relative
                    or "/pyRevitLabs.UnitTests/" in relative
                ):
                    continue
                lines = modules.setdefault(module, {})
                document = os.path.normcase(str(source))
                for methods in classes.values():
                    for method, details in methods.items():
                        for number, hits in details["Lines"].items():
                            key = (document, str(number))
                            previous = lines.setdefault(
                                key, {"hit": False, "branches": {}}
                            )
                            previous["hit"] |= hits > 0
                        for branch in details["Branches"]:
                            key = (document, str(branch["Line"]))
                            previous = lines.setdefault(
                                key, {"hit": False, "branches": {}}
                            )
                            identity = (
                                method,
                                branch["Offset"],
                                branch["EndOffset"],
                                branch["Path"],
                            )
                            previous["branches"][identity] = (
                                previous["branches"].get(identity, False)
                                or branch["Hits"] > 0
                            )
    measured = {}
    for module, lines in modules.items():
        branches = sum(len(value["branches"]) for value in lines.values())
        measured[module] = {
            "line": sum(value["hit"] for value in lines.values()) / len(lines)
            if lines
            else 0,
            "branch": sum(sum(value["branches"].values()) for value in lines.values())
            / branches
            if branches
            else 1,
            "lines": len(lines),
            "branches": branches,
        }
    python_report = results / "python/coverage.json"
    if python_report.exists():
        for filename, data in json.loads(python_report.read_text())["files"].items():
            summary = data["summary"]
            measured[f"python/{filename.replace(chr(92), '/')}"] = {
                "line": summary["covered_lines"] / summary["num_statements"]
                if summary["num_statements"]
                else 1,
                "branch": summary["covered_branches"] / summary["num_branches"]
                if summary["num_branches"]
                else 1,
                "lines": summary["num_statements"],
                "branches": summary["num_branches"],
            }
    return measured


def main():
    """Run the same selection locally and in CI; list local Revit suites only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language", choices=("all", "python", "dotnet"), default="all"
    )
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--install-dependencies", action="store_true")
    parser.add_argument("--update-baselines", action="store_true")
    parser.add_argument("--results", type=Path, default=ROOT / ".test-results")
    options = parser.parse_args()
    if options.install_dependencies:
        locked = json.loads((ROOT / "Pipfile.lock").read_text(encoding="utf-8"))[
            "develop"
        ]
        command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                *[
                    name + locked[name]["version"]
                    for name in ("pytest", "pytest-cov", "coverage")
                ],
            ]
        )
        return
    results = options.results.resolve() / uuid.uuid4().hex
    results.mkdir(parents=True, exist_ok=True)
    inventory = {"python": discover_python(), "dotnet": []}
    if options.language != "python":
        inventory["dotnet"] = discover_dotnet(results)
    (results / "inventory.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )
    if options.list:
        print(json.dumps(inventory, indent=2))
        return
    if options.language != "dotnet":
        directory = results / "python"
        directory.mkdir(exist_ok=True)
        files = [
            suite["path"]
            for suite in inventory["python"]
            if suite["Environment"] == "HostFree"
        ]
        if not files:
            raise ValueError("No host-free Python suites discovered")
        command(
            [
                sys.executable,
                "-m",
                "pytest",
                *files,
                "--strict-markers",
                "-o",
                f"cache_dir={directory / 'cache'}",
                f"--junitxml={directory / 'results.xml'}",
                "--cov",
                "--cov-branch",
                f"--cov-report=json:{directory / 'coverage.json'}",
                f"--cov-report=xml:{directory / 'coverage.xml'}",
                "--cov-report=term",
            ]
        )
        root = ET.parse(directory / "results.xml").getroot()
        if sum(int(suite.get("tests", "0")) for suite in root.iter("testsuite")) == 0:
            raise ValueError("Python run selected zero tests")
    summary = []
    for project in inventory["dotnet"]:
        outcome = run_dotnet(project, results)
        if outcome:
            summary.append(outcome)
    (results / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    measured = collect_coverage(results)
    baseline = json.loads(BASELINES.read_text()) if BASELINES.exists() else {}
    selected = {
        key: value
        for key, value in baseline.items()
        if options.language == "all" or key.startswith(options.language)
    }
    (results / "coverage-summary.json").write_text(
        json.dumps(measured, indent=2, sort_keys=True), encoding="utf-8"
    )
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as report:
            report.write(
                f"\n### {options.language} test coverage\n\n| Module | Lines | Branches |\n|---|---:|---:|\n"
            )
            for module, values in sorted(measured.items()):
                report.write(
                    f"| {module} | {values['line']:.1%} | {values['branch']:.1%} |\n"
                )
    if not options.update_baselines:
        check_baselines(measured, selected)
    if options.update_baselines:
        baseline.update(measured)
        BASELINES.parent.mkdir(parents=True, exist_ok=True)
        BASELINES.write_text(
            json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    elif set(measured) - set(baseline):
        raise ValueError(
            "New coverage modules need reviewed baselines: run --update-baselines"
        )


if __name__ == "__main__":
    main()
