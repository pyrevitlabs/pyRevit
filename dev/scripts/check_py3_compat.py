"""Static checker for Python-3 / engine-portability issues in first-party code.

Scans pyrevitlib and the shipped extensions for the Python-2-only idioms and
IronPython-only CLR APIs cataloged in IRONPYTHON_TO_PYTHON3_ANALYSIS.md
(sections 4.3-4.5 and 6.1). Run with any CPython 3:

    pipenv run check-py3 [paths ...]

Third-party extension authors can point it at their own code; it has no
pyRevit dependencies and needs only a stock Python 3:

    python check_py3_compat.py path/to/MyExtension.extension

Exit code is nonzero when findings exist, so it can gate CI once the known
residuals are fixed.

Checks:
    SYNTAX      file does not parse as Python 3 (print statements,
                ``except X, e``, etc.)
    SYNTAX-WARN parsing raises a SyntaxWarning (e.g. invalid escape
                sequences like '\\d' in non-raw strings — a hard error in
                future Pythons)
    PY2-ITER    .iteritems() / .iterkeys() / .itervalues()
    PY2-HASKEY  .has_key()
    PY2-NAME    xrange / basestring / unicode / unichr / long
    PY2-BOOL    class defines __nonzero__ without a __bool__ alias
    IPY-CLR     clr.AddReferenceToFileAndPath outside pyrevit.framework
    CLR-REF     clr.Reference out-param marshaling outside the sanctioned
                engine-dispatch wrappers
    SORT-KEY    sorted() over dict .items()/.values() without a key=
                (tuple comparison can fall through to unorderable values)

A use of a PY2-NAME builtin is not flagged when it is guarded by an engine
check the codebase already uses: an ``if`` test, an enclosing function's
decorator, or a module-level conditional that references PY2/PY3/IRONPY*,
or a try/except NameError fallback definition.
"""

import argparse
import ast
import sys
import tokenize
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCAN_ROOTS = [
    "pyrevitlib/pyrevit",
    "pyrevitlib/rjm",
    "pyrevitlib/rpws",
    "pyrevitlib/rsparam",
    "extensions",
]

# rpw is frozen as legacy-IronPython-only (analysis doc section 4.7) and is
# excluded from the Python-3-supported surface.
EXCLUDED_DIRS = [
    "pyrevitlib/rpw",
]

# Files allowed to use IronPython-only CLR loading:
# - framework.py is the designated shim site; its calls are engine-gated
# - the DevTools compile test exercises the IronPython engine by design
IPY_CLR_EXEMPT = [
    "pyrevitlib/pyrevit/framework.py",
    "extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel/"
    "Engine Tests.pulldown/Test IronPython Compile.pushbutton/script.py",
]

# Files hosting the sanctioned engine dispatch for clr.Reference out-param
# marshaling; everywhere else should call their wrappers
# (query.intersect_curves, create.load_family) instead
CLR_REF_EXEMPT = [
    "pyrevitlib/pyrevit/revit/db/create.py",
    "pyrevitlib/pyrevit/revit/db/query.py",
]

PY2_ONLY_ITER_METHODS = {"iteritems", "iterkeys", "itervalues"}
PY2_ONLY_ITERTOOLS = {"ifilter", "ifilterfalse", "imap", "izip", "izip_longest"}
PY2_ONLY_NAMES = {"xrange", "basestring", "unicode", "unichr", "long"} | (
    PY2_ONLY_ITERTOOLS
)
ENGINE_GUARD_NAMES = {"PY2", "PY3", "IRONPY", "IRONPY2", "IRONPY3"}


class Finding:
    def __init__(self, path, lineno, code, message):
        self.path = path
        self.lineno = lineno
        self.code = code
        self.message = message

    def __str__(self):
        try:
            shown = self.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            shown = self.path.as_posix()
        return "{}:{}: [{}] {}".format(shown, self.lineno, self.code, self.message)


def _names_in(node):
    """Yield every bare and attribute name referenced under a node."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            yield child.id
        elif isinstance(child, ast.Attribute):
            yield child.attr


def _is_engine_guarded(node, parents):
    """Return True if node sits under an engine-version guard.

    Recognized guards: an ``if`` whose test references an engine flag, a
    function whose decorators reference one (e.g. skipUnless(PY2, ...)), or
    a try/except NameError (the shim-definition pattern).
    """
    current = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.If):
            if ENGINE_GUARD_NAMES & set(_names_in(parent.test)):
                return True
        elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in parent.decorator_list:
                if ENGINE_GUARD_NAMES & set(_names_in(decorator)):
                    return True
        elif isinstance(parent, ast.Try):
            for handler in parent.handlers:
                if handler.type is not None and "NameError" in set(
                    _names_in(handler.type)
                ):
                    return True
        current = parent
    return False


def _locally_defined_names(tree):
    """Names assigned or def'd at module level (compat shims like unicode=str)."""
    defined = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, (ast.If, ast.Try)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Name):
                            defined.add(target.id)
    return defined


def _keyless_sorted_over_dict_view(node):
    if not (isinstance(node.func, ast.Name) and node.func.id == "sorted"):
        return False
    if any(kw.arg == "key" for kw in node.keywords):
        return False
    if not node.args:
        return False
    first = node.args[0]
    return (
        isinstance(first, ast.Call)
        and isinstance(first.func, ast.Attribute)
        and first.func.attr in ("items", "values")
    )


def check_file(path):
    findings = []
    try:
        with tokenize.open(path) as fp:
            source = fp.read()
    except (OSError, SyntaxError, UnicodeDecodeError) as err:
        findings.append(Finding(path, 0, "SYNTAX", "cannot read: {}".format(err)))
        return findings

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", SyntaxWarning)
            tree = ast.parse(source, filename=str(path))
        for warning in caught:
            if issubclass(warning.category, SyntaxWarning):
                findings.append(
                    Finding(
                        path,
                        warning.lineno,
                        "SYNTAX-WARN",
                        str(warning.message),
                    )
                )
    except SyntaxError as err:
        findings.append(
            Finding(
                path,
                err.lineno or 0,
                "SYNTAX",
                "does not parse as Python 3: {}".format(err.msg),
            )
        )
        return findings

    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    local_names = _locally_defined_names(tree)
    clr_exempt = any(
        path == REPO_ROOT.joinpath(*exempt.split("/")) for exempt in IPY_CLR_EXEMPT
    )
    clr_ref_exempt = any(
        path == REPO_ROOT.joinpath(*exempt.split("/")) for exempt in CLR_REF_EXEMPT
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr in PY2_ONLY_ITER_METHODS:
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PY2-ITER",
                        ".{}() does not exist in Python 3".format(node.attr),
                    )
                )
            elif (
                node.attr in PY2_ONLY_ITERTOOLS
                and "itertools" in set(_names_in(node.value))
            ):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PY2-ITER",
                        "itertools.{} does not exist in Python 3".format(node.attr),
                    )
                )
            elif node.attr == "has_key":
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PY2-HASKEY",
                        ".has_key() does not exist in Python 3 (use `in`)",
                    )
                )
            elif node.attr == "AddReferenceToFileAndPath" and not clr_exempt:
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "IPY-CLR",
                        "IronPython-only CLR API; route through the "
                        "pyrevit.framework shim",
                    )
                )
            elif (
                node.attr == "Reference"
                and "clr" in set(_names_in(node.value))
                and not clr_ref_exempt
            ):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "CLR-REF",
                        "IronPython-only out-param marshaling; use "
                        "query.intersect_curves / create.load_family or an "
                        "engine-dispatched wrapper",
                    )
                )

        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if (
                node.id in PY2_ONLY_NAMES
                and node.id not in local_names
                and not _is_engine_guarded(node, parents)
            ):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PY2-NAME",
                        "`{}` does not exist in Python 3".format(node.id),
                    )
                )

        elif isinstance(node, ast.ClassDef):
            method_names = {
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            assigned_names = {
                target.id
                for item in node.body
                if isinstance(item, ast.Assign)
                for target in item.targets
                if isinstance(target, ast.Name)
            }
            if "__nonzero__" in method_names and "__bool__" not in (
                method_names | assigned_names
            ):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PY2-BOOL",
                        "class {} defines __nonzero__ but no __bool__; "
                        "Python 3 ignores __nonzero__".format(node.name),
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            if node.module == "itertools" and not _is_engine_guarded(
                node, parents
            ):
                for alias in node.names:
                    if alias.name in PY2_ONLY_ITERTOOLS:
                        findings.append(
                            Finding(
                                path,
                                node.lineno,
                                "PY2-ITER",
                                "itertools.{} does not exist in "
                                "Python 3".format(alias.name),
                            )
                        )

        elif isinstance(node, ast.Call) and _keyless_sorted_over_dict_view(node):
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "SORT-KEY",
                    "sorted() over dict view without key=; tuple comparison "
                    "can fall through to unorderable values in Python 3",
                )
            )

    return findings


def iter_python_files(roots, resolve_against):
    excluded = [REPO_ROOT.joinpath(*d.split("/")) for d in EXCLUDED_DIRS]
    for root in roots:
        root_path = root if root.is_absolute() else resolve_against / root
        if root_path.is_file():
            candidates = [root_path]
        else:
            candidates = sorted(root_path.rglob("*.py"))
        for path in candidates:
            if any(exc in path.parents or exc == path for exc in excluded):
                continue
            yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="files or directories to scan, e.g. a third-party .extension "
        "folder (default: pyRevit's first-party trees)",
    )
    args = parser.parse_args()

    # Explicit paths resolve against the caller's working directory so the
    # checker works on any extension folder; the built-in defaults resolve
    # against this repository.
    if args.paths:
        roots = args.paths
        resolve_against = Path.cwd()
    else:
        roots = [Path(p) for p in DEFAULT_SCAN_ROOTS]
        resolve_against = REPO_ROOT

    all_findings = []
    file_count = 0
    for path in iter_python_files(roots, resolve_against):
        file_count += 1
        all_findings.extend(check_file(path))

    for finding in all_findings:
        print(finding)

    counts = {}
    for finding in all_findings:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    summary = ", ".join(
        "{}: {}".format(code, count) for code, count in sorted(counts.items())
    )
    print(
        "\nscanned {} files; {} finding(s){}".format(
            file_count,
            len(all_findings),
            " ({})".format(summary) if summary else "",
        )
    )
    return 1 if all_findings else 0


if __name__ == "__main__":
    sys.exit(main())
