r"""Static checker for Python-3 / engine-portability issues in first-party code.

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
    CLR-LIST    `List[T](python_iterable)` relies on IronPython collection
                coercion; build the list through the shared Add-based helper
    CLR-NAMESPACE Python class implementing a reload-sensitive CLR callback needs a stable
                `__namespace__` so pythonnet can reuse its generated type
    FORM-NATIVE a pyRevit form hands `self` to WPF as the native window or page
                (`.Owner = self`, `WindowInteropHelper(self)`,
                `isinstance(self, Window)`); under CPython the form is a
                Python controller wrapping the native root. Checked only in
                pyrevitlib and in scripts with a CPython shebang, since the
                same code is correct under IronPython

Findings in bundled extensions under ``extensions/`` are tracked, not blocking,
while those extensions migrate; the run still fails if their count exceeds
``TRACKED_EXTENSION_FINDINGS_LIMIT``.

A finding is not flagged when its branch is unreachable on IronPython 3,
its enclosing test is skipped on that engine, or it is inside a try/except
NameError/ImportError fallback (the name-shim and import-fallback patterns).
"""

import argparse
import ast
import json
import re
import sys
import tokenize
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCAN_ROOTS = [
    "pyrevitlib/pyrevit",
    "pyrevitlib/rpw",
    "pyrevitlib/rjm",
    "pyrevitlib/rpws",
    "pyrevitlib/rsparam",
    "extensions",
]

# Excluded from the Python-3-supported surface:
# - coreutils/markdown: vendored python-markdown with no first-party runtime
#   consumers (output.print_md renders via C#); a deprecated, unbundling
#   candidate that scripts should replace with pip `markdown`, so it is not
#   maintained against this checker
EXCLUDED_DIRS = [
    "pyrevitlib/pyrevit/coreutils/markdown",
]

# Files allowed to use IronPython-only CLR loading:
# - framework.py is the designated shim site; its calls are engine-gated
# - rpw's WPF bootstrap dispatches to the engine-local assemblies
# - the DevTools compile test exercises the IronPython engine by design
IPY_CLR_EXEMPT = [
    "pyrevitlib/pyrevit/framework.py",
    "pyrevitlib/rpw/ui/forms/resources.py",
    "extensions/pyRevitDevTools.extension/pyRevitDev.tab/Debug.panel/"
    "Engine Tests.pulldown/Test IronPython Compile.pushbutton/script.py",
]

# Files hosting the sanctioned engine dispatch for clr.Reference out-param
# marshaling; everywhere else should call their wrappers
# (geom.intersect_curves, create.load_family) instead
CLR_REF_EXEMPT = [
    "pyrevitlib/pyrevit/revit/db/create.py",
    "pyrevitlib/pyrevit/revit/geom.py",
]

PY2_ONLY_ITER_METHODS = {"iteritems", "iterkeys", "itervalues"}
PY2_ONLY_ITERTOOLS = {"ifilter", "ifilterfalse", "imap", "izip", "izip_longest"}
PY2_ONLY_NAMES = {
    "xrange",
    "basestring",
    "unicode",
    "unichr",
    "long",
    "StandardError",
} | PY2_ONLY_ITERTOOLS
IPY3_FLAG_VALUES = {
    "PY2": False,
    "PY3": True,
    "IRONPY": True,
    "IRONPY2": False,
    "IRONPY3": True,
}

# Builtins removed in Python 3. Flagged only when CALLED, and skipped when the
# name is imported (reduce/reload/intern have functools/importlib/sys homes) or
# engine-guarded.
PY2_REMOVED_BUILTIN_CALLS = {
    "raw_input",
    "execfile",
    "apply",
    "coerce",
    "intern",
    "buffer",
    "cmp",
    "reduce",
    "reload",
    "file",
}

# Stdlib modules renamed/removed in Python 3 (2to3 fix_imports). Matched on the
# top-level import name; engine-guarded imports (compat shims) are skipped.
PY2_ONLY_MODULES = {
    "StringIO",
    "cStringIO",
    "Queue",
    "cPickle",
    "ConfigParser",
    "copy_reg",
    "__builtin__",
    "HTMLParser",
    "htmlentitydefs",
    "urllib2",
    "urlparse",
    "robotparser",
    "httplib",
    "cookielib",
    "Cookie",
    "BaseHTTPServer",
    "SimpleHTTPServer",
    "CGIHTTPServer",
    "SocketServer",
    "xmlrpclib",
    "SimpleXMLRPCServer",
    "Tkinter",
    "tkFileDialog",
    "tkMessageBox",
    "thread",
    "dummy_thread",
    "UserDict",
    "UserList",
    "UserString",
    "anydbm",
    "commands",
    "_winreg",
    "markupbase",
}

# Python-3 lazy views/iterators that were lists in Python 2. Indexing or
# returning one bare breaks on any Python 3 engine (IronPython 3 included).
PY3_VIEW_METHODS = {"keys", "values", "items"}
PY3_LAZY_BUILTINS = {"map", "filter", "zip"}

PYTHON_ENGINE_CPYTHON = "cpython"
PYTHON_ENGINE_IRONPYTHON = "ironpython"
CPYTHON_FIRST_LINE_MARKERS = ("python3", "cpython")


class Finding:
    """A source finding emitted by the Python 3 compatibility scan."""

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


def _ipy3_condition_value(node):
    """Resolve an engine condition when its value is certain on IronPython 3."""
    if isinstance(node, ast.Name):
        return IPY3_FLAG_VALUES.get(node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = _ipy3_condition_value(node.operand)
        return None if value is None else not value
    if isinstance(node, ast.BoolOp):
        values = [_ipy3_condition_value(value) for value in node.values]
        if isinstance(node.op, ast.And):
            if False in values:
                return False
            return True if all(value is True for value in values) else None
        if isinstance(node.op, ast.Or):
            if True in values:
                return True
            return False if all(value is False for value in values) else None
    return None


def _is_engine_guarded(node, parents):
    """Return True when a branch cannot execute on IronPython 3."""
    current = node
    while current in parents:
        parent = parents[current]
        if isinstance(parent, ast.If):
            value = _ipy3_condition_value(parent.test)
            if value is False and current in parent.body:
                return True
            if value is True and current in parent.orelse:
                return True
        elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in parent.decorator_list:
                if not isinstance(decorator, ast.Call) or not decorator.args:
                    continue
                value = _ipy3_condition_value(decorator.args[0])
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "skipIf" and value is True:
                        return True
                    if decorator.func.attr == "skipUnless" and value is False:
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


PYTHON_ITERABLE_BUILTINS = {
    "list",
    "tuple",
    "set",
    "sorted",
    "reversed",
    "map",
    "filter",
}


def _is_generic_list_type(node):
    if not isinstance(node, ast.Subscript):
        return False
    target = node.value
    if isinstance(target, ast.Name):
        return target.id == "List"
    return isinstance(target, ast.Attribute) and target.attr == "List"


def _is_python_iterable(node):
    """Return whether node is clearly a Python iterable rather than a CLR value.

    Literal containers, comprehensions, generators, calls to the iterable
    builtins and bare names count; int capacities, attributes and other call
    results (e.g. ``uidoc.Selection.GetElementIds()``) are left alone.
    """
    if isinstance(
        node,
        (ast.List, ast.Tuple, ast.Set, ast.ListComp, ast.SetComp, ast.GeneratorExp),
    ):
        return True
    if isinstance(node, ast.Call):
        return (
            isinstance(node.func, ast.Name) and node.func.id in PYTHON_ITERABLE_BUILTINS
        )
    return isinstance(node, ast.Name)


def _is_generic_list_constructor(node):
    """Return whether node constructs a CLR List from a Python iterable.

    Matches ``List[T](...)`` and attribute-qualified forms such as
    ``framework.List[T](...)`` or ``Generic.List[T](...)``.
    """
    return (
        isinstance(node, ast.Call)
        and len(node.args) == 1
        and not node.keywords
        and _is_generic_list_type(node.func)
        and _is_python_iterable(node.args[0])
    )


CLR_NAMESPACE_INTERFACES = {
    "IExternalEventHandler",
    "ISelectionFilter",
    "IFailuresPreprocessor",
    "IFamilyLoadOptions",
    "IDuplicateTypeNamesHandler",
}


def _is_clr_interface_base(node):
    """Return whether a class base needs a stable generated CLR type."""
    if isinstance(node, ast.Name):
        name = node.id
    elif isinstance(node, ast.Attribute):
        name = node.attr
    else:
        return False
    return name in CLR_NAMESPACE_INTERFACES


def _has_stable_clr_namespace(node):
    """Return whether an interface class declares a literal namespace."""
    for item in node.body:
        if not isinstance(item, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__namespace__"
            for target in item.targets
        ):
            continue
        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
            return bool(item.value.value)
    return False


def _base_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _literal_list(tree, name):
    """Return the literal value of a module-level ``name = [...]`` assignment."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    return []


def _exported_form_classes(forms_dir):
    """Return the pyRevit form classes ``forms/_common.py`` exports.

    Reads ``__all__`` without importing pyrevitlib and keeps the names whose
    class hierarchy in ``forms/*.py`` reaches ``FORM_ROOT_MIXIN``, the base
    shared by every window and panel form. Outside a pyRevit checkout the
    forms sources are absent and the result is empty, which disables
    FORM-NATIVE.
    """
    try:
        exported = _literal_list(
            ast.parse((forms_dir / "_common.py").read_text(encoding="utf-8")),
            "__all__",
        )
    except (OSError, SyntaxError, ValueError):
        return frozenset()
    class_bases = {}
    for module in sorted(forms_dir.glob("*.py")):
        try:
            tree = ast.parse(module.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_bases[node.name] = [_base_name(base) for base in node.bases]

    def reaches_root(name, seen):
        if name == FORM_ROOT_MIXIN:
            return True
        if name in seen or name not in class_bases:
            return False
        seen.add(name)
        return any(reaches_root(base, seen) for base in class_bases[name])

    return frozenset(
        name for name in exported if name in class_bases and reaches_root(name, set())
    )


FORMS_DIR = REPO_ROOT / "pyrevitlib" / "pyrevit" / "forms"
FORM_ROOT_MIXIN = "_WPFMixin"
FORM_BASES = _exported_form_classes(FORMS_DIR)

NATIVE_FORM_TYPES = {"Window", "Page"}


def _is_self(node):
    return isinstance(node, ast.Name) and node.id == "self"


_BUNDLE_ENGINE_TYPE_PATTERNS = (
    re.compile(
        r"^engine[ \t]*:[ \t]*(?:#.*)?\r?\n"
        r"(?:(?:[ \t]+.*|[ \t]*)\r?\n)*?"
        r"[ \t]+type[ \t]*:[ \t]*['\"]?([^'\"\s#,}]*)",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^engine[ \t]*:[ \t]*\{[^}]*?\btype[ \t]*:[ \t]*['\"]?([^'\"\s,}]*)",
        re.IGNORECASE | re.MULTILINE,
    ),
)


def _extension_engine_type(path):
    """Return the raw engine type the enclosing extension.json declares, if any.

    Mirrors ``pyrevit.extensions.get_declared_engine_type``: ``"engine"`` may be
    a string or a mapping with ``type``.
    """
    for parent in path.parents:
        if not parent.name.endswith(".extension"):
            continue
        manifest = parent / "extension.json"
        if not manifest.is_file():
            return None
        try:
            engine = json.loads(manifest.read_text(encoding="utf-8-sig")).get("engine")
        except (OSError, ValueError, AttributeError):
            return None
        if isinstance(engine, dict):
            engine = engine.get("type")
        return engine if isinstance(engine, str) else None
    return None


def _scalar_value(node):
    import yaml

    return node.value if isinstance(node, yaml.ScalarNode) else None


def _bundle_engine_type_from_yaml(text):
    """Read ``engine.type`` from the YAML node tree, as the C# BundleParser does.

    Composing nodes without constructing values keeps every scalar a string
    and accepts any tag, matching YamlDotNet's representation model rather
    than PyYAML's stricter ``safe_load``.
    """
    import yaml

    documents = list(yaml.compose_all(text))
    root = documents[0] if documents else None
    if not isinstance(root, yaml.MappingNode):
        return None
    engine_type = None
    for key, engine in root.value:
        if (_scalar_value(key) or "").strip().lower() != "engine":
            continue
        if not isinstance(engine, yaml.MappingNode):
            continue
        for engine_key, value in engine.value:
            if (_scalar_value(engine_key) or "").strip().lower() == "type":
                engine_type = _scalar_value(value)
    return engine_type


def _bundle_engine_type_from_regex(text):
    for pattern in _BUNDLE_ENGINE_TYPE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _bundle_engine_type(path):
    """Return the raw ``engine.type`` of the script's bundle.yaml, if any.

    Parses the YAML node tree with PyYAML when it is installed so block and
    flow mappings both count. A stock Python 3, or text PyYAML rejects, falls
    back to regexes covering both styles, so the result does not depend on
    PyYAML being installed.
    """
    bundle = path.parent / "bundle.yaml"
    if not bundle.is_file():
        return None
    try:
        text = bundle.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    try:
        import yaml
    except ImportError:
        return _bundle_engine_type_from_regex(text)
    try:
        return _bundle_engine_type_from_yaml(text)
    except yaml.YAMLError:
        return _bundle_engine_type_from_regex(text)


def _first_line_selects_cpython(first_line):
    """Apply the runtime's shebang rule: a case-sensitive substring match.

    Mirrors ``pyrevit.extensions.first_line_selects_cpython``, which follows
    ``ScriptRuntime.EngineType``: any first line containing a marker selects
    CPython, with or without ``#!``.
    """
    return any(marker in first_line for marker in CPYTHON_FIRST_LINE_MARKERS)


def _selects_cpython(bundle_engine_type, extension_engine_type, first_line):
    """Return whether the runtime would run a Python script under CPython.

    Invariant:
        Mirrors the C# command generator plus ``ScriptRuntime``: a non-blank
        bundle ``engine.type`` replaces the extension declaration, and only
        ``cpython``/``ironpython`` (any case) decide outright; any other bundle
        value falls back to the first-line rule. Otherwise an extension
        ``cpython`` declaration selects CPython, then the first-line rule.
    """
    if bundle_engine_type is not None and bundle_engine_type.strip():
        bundle_engine = bundle_engine_type.lower()
        if bundle_engine == PYTHON_ENGINE_CPYTHON:
            return True
        if bundle_engine == PYTHON_ENGINE_IRONPYTHON:
            return False
        return _first_line_selects_cpython(first_line)
    if (
        extension_engine_type is not None
        and extension_engine_type.strip().lower() == PYTHON_ENGINE_CPYTHON
    ):
        return True
    return _first_line_selects_cpython(first_line)


def _may_run_under_cpython(path, source):
    """Return whether a file is pyrevitlib code or a script that runs under CPython."""
    try:
        path.relative_to(REPO_ROOT / "pyrevitlib")
        return True
    except ValueError:
        pass
    return _selects_cpython(
        _bundle_engine_type(path),
        _extension_engine_type(path),
        re.split(r"\r\n|\r|\n", source, maxsplit=1)[0],
    )


def _class_body_nodes(class_node):
    """Yield a class's nodes without entering nested classes, checked on their own."""
    pending = list(ast.iter_child_nodes(class_node))
    while pending:
        node = pending.pop()
        if isinstance(node, ast.ClassDef):
            continue
        yield node
        pending.extend(ast.iter_child_nodes(node))


def _native_form_uses(class_node):
    """Return (node, usage) pairs where a form class treats ``self`` as WPF."""
    if not any(_base_name(base) in FORM_BASES for base in class_node.bases):
        return []
    return sorted(_self_as_native(class_node), key=lambda use: use[0].lineno)


def _self_as_native(class_node):
    for node in _class_body_nodes(class_node):
        if isinstance(node, ast.Assign) and _is_self(node.value):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "Owner":
                    yield node, "`.Owner = self`"
        elif isinstance(node, ast.Call) and node.args and _is_self(node.args[0]):
            name = _base_name(node.func)
            if name == "WindowInteropHelper":
                yield node, "`WindowInteropHelper(self)`"
            elif (
                name == "isinstance"
                and len(node.args) == 2
                and _base_name(node.args[1]) in NATIVE_FORM_TYPES
            ):
                yield node, "`isinstance(self, {})`".format(_base_name(node.args[1]))


class _FileContext:
    """Per-file facts the rules share, computed once per checked file."""

    def __init__(self, path, source, tree):
        self.path = path
        self.source = source
        self.tree = tree
        self.parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node
        self.local_names = _locally_defined_names(tree)
        self.clr_exempt = _is_listed(path, IPY_CLR_EXEMPT)
        self.clr_ref_exempt = _is_listed(path, CLR_REF_EXEMPT)

    def is_engine_guarded(self, node):
        return _is_engine_guarded(node, self.parents)


def _is_listed(path, repo_paths):
    return any(path == REPO_ROOT.joinpath(*entry.split("/")) for entry in repo_paths)


def _py2_iter_attribute(node, ctx):
    if node.attr in PY2_ONLY_ITER_METHODS:
        yield "PY2-ITER", ".{}() does not exist in Python 3".format(node.attr)
    elif node.attr in PY2_ONLY_ITERTOOLS and _receiver_name(node.value) == "itertools":
        yield "PY2-ITER", "itertools.{} does not exist in Python 3".format(node.attr)


def _py2_has_key(node, ctx):
    if node.attr == "has_key":
        yield "PY2-HASKEY", ".has_key() does not exist in Python 3 (use `in`)"


def _ipy_clr_file_reference(node, ctx):
    if node.attr == "AddReferenceToFileAndPath" and not ctx.clr_exempt:
        yield (
            "IPY-CLR",
            "IronPython-only CLR API; route through the pyrevit.framework shim",
        )


def _clr_reference(node, ctx):
    if (
        node.attr == "Reference"
        and _receiver_name(node.value) == "clr"
        and not ctx.clr_ref_exempt
    ):
        yield (
            "CLR-REF",
            "IronPython-only out-param marshaling; use "
            "geom.intersect_curves / create.load_family or an "
            "engine-dispatched wrapper",
        )


def _py2_name(node, ctx):
    if (
        isinstance(node.ctx, ast.Load)
        and node.id in PY2_ONLY_NAMES
        and node.id not in ctx.local_names
        and not ctx.is_engine_guarded(node)
    ):
        yield "PY2-NAME", "`{}` does not exist in Python 3".format(node.id)


def _class_member_names(node):
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
    return method_names, method_names | assigned_names


def _py2_bool(node, ctx):
    method_names, member_names = _class_member_names(node)
    if "__nonzero__" in method_names and "__bool__" not in member_names:
        yield (
            "PY2-BOOL",
            "class {} defines __nonzero__ but no __bool__; "
            "Python 3 ignores __nonzero__".format(node.name),
        )


def _py2_next(node, ctx):
    method_names, member_names = _class_member_names(node)
    if (
        "next" in method_names
        and "__iter__" in method_names
        and "__next__" not in member_names
    ):
        yield (
            "PY2-NEXT",
            "iterator class {} defines next() but no __next__; "
            "Python 3 uses __next__".format(node.name),
        )


def _clr_namespace(node, ctx):
    if any(
        _is_clr_interface_base(base) for base in node.bases
    ) and not _has_stable_clr_namespace(node):
        yield (
            "CLR-NAMESPACE",
            "class {} implements a CLR interface without a literal, "
            "stable __namespace__".format(node.name),
        )


def _py2_module_import(node, ctx):
    if ctx.is_engine_guarded(node):
        return
    for alias in node.names:
        if alias.name.split(".")[0] in PY2_ONLY_MODULES:
            yield (
                "PY2-MODULE",
                "module `{}` was renamed/removed in Python 3".format(alias.name),
            )


def _py2_from_import(node, ctx):
    if ctx.is_engine_guarded(node):
        return
    if node.module == "itertools":
        for alias in node.names:
            if alias.name in PY2_ONLY_ITERTOOLS:
                yield (
                    "PY2-ITER",
                    "itertools.{} does not exist in Python 3".format(alias.name),
                )
    if (
        node.level == 0
        and node.module
        and node.module.split(".")[0] in PY2_ONLY_MODULES
    ):
        yield (
            "PY2-MODULE",
            "module `{}` was renamed/removed in Python 3".format(node.module),
        )


def _py2_builtin_call(node, ctx):
    if (
        isinstance(node.func, ast.Name)
        and node.func.id in PY2_REMOVED_BUILTIN_CALLS
        and node.func.id not in ctx.local_names
        and not ctx.is_engine_guarded(node)
    ):
        yield "PY2-BUILTIN", "{}() was removed in Python 3".format(node.func.id)


def _sort_key(node, ctx):
    if _keyless_sorted_over_dict_view(node):
        yield (
            "SORT-KEY",
            "sorted() over dict view without key=; tuple comparison "
            "can fall through to unorderable values in Python 3",
        )


def _clr_list(node, ctx):
    if _is_generic_list_constructor(node):
        yield (
            "CLR-LIST",
            "List[T](python_iterable) relies on IronPython coercion; "
            "build the list through an Add-based helper",
        )


def _indexed_view(node, ctx):
    if _bare_py3_view(node.value):
        yield (
            "PY3-VIEW",
            "indexing a Python-3 view/iterator (keys/values/items/"
            "map/filter/zip); wrap in list()",
        )


def _returned_view(node, ctx):
    if node.value is not None and _bare_py3_view(node.value):
        yield (
            "PY3-VIEW",
            "returning a bare Python-3 view/iterator (was a list in "
            "Python 2); callers that index it break - wrap in list()",
        )


def _yielded_view(node, ctx):
    if node.value is not None and _bare_py3_view(node.value):
        yield "PY3-VIEW", "yielding a bare Python-3 view/iterator; wrap in list()"


def _attribute_stored_view(node, ctx):
    if _bare_py3_view(node.value) and any(
        isinstance(target, ast.Attribute) for target in node.targets
    ):
        yield (
            "PY3-VIEW",
            "storing a bare Python-3 view/iterator to an attribute "
            "(escapes to object state, later use unknown); wrap in "
            "list()",
        )


NODE_RULES = {
    ast.Attribute: (
        _py2_iter_attribute,
        _py2_has_key,
        _ipy_clr_file_reference,
        _clr_reference,
    ),
    ast.Name: (_py2_name,),
    ast.ClassDef: (_py2_bool, _py2_next, _clr_namespace),
    ast.Import: (_py2_module_import,),
    ast.ImportFrom: (_py2_from_import,),
    ast.Call: (_py2_builtin_call, _sort_key, _clr_list),
    ast.Subscript: (_indexed_view,),
    ast.Return: (_returned_view,),
    ast.Yield: (_yielded_view,),
    ast.Assign: (_attribute_stored_view,),
}


def _form_native(ctx):
    if not _may_run_under_cpython(ctx.path, ctx.source):
        return
    for class_node in ast.walk(ctx.tree):
        if not isinstance(class_node, ast.ClassDef):
            continue
        for node, usage in _native_form_uses(class_node):
            yield (
                node.lineno,
                "FORM-NATIVE",
                "{} treats a pyRevit form as its native WPF root; under "
                "CPython hand WPF the native root instead".format(usage),
            )


FILE_RULES = (_form_native,)


def _parse(path):
    """Return ``(source, tree, findings)``; ``tree`` is None when unparsable."""
    try:
        with tokenize.open(path) as fp:
            source = fp.read()
    except (OSError, SyntaxError, UnicodeDecodeError) as err:
        return None, None, [Finding(path, 0, "SYNTAX", "cannot read: {}".format(err))]

    findings = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", SyntaxWarning)
            tree = ast.parse(source, filename=str(path))
    except SyntaxError as err:
        message = "does not parse as Python 3: {}".format(err.msg)
        return source, None, [Finding(path, err.lineno or 0, "SYNTAX", message)]
    for warning in caught:
        if issubclass(warning.category, SyntaxWarning):
            findings.append(
                Finding(path, warning.lineno, "SYNTAX-WARN", str(warning.message))
            )
    return source, tree, findings


def check_file(path):
    """Return compatibility findings for one Python source file.

    File-level rules in ``FILE_RULES`` report first, then every AST node is
    passed to the ``NODE_RULES`` registered for its exact type, in order. A
    node rule takes ``(node, ctx)`` and yields ``(code, message)`` pairs
    reported at the node's line.
    """
    source, tree, findings = _parse(path)
    if tree is None:
        return findings

    ctx = _FileContext(path, source, tree)
    for rule in FILE_RULES:
        findings.extend(
            Finding(path, lineno, code, message) for lineno, code, message in rule(ctx)
        )
    for node in ast.walk(tree):
        for rule in NODE_RULES.get(type(node), ()):
            findings.extend(
                Finding(path, node.lineno, code, message)
                for code, message in rule(node, ctx)
            )
    return findings


def iter_python_files(roots, resolve_against):
    """Yield source files under the requested roots, excluding unsupported trees."""
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


TRACKED_EXTENSION_FINDINGS_LIMIT = 54


def _is_tracked_extension_finding(finding):
    """Return whether a phased first-party extension finding is non-blocking."""
    try:
        finding.path.relative_to(REPO_ROOT / "extensions")
    except ValueError:
        return False
    return finding.code in {"CLR-LIST", "CLR-NAMESPACE", "FORM-NATIVE"}


def main():
    """Run the checker CLI and return its process exit code."""
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
            "error: scanned 0 files from {}".format(", ".join(str(r) for r in roots)),
            file=sys.stderr,
        )
        return 2

    for finding in all_findings:
        print(finding)

    blocking_findings = [
        finding
        for finding in all_findings
        if not _is_tracked_extension_finding(finding)
    ]
    tracked_findings = [
        finding for finding in all_findings if _is_tracked_extension_finding(finding)
    ]
    counts = {}
    for finding in blocking_findings:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    summary = ", ".join(
        "{}: {}".format(code, count) for code, count in sorted(counts.items())
    )
    print(
        "\nscanned {} files; {} blocking finding(s){}{}".format(
            file_count,
            len(blocking_findings),
            " ({})".format(summary) if summary else "",
            "; {} tracked extension finding(s)".format(len(tracked_findings))
            if tracked_findings
            else "",
        )
    )
    if len(tracked_findings) > TRACKED_EXTENSION_FINDINGS_LIMIT:
        print(
            "tracked extension findings rose to {} (limit {}); fix the new ones "
            "rather than raising the limit".format(
                len(tracked_findings), TRACKED_EXTENSION_FINDINGS_LIMIT
            )
        )
        return 1
    return 1 if blocking_findings else 0


if __name__ == "__main__":
    sys.exit(main())
