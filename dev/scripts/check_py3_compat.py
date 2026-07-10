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
    PY2-NAME    xrange / basestring / unicode / unichr / long / StandardError
    PY2-BUILTIN a removed builtin called: raw_input / execfile / apply / cmp /
                coerce / intern / buffer / reduce / reload / file (skipped
                when the name is imported, e.g. functools.reduce)
    PY2-MODULE  import of a stdlib module renamed/removed in Python 3
                (StringIO, Queue, cPickle, ConfigParser, urllib2, ...)
    PY2-NEXT    iterator class defines next() (with __iter__) but no __next__
    PY2-BOOL    class defines __nonzero__ without a __bool__ alias
    IPY-CLR     clr.AddReferenceToFileAndPath outside pyrevit.framework
    CLR-REF     clr.Reference out-param marshaling outside the sanctioned
                engine-dispatch wrappers
    SORT-KEY    sorted() over dict .items()/.values() without a key=
                (tuple comparison can fall through to unorderable values)
    PY3-VIEW    a bare dict view (keys/values/items) or map/filter/zip that
                escapes local scope - indexed, returned, yielded, or stored
                to an attribute; these are non-indexable lazy views in
                Python 3 but were lists in Python 2 (wrap in list())

A finding is not flagged when it is guarded by a compat pattern the codebase
already uses: an ``if`` test, an enclosing function's decorator, or a
module-level conditional that references PY2/PY3/IRONPY*, or a try/except
NameError/ImportError fallback (the name-shim and import-fallback patterns).
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

# Excluded from the Python-3-supported surface:
# - rpw: frozen legacy, IronPython-WPF-locked (analysis doc section 4.7)
# - coreutils/markdown: vendored python-markdown with no first-party runtime
#   consumers (output.print_md renders via C#); a deprecated, unbundling
#   candidate that scripts should replace with pip `markdown`, so it is not
#   maintained against this checker
EXCLUDED_DIRS = [
    "pyrevitlib/rpw",
    "pyrevitlib/pyrevit/coreutils/markdown",
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
PY2_ONLY_NAMES = {
    "xrange", "basestring", "unicode", "unichr", "long", "StandardError",
} | PY2_ONLY_ITERTOOLS
ENGINE_GUARD_NAMES = {"PY2", "PY3", "IRONPY", "IRONPY2", "IRONPY3"}

# Builtins removed in Python 3. Flagged only when CALLED, and skipped when the
# name is imported (reduce/reload/intern have functools/importlib/sys homes) or
# engine-guarded.
PY2_REMOVED_BUILTIN_CALLS = {
    "raw_input", "execfile", "apply", "coerce", "intern", "buffer",
    "cmp", "reduce", "reload", "file",
}

# Stdlib modules renamed/removed in Python 3 (2to3 fix_imports). Matched on the
# top-level import name; engine-guarded imports (compat shims) are skipped.
PY2_ONLY_MODULES = {
    "StringIO", "cStringIO", "Queue", "cPickle", "ConfigParser", "copy_reg",
    "__builtin__", "HTMLParser", "htmlentitydefs", "urllib2", "urlparse",
    "robotparser", "httplib", "cookielib", "Cookie", "BaseHTTPServer",
    "SimpleHTTPServer", "CGIHTTPServer", "SocketServer", "xmlrpclib",
    "SimpleXMLRPCServer", "Tkinter", "tkFileDialog", "tkMessageBox",
    "thread", "dummy_thread", "UserDict", "UserList", "UserString",
    "anydbm", "commands", "_winreg", "markupbase",
}

# Python-3 lazy views/iterators that were lists in Python 2. Indexing or
# returning one bare breaks on any Python 3 engine (IronPython 3 included).
PY3_VIEW_METHODS = {"keys", "values", "items"}
PY3_LAZY_BUILTINS = {"map", "filter", "zip"}


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


def _receiver_name(node):
    """Final name of an immediate receiver: `clr` and `framework.clr` -> 'clr'.

    Returns None for a subscript/call/other receiver, so `foo[clr].Reference`
    or `obj[itertools].imap()` do not false-match a whole-subtree name search.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_engine_guarded(node, parents):
    """Return True if node sits under an engine-version guard.

    Recognized guards: an ``if`` whose test references an engine flag, a
    function whose decorators reference one (e.g. skipUnless(PY2, ...)), or a
    try/except NameError/ImportError (the shim-definition and import-fallback
    patterns, e.g. `try: from StringIO import StringIO / except ImportError:
    from io import StringIO`).
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
                if handler.type is not None and (
                    {"NameError", "ImportError"} & set(_names_in(handler.type))
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
    # imported names anywhere suppress removed-builtin/name findings
    # (e.g. `from functools import reduce`)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                defined.add(alias.asname or alias.name.split(".")[0])
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


def _bare_py3_view(node):
    """Return True if node is a bare Python-3 view/iterator call.

    ``d.keys()`` / ``.values()`` / ``.items()`` or ``map()`` / ``filter()``
    / ``zip()`` - each a subscriptable list in Python 2 but a lazy,
    non-indexable view in Python 3. A ``list()``/``sorted()``/etc. wrapper is
    a different node (its own Call), so wrapped uses are not matched here.
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in PY3_VIEW_METHODS:
        return True
    return isinstance(func, ast.Name) and func.id in PY3_LAZY_BUILTINS


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
                and _receiver_name(node.value) == "itertools"
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
                and _receiver_name(node.value) == "clr"
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
            if (
                "next" in method_names
                and "__iter__" in method_names
                and "__next__" not in (method_names | assigned_names)
            ):
                findings.append(
                    Finding(
                        path,
                        node.lineno,
                        "PY2-NEXT",
                        "iterator class {} defines next() but no __next__; "
                        "Python 3 uses __next__".format(node.name),
                    )
                )

        elif isinstance(node, ast.Import):
            if not _is_engine_guarded(node, parents):
                for alias in node.names:
                    if alias.name.split(".")[0] in PY2_ONLY_MODULES:
                        findings.append(
                            Finding(
                                path,
                                node.lineno,
                                "PY2-MODULE",
                                "module `{}` was renamed/removed in "
                                "Python 3".format(alias.name),
                            )
                        )

        elif isinstance(node, ast.ImportFrom):
            if not _is_engine_guarded(node, parents):
                if node.module == "itertools":
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
                if (
                    node.level == 0
                    and node.module
                    and node.module.split(".")[0] in PY2_ONLY_MODULES
                ):
                    findings.append(
                        Finding(
                            path,
                            node.lineno,
                            "PY2-MODULE",
                            "module `{}` was renamed/removed in "
                            "Python 3".format(node.module),
                        )
                    )

        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in PY2_REMOVED_BUILTIN_CALLS
            and node.func.id not in local_names
            and not _is_engine_guarded(node, parents)
        ):
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "PY2-BUILTIN",
                    "{}() was removed in Python 3".format(node.func.id),
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

        elif isinstance(node, ast.Subscript) and _bare_py3_view(node.value):
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "PY3-VIEW",
                    "indexing a Python-3 view/iterator (keys/values/items/"
                    "map/filter/zip); wrap in list()",
                )
            )

        elif (
            isinstance(node, ast.Return)
            and node.value is not None
            and _bare_py3_view(node.value)
        ):
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "PY3-VIEW",
                    "returning a bare Python-3 view/iterator (was a list in "
                    "Python 2); callers that index it break - wrap in list()",
                )
            )

        elif (
            isinstance(node, ast.Yield)
            and node.value is not None
            and _bare_py3_view(node.value)
        ):
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "PY3-VIEW",
                    "yielding a bare Python-3 view/iterator; wrap in list()",
                )
            )

        elif (
            isinstance(node, ast.Assign)
            and _bare_py3_view(node.value)
            and any(isinstance(t, ast.Attribute) for t in node.targets)
        ):
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    "PY3-VIEW",
                    "storing a bare Python-3 view/iterator to an attribute "
                    "(escapes to object state, later use unknown); wrap in "
                    "list()",
                )
            )

    return findings


def iter_python_files(roots, resolve_against):
    excluded = [REPO_ROOT.joinpath(*d.split("/")) for d in EXCLUDED_DIRS]
    for root in roots:
        root_path = root if root.is_absolute() else resolve_against / root
        # A missing path must not silently scan nothing and pass green -
        # this runs as a CI gate, where a typoed path would mask real findings
        if not root_path.exists():
            raise FileNotFoundError("path does not exist: {}".format(root_path))
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
    try:
        for path in iter_python_files(roots, resolve_against):
            file_count += 1
            all_findings.extend(check_file(path))
    except FileNotFoundError as err:
        print("error: {}".format(err), file=sys.stderr)
        return 2

    if file_count == 0:
        print(
            "error: scanned 0 files from {}".format(
                ", ".join(str(r) for r in roots)
            ),
            file=sys.stderr,
        )
        return 2

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
