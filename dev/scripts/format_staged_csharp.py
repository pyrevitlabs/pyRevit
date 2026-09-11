"""Pre-commit hook: run ``dotnet format`` on staged C# files.

Groups the files passed on argv by the nearest ancestor solution (the four
first-party ones under dev/) and runs one ``dotnet format <sln> --include``
per group, so files are formatted against the project they actually belong
to. Files under dev/modules/ (vendored git submodules) are never passed in by
pre-commit's own path filtering, but are skipped defensively anyway.

Uses the default (whitespace + style) scope, not the ``analyzers`` command -
this is meant to be a formatter, the C# equivalent of ``ruff format``, not a
linter. ``--include`` only accepts paths relative to the solution/repo root,
not absolute ones.

Exits nonzero (after leaving the formatted files in the working tree) if any
file was changed, so the commit stops for review - the same pattern ruff's
own formatting hook uses.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# First-party solutions only. Vendored submodules under dev/modules/ (IronPython,
# dlr, NLog, Python.Net, MahApps.Metro, Newtonsoft.Json) are excluded on purpose.
SOLUTIONS = [
    REPO_ROOT / "dev" / "pyRevitLabs" / "pyRevitLabs.sln",
    REPO_ROOT / "dev" / "pyRevitLabs.PyRevit.Runtime" / "pyRevitLabs.PyRevit.Runtime.sln",
    REPO_ROOT / "dev" / "pyRevitLoader" / "pyRevitLoader.sln",
    REPO_ROOT / "dev" / "pyRevitWPFForms" / "pyRevitWPFForms.sln",
]


def _resolve_solution(file_path):
    """Return the first SOLUTIONS entry whose directory contains file_path."""
    for solution in SOLUTIONS:
        try:
            file_path.relative_to(solution.parent)
            return solution
        except ValueError:
            continue
    return None


def _is_vendored(file_path):
    parts = file_path.relative_to(REPO_ROOT).parts
    return len(parts) >= 2 and parts[0] == "dev" and parts[1] == "modules"


def main(argv):
    staged_files = [Path(arg).resolve() for arg in argv]
    by_solution = {}
    skipped = []

    for file_path in staged_files:
        if _is_vendored(file_path):
            continue
        solution = _resolve_solution(file_path)
        if solution is None:
            skipped.append(file_path)
            continue
        by_solution.setdefault(solution, []).append(file_path)

    if skipped:
        names = ", ".join(str(p.relative_to(REPO_ROOT)) for p in skipped)
        print(f"format_staged_csharp: no known solution for: {names} - skipped")

    if not by_solution:
        return 0

    changed = False
    for solution, files in by_solution.items():
        before = {f: f.read_bytes() for f in files}
        relative_files = [str(f.relative_to(REPO_ROOT)) for f in files]
        cmd = [
            "dotnet", "format", str(solution.relative_to(REPO_ROOT)),
            "--include", *relative_files,
        ]
        result = subprocess.run(cmd, cwd=REPO_ROOT)
        if result.returncode != 0:
            print(f"format_staged_csharp: 'dotnet format' failed for {solution.name}")
            return result.returncode

        for f in files:
            if f.read_bytes() != before[f]:
                changed = True
                print(f"formatted: {f.relative_to(REPO_ROOT)}")

    if changed:
        print("format_staged_csharp: files were reformatted - review and re-stage them.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
