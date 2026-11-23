"""Discover first-party suites and run API-free tests with reproducible reports.

Classification is inspected before Python imports or C# fixture execution. Revit
tests are inventoried for local execution and are never run by this entry point.
"""

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
LEVELS = {"Unit", "Integration", "E2E", "Performance"}
ENVIRONMENTS = {"HostFree", "Revit"}
VENDORED_NAMES = {".git", ".venv", "site-packages"}
VENDORED_PATHS = {"dev/modules"}
BUILD_OUTPUT_NAMES = {"bin", "obj"}
PROJECT_PATTERNS = ("*.csproj", "*.vbproj")
STRICT_SKIPS_ENV = "PYREVIT_STRICT_SKIPS"
BASELINES = ROOT / "dev/tests/coverage-baselines.json"
COVERAGE_TOLERANCE = 0.000001
TRX_NS = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
COVERAGE_EXCLUDED_FILES = (
    "**/dev/modules/**",
    "**/obj/**",
    "**/tests/**",
)
IRONPYTHON_ENGINES = {"IPY2712PR", "IPY342"}


def python_metadata(path):
    """Read literal module defaults without importing test dependencies."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value:
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in {
                "TEST_ENVIRONMENT",
                "TEST_LEVEL",
            }:
                try:
                    values[target.id] = ast.literal_eval(node.value)
                except ValueError as error:
                    raise ValueError(
                        f"{path}: {target.id} must be a literal value"
                    ) from error
    for name, allowed in (("TEST_ENVIRONMENT", ENVIRONMENTS), ("TEST_LEVEL", LEVELS)):
        if values.get(name) not in allowed:
            raise ValueError(
                f"{path}: {name} must be one of {sorted(allowed)}, found {values.get(name)!r}"
            )
    return {"Environment": values["TEST_ENVIRONMENT"], "Level": values["TEST_LEVEL"]}


def is_third_party(directory, name, repository):
    """Tell vendored or generated folders from first-party folders named alike.

    Only ``VENDORED_NAMES``, the ``VENDORED_PATHS`` below the repository root,
    and ``bin``/``obj`` beside a project file are skipped; any other folder,
    for example ``lib/modules``, is first-party and must be discovered.
    """
    path = Path(directory) / name
    if name in VENDORED_NAMES:
        return True
    if (
        path.is_relative_to(repository)
        and path.relative_to(repository).as_posix() in VENDORED_PATHS
    ):
        return True
    return name in BUILD_OUTPUT_NAMES and any(
        next(Path(directory).glob(pattern), None) for pattern in PROJECT_PATTERNS
    )


def first_party_files(root, pattern, repository):
    """Walk source trees without descending into dependencies or build outputs.

    ``root`` is the tree to walk; ``repository`` anchors ``VENDORED_PATHS``.
    """
    for directory, children, files in os.walk(root):
        children[:] = sorted(
            child
            for child in children
            if not is_third_party(directory, child, repository)
        )
        for name in sorted(files):
            if Path(name).match(pattern):
                yield Path(directory) / name


def command(arguments, capture=False, timeout=1200, environment=None):
    """Propagate subprocess failures and bound potentially hanging test runs.

    With ``capture`` only stdout is returned; stderr is kept apart so tool
    warnings cannot corrupt parsed output, and is reported on failure.
    """
    try:
        result = subprocess.run(
            [str(argument) for argument in arguments],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            capture_output=capture,
            env={**os.environ, "DOTNET_CLI_UI_LANGUAGE": "en", **(environment or {})},
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Timed out after {timeout}s: {arguments}") from error
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {arguments}\n"
            f"{result.stdout or ''}{result.stderr or ''}"
        )
    return result.stdout


def evaluate_project(path, framework=None):
    """Evaluate MSBuild properties and compiled sources, including imports."""
    arguments = [
        "dotnet",
        "msbuild",
        path,
        "-getProperty:IsTestProject,TargetFramework,TargetFrameworks,AssemblyName,DefineConstants,PyRevitTestEngines",
        "-getItem:Compile,PackageReference",
        "-p:Configuration=Release",
        "-m:1",
        "-nr:false",
    ]
    if framework:
        arguments.append(f"-p:TargetFramework={framework}")
        arguments.append("-target:AddImplicitDefineConstants")
    return json.loads(command(arguments, capture=True))


def find_dotnet_projects():
    """List each evaluated ``IsTestProject`` project once per target framework.

    Note:
        Implicit framework defines come from a target that exists only in a
        framework's inner build, so each test framework needs its own
        evaluation. Evaluations are independent and run concurrently.

    Raises:
        ValueError: A project references the test SDK without
            ``IsTestProject=true``, declares an unknown engine, or none is
            found.
    """
    paths = [
        path
        for root in (ROOT / "dev", ROOT / "build")
        for path in first_party_files(root, "*.csproj", ROOT)
    ]
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as pool:
        targets = []
        for path, data in zip(paths, pool.map(evaluate_project, paths)):
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
            targets.extend((path, framework) for framework in frameworks.split(";"))
        evaluations = list(pool.map(lambda target: evaluate_project(*target), targets))
    projects = [
        {
            "path": str(path),
            "framework": framework,
            "assembly": evaluated["Properties"]["AssemblyName"],
            "sources": [item["FullPath"] for item in evaluated["Items"]["Compile"]],
            "defines": [
                value
                for value in evaluated["Properties"]["DefineConstants"].split(";")
                if value
            ],
            "engines": declared_engines(
                path, evaluated["Properties"]["PyRevitTestEngines"]
            ),
        }
        for (path, framework), evaluated in zip(targets, evaluations)
    ]
    if not projects:
        raise ValueError("No first-party .NET test projects discovered")
    return projects


def classify_dotnet(projects, results):
    """Attach each project's tests, classified from source by the build catalog.

    The C# classification rules live in ``build/Helpers/TestMetadata.cs``.

    Raises:
        ValueError: A project and framework has no classified test.
    """
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
            "run",
            "--project",
            ROOT / "build/Build.csproj",
            "-c",
            "Release",
            "--",
            "test-catalog",
            source_list,
            catalog_path,
        ],
        environment={"MSBUILDDISABLENODEREUSE": "1"},
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
    """Inventory named Python tests without importing hosted suites.

    Note:
        ``*_tests.py`` is the extensions' in-Revit suite convention and is only
        searched there: under ``dev/`` it would match this runner. Name every
        other suite ``test_*.py``.
    """
    roots = (ROOT / "dev", ROOT / "pyrevitlib/pyrevit/unittests", ROOT / "extensions")
    paths = {
        path for root in roots for path in first_party_files(root, "test_*.py", ROOT)
    } | set(first_party_files(ROOT / "extensions", "*_tests.py", ROOT))
    return [{"path": str(path), **python_metadata(path)} for path in sorted(paths)]


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


def locked_requirements(lock):
    """Render the lock file's develop section as hash-pinned pip requirements."""
    packages = json.loads(Path(lock).read_text(encoding="utf-8"))["develop"]
    lines = []
    for name, package in packages.items():
        if "version" not in package:
            raise ValueError(f"Pipfile.lock develop entry {name} has no pinned version")
        marker = f" ; {package['markers']}" if package.get("markers") else ""
        hashes = "".join(f" --hash={value}" for value in package["hashes"])
        lines.append(f"{name}{package['version']}{marker}{hashes}\n")
    return "".join(lines)


def declared_engines(project, value):
    """Parse a project's ``PyRevitTestEngines`` MSBuild property.

    ``IRONPYTHON_ENGINES`` mirrors the engine configurations in
    ``dev/pyRevitLabs.PyRevit.Runtime/Directory.Build.targets``.

    Raises:
        ValueError: A declared engine is not an IronPython engine, so a typo
            cannot silently drop or rename an engine run.
    """
    engines = [engine for engine in value.split(";") if engine]
    unknown = sorted(set(engines) - IRONPYTHON_ENGINES)
    if unknown:
        raise ValueError(
            f"{project}: PyRevitTestEngines names unknown engines {unknown};"
            f" allowed engines are {sorted(IRONPYTHON_ENGINES)}"
        )
    return engines


def engine_variants(project):
    """IronPython engines a suite must pass on; ``None`` means the project default."""
    return project["engines"] or [None]


def require_built_product(root=ROOT):
    """Fail fast when the C# suites have no built product to test.

    Renderer layout, shell engine and runtime suites read the deployed ``bin``
    tree, so running them against a fresh checkout would only end in
    inconclusive cases, which the runner rejects.
    """
    missing = [
        path
        for path in (root / "bin/netfx", root / "bin/netcore/engines")
        if not path.is_dir()
    ]
    if missing:
        raise ValueError(
            "C# suites test the built product, which is missing ("
            + ", ".join(str(path) for path in missing)
            + "); build it first: cd build && dotnet run -c Release -- ci"
        )


def run_dotnet(project, results, engine=None):
    """Run all eligible classes through their native framework adapters.

    Each engine variant reports to its own directory so one run cannot
    overwrite another's evidence; their coverage merges into one module.

    Invariant:
        The run executes at least the host-free methods the source catalog
        classified, so drift between catalog parsing and the runtime trait
        filter fails instead of dropping tests. Test cases only add to it.
    """
    cataloged = sum(test["Environment"] == "HostFree" for test in project["tests"])
    if not cataloged:
        return None
    suite = Path(project["path"]).stem
    directory = (
        results / (f"{suite}.{engine}" if engine else suite) / project["framework"]
    )
    directory.mkdir(parents=True, exist_ok=True)
    settings = directory / "coverage.runsettings"
    settings.write_text(
        "<RunSettings><RunConfiguration><TestSessionTimeout>600000</TestSessionTimeout>"
        "</RunConfiguration><DataCollectionRunSettings><DataCollectors>"
        '<DataCollector friendlyName="XPlat Code Coverage"><Configuration>'
        "<Format>cobertura,json</Format><Include>[pyRevit*]*,[Build*]*</Include>"
        f"<ExcludeByFile>{','.join(COVERAGE_EXCLUDED_FILES)}</ExcludeByFile>"
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
            "-p:DebugSymbols=true",
            "-p:DebugType=portable",
            "-m:1",
            "-nr:false",
            *([f"-p:IronPythonVersion={engine}"] if engine else []),
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
    if int(counters["executed"]) < cataloged:
        raise ValueError(
            f"{suite} {project['framework']}: executed {counters['executed']} tests,"
            f" fewer than the {cataloged} host-free tests in the catalog"
        )
    for report in ("coverage.cobertura.xml", "coverage.json"):
        if not list(directory.glob(f"*/{report}")):
            raise ValueError(f"Missing {report} coverage report: {directory}")
    return {
        "project": project["path"],
        "framework": project["framework"],
        **({"engine": engine} if engine else {}),
        **counters,
    }


def check_baselines(measured, baseline):
    """Enforce separate line and branch floors for each measured module.

    Every failing module and kind is reported in one error.
    """
    failures = []
    for module, expected in baseline.items():
        if module not in measured:
            failures.append(f"Missing coverage for {module}")
            continue
        for kind in ("line", "branch"):
            if measured[module][kind] + COVERAGE_TOLERANCE < expected[kind]:
                failures.append(
                    f"Coverage decreased: {module} {kind}: {measured[module][kind]} < {expected[kind]}"
                )
    if failures:
        raise ValueError("\n".join(failures))


def product_documents(documents):
    """Yield ``(identity, classes)`` for each first-party, non-excluded source.

    The identity is the case-normalized path, so differently cased references
    to one Windows file share a denominator.
    """
    for filename, classes in documents.items():
        source = Path(filename)
        if not source.is_relative_to(ROOT):
            continue
        relative = PurePosixPath(source.relative_to(ROOT).as_posix())
        if not any(map(relative.full_match, COVERAGE_EXCLUDED_FILES)):
            yield os.path.normcase(str(source)), classes


def _source_line(lines, document, number):
    return lines.setdefault((document, str(number)), {"hit": False, "branches": {}})


def merge_document(lines, document, classes):
    """Merge one source's line hits and branch outcomes into a module's lines.

    Invariant:
        A branch is identified by its method, offsets and path, so a branch
        reported by several suites counts once and is hit if any suite hit it.
    """
    for methods in classes.values():
        for method, details in methods.items():
            for number, hits in details["Lines"].items():
                _source_line(lines, document, number)["hit"] |= hits > 0
            for branch in details["Branches"]:
                outcomes = _source_line(lines, document, branch["Line"])["branches"]
                identity = (
                    method,
                    branch["Offset"],
                    branch["EndOffset"],
                    branch["Path"],
                )
                outcomes[identity] = outcomes.get(identity, False) or branch["Hits"] > 0


def merge_dotnet_report(modules, path):
    """Merge one run's ``coverage.json`` into the per-module line maps."""
    framework = path.parent.parent.name
    for assembly, documents in json.loads(path.read_text(encoding="utf-8")).items():
        name = Path(assembly).stem
        kind = "dotnet-linked" if name.endswith(".Tests") else "dotnet"
        module = f"{kind}/{name}/{framework}"
        for document, classes in product_documents(documents):
            merge_document(modules.setdefault(module, {}), document, classes)


def dotnet_ratios(lines):
    """Summarize a module's merged lines; a module without branches scores 1."""
    branches = sum(len(value["branches"]) for value in lines.values())
    return {
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


def python_coverage(report):
    """Read coverage.py's JSON report as one measured module per source file."""
    measured = {}
    for filename, data in json.loads(report.read_text())["files"].items():
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


def collect_coverage(results):
    """Merge executed lines and branches across suites per module/framework."""
    modules = {}
    for path in results.glob("*/*/*/coverage.json"):
        merge_dotnet_report(modules, path)
    measured = {module: dotnet_ratios(lines) for module, lines in modules.items()}
    python_report = results / "python/coverage.json"
    if python_report.exists():
        measured.update(python_coverage(python_report))
    return measured


def updated_baselines(baseline, measured, language):
    """Replace the selected language's floors with this run's exact measurements.

    Modules of that language missing from the run are dropped, so removing or
    renaming a module needs no manual edit; other languages are kept as is.
    """
    kept = {
        module: floors
        for module, floors in baseline.items()
        if language != "all" and not module.startswith(language)
    }
    return {**kept, **measured}


def run_python(suites, directory):
    """Run the inventoried host-free Python suites with strict skips and coverage.

    Raises:
        ValueError: No host-free suite is inventoried or pytest selected zero
            tests, so an empty selection never passes.
    """
    files = [suite["path"] for suite in suites if suite["Environment"] == "HostFree"]
    if not files:
        raise ValueError("No host-free Python suites discovered")
    directory.mkdir(parents=True, exist_ok=True)
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
        ],
        environment={STRICT_SKIPS_ENV: "1"},
    )
    root = ET.parse(directory / "results.xml").getroot()
    if sum(int(suite.get("tests", "0")) for suite in root.iter("testsuite")) == 0:
        raise ValueError("Python run selected zero tests")


def report_coverage(results, measured, language):
    """Write the run's coverage summary and, in CI, the job step summary."""
    (results / "coverage-summary.json").write_text(
        json.dumps(measured, indent=2, sort_keys=True), encoding="utf-8"
    )
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as report:
            report.write(
                f"\n### {language} test coverage\n\n| Module | Lines | Branches |\n|---|---:|---:|\n"
            )
            for module, values in sorted(measured.items(), key=lambda item: item[0]):
                report.write(
                    f"| {module} | {values['line']:.1%} | {values['branch']:.1%} |\n"
                )


def gate_coverage(measured, baseline, language, update):
    """Enforce the selected language's floors, or return replacement floors.

    Returns:
        With ``update``, the baselines to write, unchecked; otherwise ``None``.

    Raises:
        ValueError: A floor of the selected language regressed or lost its
            module, or any measured module has no reviewed baseline.
    """
    if update:
        return updated_baselines(baseline, measured, language)
    check_baselines(
        measured,
        {
            module: floors
            for module, floors in baseline.items()
            if language == "all" or module.startswith(language)
        },
    )
    if set(measured) - set(baseline):
        raise ValueError(
            "New coverage modules need reviewed baselines: run --update-baselines"
        )
    return None


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
        with tempfile.TemporaryDirectory() as directory:
            requirements = Path(directory) / "requirements.txt"
            requirements.write_text(
                locked_requirements(ROOT / "Pipfile.lock"), encoding="utf-8"
            )
            command(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--require-hashes",
                    "-r",
                    requirements,
                ]
            )
        return
    results = options.results.resolve() / uuid.uuid4().hex
    results.mkdir(parents=True, exist_ok=True)
    inventory = {"python": discover_python(), "dotnet": []}
    if options.language != "python":
        inventory["dotnet"] = classify_dotnet(find_dotnet_projects(), results)
    (results / "inventory.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )
    if options.list:
        print(json.dumps(inventory, indent=2))
        return
    if options.language != "python":
        require_built_product()
    if options.language != "dotnet":
        run_python(inventory["python"], results / "python")
    summary = []
    for project in inventory["dotnet"]:
        for engine in engine_variants(project):
            outcome = run_dotnet(project, results, engine)
            if outcome:
                summary.append(outcome)
    (results / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    measured = collect_coverage(results)
    baseline = json.loads(BASELINES.read_text()) if BASELINES.exists() else {}
    report_coverage(results, measured, options.language)
    updated = gate_coverage(
        measured, baseline, options.language, options.update_baselines
    )
    if updated is not None:
        BASELINES.parent.mkdir(parents=True, exist_ok=True)
        BASELINES.write_text(
            json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
