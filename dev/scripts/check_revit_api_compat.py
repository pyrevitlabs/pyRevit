r"""Static checker for Revit API version compatibility of pyRevit scripts.

Flags uses of Revit API types and members that do not exist (or are
deprecated) in some Revit year a script can run in, unless the use is
protected. Run with any CPython 3.9+; it has no dependencies and never
imports or executes the code it reads:

    pipenv run check-revit-api [paths ...]
    python check_revit_api_compat.py path/to/MyExtension.extension
    python check_revit_api_compat.py --git-url https://github.com/org/repo.git
    python check_revit_api_compat.py --extensions all

With no paths it lints the CI targets: ``extensions/pyRevitTools.extension``
and ``pyrevitlib``. Exit code is 1 when errors exist (warnings too with
``--strict``), 2 on usage or I/O problems.

API facts come from ``revit_api_catalog/catalog.json``, generated from the
real RevitAPI/RevitAPIUI assemblies by ``build_revit_api_catalog.py`` (an
on-demand step - see that script). Curated knowledge (pyRevit helpers, fix
wording, tiers, .NET runtime entries) comes from
``revit_api_catalog/overrides.json`` and is merged here at load time.

A use is protected when, for every Revit year it can execute in, the member
exists. The years a line can execute in start from the script's effective
``min_revit_version``/``max_revit_version`` (intersected over the extension
and every parent bundle, bundle.yaml taking precedence over
``__min_revit_ver__``/``__max_revit_ver__``, as the C# loader does) and are
narrowed by enclosing runtime checks: ``HOST_APP.is_newer_than(v[, or_equal])``,
``is_older_than``, ``is_exactly``, comparisons of a version value with a year,
``pyrevit.compat.NETCORE``/``NETFRAMEWORK``, including ``and`` chains,
ternaries and early exits. Feature detection - ``hasattr``, ``getattr`` with a
default, or a ``try`` whose handler catches AttributeError/ImportError/
TypeError/Exception (bare included) - protects both the guarded code and its
fallback.

Checks:
    API-MISSING     a type/member used in a year where it does not exist
    API-OVERLOAD    a call passes a Revit type no remaining overload accepts
    API-DEPRECATED  a type/member used in a year where it is [Obsolete]
    DOTNET          a .NET Framework API used where Revit runs on .NET 8+
    ENGINE          an IronPython-only module imported by a ``#! python3`` script
    BUNDLE          an unparseable min/max_revit_version (the loader hides it)
    PARSE           a file that cannot be analyzed (IronPython 2 syntax)
    SUPPRESS        a ``# compat-ignore`` without justification, or unused

A year counts only when every update release of it has the API; years
where only some updates do are reported as missing too, with a hint to use
feature detection, because ``HOST_APP`` checks see the year, not the update.

Severity: references resolved to a fully qualified type (``DB.X``, imports)
are exact and report as errors. Bare attribute accesses (``obj.IntegerValue``)
are reported only when no Revit type offers that name in the failing years;
overrides.json can demote or disable ambiguous names. Deprecations are
warnings.

Suppress a finding with a justified pragma on its line (or anywhere in
its statement's header); an optional id list narrows it::

    value = eid.IntegerValue  # compat-ignore: only reached under Revit 2023
    value = eid.IntegerValue  # compat-ignore[API-MISSING]: legacy branch

Existing debt can be frozen in a baseline so CI fails only on new findings
(``--baseline``; refresh with ``--update-baseline`` after fixing some).
Baseline entries match on path, code and message, not line numbers.

Python 2 vs 3 language portability is a separate axis, covered by
``check_py3_compat.py``.
"""

import argparse
import ast
import fnmatch
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tokenize
import warnings
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
CATALOG_PATH = SCRIPT_DIR / "revit_api_catalog" / "catalog.json"
OVERRIDES_PATH = SCRIPT_DIR / "revit_api_catalog" / "overrides.json"
BASELINE_PATH = SCRIPT_DIR / "revit_api_catalog" / "baseline.json"
EXTENSIONS_CATALOG_PATH = REPO_ROOT / "extensions" / "extensions.json"

DEFAULT_SCAN_ROOTS = [
    "extensions/pyRevitTools.extension",
    "pyrevitlib",
]

EXCLUDED_DIRS = {"__pycache__", ".git", "site-packages", "node_modules", ".venv"}

COMPONENT_POSTFIXES = (
    ".extension",
    ".tab",
    ".panel",
    ".stack",
    ".pulldown",
    ".splitbutton",
    ".splitpushbutton",
    ".pushbutton",
    ".smartbutton",
    ".linkbutton",
    ".invokebutton",
    ".panelbutton",
    ".nobutton",
    ".content",
    ".urlbutton",
    ".combobox",
)
BUNDLE_FILE = "bundle.yaml"
SCRIPT_STEM_ENDINGS = ("script",)

API_ROOTS = ("Autodesk.", "System.")
REEXPORTED_NAMESPACES = {
    "pyrevit.DB": "Autodesk.Revit.DB",
    "pyrevit.UI": "Autodesk.Revit.UI",
    "pyrevit.api.DB": "Autodesk.Revit.DB",
    "pyrevit.api.UI": "Autodesk.Revit.UI",
    "pyrevit.revit.DB": "Autodesk.Revit.DB",
    "pyrevit.revit.UI": "Autodesk.Revit.UI",
    "rpw.DB": "Autodesk.Revit.DB",
    "rpw.UI": "Autodesk.Revit.UI",
    "rpw.revit.DB": "Autodesk.Revit.DB",
    "rpw.revit.UI": "Autodesk.Revit.UI",
}
DEFAULT_ALIASES = {"DB": "Autodesk.Revit.DB", "UI": "Autodesk.Revit.UI"}

HOST_VERSION_METHODS = {"is_newer_than", "is_older_than", "is_exactly"}
NETCORE_FIRST_YEAR = 2025
NETCORE_FLAGS = {"NETCORE": True, "NETFRAMEWORK": False}
FEATURE_TEST_CALLS = {"hasattr"}
GUARDING_EXCEPTIONS = {
    "AttributeError",
    "ImportError",
    "ModuleNotFoundError",
    "NameError",
    "TypeError",
    "Exception",
    "BaseException",
    "MissingMemberException",
    "MissingMethodException",
    "ArgumentException",
    "PlatformNotSupportedException",
}
EXIT_CALL_NAMES = {"exit", "quit", "_exit"}
YEAR_MIN, YEAR_MAX = 2000, 2100

ERROR, WARNING = "error", "warning"
SUPPRESS_RE = re.compile(
    r"#\s*compat-ignore(?:\[(?P<ids>[^\]]*)\])?\s*(?::\s*(?P<reason>.*))?$"
)
VERSION_NAME_RE = re.compile(r"(?i)ver|year")
NOT_REVIT_VERSION_RE = re.compile(r"(?i)py|engine|net|clr|sys|schema|format|file")


def format_years(years):
    """Render a year set compactly: ``2021-2023, 2026``."""
    runs = []
    for year in sorted(years):
        if runs and year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return ", ".join(
        str(a) if a == b else "{}-{}".format(a, b) for a, b in (tuple(r) for r in runs)
    )


def _years_from_ranges(ranges):
    years = set()
    for first, last in ranges:
        years.update(range(first, last + 1))
    return frozenset(years)


def _deep_merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class Catalog:
    """Merged API change data: generated facts plus curated overrides.

    Invariant:
        Availability is expressed as year sets inside ``universe``; an entry
        without ``avail`` exists in every cataloged year.
    """

    def __init__(self, generated, overrides=None):
        overrides = overrides or {}
        self.years = list(generated["years"])
        self.universe = frozenset(range(self.years[0], self.years[-1] + 1))
        self.types = _deep_merge(
            json.loads(json.dumps(generated.get("types", {}))),
            overrides.get("types", {}),
        )
        self.instance_members = _deep_merge(
            json.loads(json.dumps(generated.get("instance_members", {}))),
            overrides.get("instance_members", {}),
        )
        self.namespaces = overrides.get("namespaces", {})
        self.cpython_unavailable_modules = overrides.get("engine", {}).get(
            "cpython_unavailable_modules", {}
        )
        self.packages = generated.get("packages", {})

    @classmethod
    def load(cls, catalog_path=CATALOG_PATH, overrides_path=OVERRIDES_PATH):
        """Read the catalog files; raises OSError/ValueError when unreadable."""
        generated = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        overrides = {}
        if overrides_path and Path(overrides_path).exists():
            overrides = json.loads(Path(overrides_path).read_text(encoding="utf-8"))
        return cls(generated, overrides)

    def avail(self, entry):
        """Years an entry exists in."""
        if "avail" in entry:
            return _years_from_ranges(entry["avail"]) & self.universe
        return self.universe

    def partial(self, entry):
        """Years only some update releases have an entry in.

        The linter counts these as missing: a year check cannot tell updates
        apart, so only feature detection protects such a use.
        """
        return _years_from_ranges(entry.get("partial", [])) & self.universe

    def member_entry(self, type_name, member):
        """Return (entry, declaring type entry) for a member, walking bases.

        A member a derived type inherits is cataloged on the base that
        declares it; returns (None, None) when no cataloged ancestor has it.
        """
        seen = set()
        while type_name in self.types and type_name not in seen:
            seen.add(type_name)
            type_entry = self.types[type_name]
            entry = type_entry.get("members", {}).get(member)
            if entry is not None:
                return entry, type_entry
            type_name = type_entry.get("base", "")
        return None, None

    def obsolete_years(self, entry):
        """Years an entry exists in while marked [Obsolete]."""
        if "obsolete_years" in entry:
            return _years_from_ranges(entry["obsolete_years"]) & self.universe
        obsolete = entry.get("obsolete")
        if not obsolete:
            return frozenset()
        return frozenset(y for y in self.avail(entry) if y >= obsolete["since"])

    def split_qualified(self, full_name):
        """Split a dotted name into (type name, member, trailing attrs).

        Returns None when no cataloged type is a prefix of the name.
        """
        parts = full_name.split(".")
        for cut in range(len(parts), 0, -1):
            type_name = ".".join(parts[:cut])
            if type_name in self.types:
                rest = parts[cut:]
                return type_name, (rest[0] if rest else None), rest[1:]
        return None

    def namespace_entry(self, full_name):
        """Return (namespace, entry) for a curated namespace containing a name."""
        for namespace, entry in self.namespaces.items():
            if full_name == namespace or full_name.startswith(namespace + "."):
                return namespace, entry
        return None

    def is_type(self, full_name):
        """True if the name is a cataloged type (changed itself or a parent)."""
        return full_name in self.types


class Finding:
    """One reported problem at a source location."""

    def __init__(self, path, line, col, code, severity, message, fix="", years=None):
        self.path = path
        self.line = line
        self.col = col
        self.code = code
        self.severity = severity
        self.message = message
        self.fix = fix
        self.years = years
        self.stmt_span = (line, line)

    def shown_path(self, base=None):
        """Path relative to base, the repository or the cwd, whichever fits."""
        for root in [base, REPO_ROOT, Path.cwd()]:
            if root is None:
                continue
            try:
                return self.path.relative_to(root).as_posix()
            except ValueError:
                continue
        return self.path.as_posix()

    def as_dict(self, base=None):
        """JSON-ready form, with the path shown relative to base."""
        return {
            "path": self.shown_path(base),
            "line": self.line,
            "col": self.col,
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "fix": self.fix,
        }

    def __str__(self):
        return "{}:{}:{}: {} [{}] {}".format(
            self.shown_path(),
            self.line,
            self.col,
            self.severity,
            self.code,
            self.message,
        )


def _parse_year(value):
    if value is None:
        return None
    text = str(value).strip().strip("\"'")
    if not text:
        return None
    if re.fullmatch(r"\d{4}", text):
        return int(text)
    raise ValueError(text)


def read_bundle_versions(bundle_path):
    """Read top-level min/max_revit_version scalars from a bundle.yaml.

    Only column-0 ``key: value`` lines are considered, matching how the
    loader reads these keys as top-level scalars; nested keys are ignored.
    """
    values = {}
    try:
        text = bundle_path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return values
    for raw in text.splitlines():
        if not raw or raw[0] in " \t#-":
            continue
        key, sep, value = raw.partition(":")
        key = key.strip().lower()
        if not sep or key not in ("min_revit_version", "max_revit_version"):
            continue
        value = value.split(" #", 1)[0].strip()
        if value:
            values[key] = value
    return values


def read_script_versions(script_path):
    """Read module-level ``__min_revit_ver__``/``__max_revit_ver__`` constants."""
    values = {}
    try:
        with tokenize.open(script_path) as handle, warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(handle.read())
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return values
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in (
                "__min_revit_ver__",
                "__max_revit_ver__",
            ):
                key = (
                    "min_revit_version"
                    if target.id == "__min_revit_ver__"
                    else "max_revit_version"
                )
                values[key] = str(node.value.value)
    return values


def _component_script(directory):
    try:
        candidates = sorted(
            p
            for p in directory.iterdir()
            if p.suffix.lower() == ".py"
            and p.stem.lower().endswith(SCRIPT_STEM_ENDINGS)
        )
    except OSError:
        return None
    return candidates[0] if candidates else None


class BundleRanges:
    """Effective Revit year range per directory, cached across files.

    Important:
        Mirrors ExtensionParser.cs: an extension's root bundle.yaml gates the
        whole tree; each component's bundle.yaml value wins over its script's
        dunder constant; a hidden parent hides its children, so the effective
        range is the intersection along the ancestor chain.
    """

    def __init__(self, universe):
        self.universe = universe
        self._cache = {}
        self.problems = []

    def years_for(self, path):
        """Return (years, constraint descriptions) for a file."""
        return self._for_dir(path.parent)

    def _for_dir(self, directory):
        if directory in self._cache:
            return self._cache[directory]
        parent = directory.parent
        if parent == directory:
            result = (self.universe, [])
        else:
            years, reasons = self._for_dir(parent)
            if directory.name.lower().endswith(COMPONENT_POSTFIXES):
                years, reasons = self._apply_component(directory, years, reasons)
            result = (years, reasons)
        self._cache[directory] = result
        return result

    def _apply_component(self, directory, years, reasons):
        values = {}
        script = None
        if not directory.name.lower().endswith(".extension"):
            script = _component_script(directory)
            if script is not None:
                values.update(read_script_versions(script))
        bundle = directory / BUNDLE_FILE
        values.update(read_bundle_versions(bundle))
        if not values:
            return years, reasons
        source = bundle if bundle.exists() else script
        try:
            low = _parse_year(values.get("min_revit_version"))
            high = _parse_year(values.get("max_revit_version"))
        except ValueError as err:
            self.problems.append(
                Finding(
                    source or bundle,
                    1,
                    0,
                    "BUNDLE",
                    ERROR,
                    "min/max_revit_version '{}' is not a 4-digit year; the "
                    "loader hides this component in every Revit".format(err),
                )
            )
            return frozenset(), reasons + ["{}: invalid".format(directory.name)]
        narrowed = frozenset(
            y
            for y in years
            if (low is None or y >= low) and (high is None or y <= high)
        )
        label = []
        if low is not None:
            label.append("min {}".format(low))
        if high is not None:
            label.append("max {}".format(high))
        return narrowed, reasons + ["{} ({})".format(directory.name, ", ".join(label))]


class _Condition:
    """Years a test is true / false in, and whether it detects features."""

    __slots__ = ("true", "false", "feature")

    def __init__(self, true, false, feature=False):
        self.true = true
        self.false = false
        self.feature = feature


def _year_literal(node):
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and YEAR_MIN <= value <= YEAR_MAX:
            return value
        if isinstance(value, str) and re.fullmatch(r"\d{4}", value.strip()):
            year = int(value)
            if YEAR_MIN <= year <= YEAR_MAX:
                return year
    return None


def _strip_casts(node):
    while (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("int", "str", "float")
        and len(node.args) == 1
    ):
        node = node.args[0]
    return node


def _terminal_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _terminal_name(node.func)
    return None


def _is_version_value(node):
    node = _strip_casts(node)
    name = _terminal_name(node)
    if not name:
        return False
    if isinstance(node, ast.Attribute) and _terminal_name(node.value) in (
        "HOST_APP",
        "host_app",
    ):
        return name in ("version", "version_name") or bool(VERSION_NAME_RE.search(name))
    return bool(VERSION_NAME_RE.search(name)) and not NOT_REVIT_VERSION_RE.search(name)


def _compare_years(op, year, universe):
    checks = {
        ast.Gt: lambda y: y > year,
        ast.GtE: lambda y: y >= year,
        ast.Lt: lambda y: y < year,
        ast.LtE: lambda y: y <= year,
        ast.Eq: lambda y: y == year,
        ast.NotEq: lambda y: y != year,
    }
    check = checks.get(type(op))
    if check is None:
        return None
    return frozenset(y for y in universe if check(y))


_FLIPPED = {ast.Gt: ast.Lt, ast.Lt: ast.Gt, ast.GtE: ast.LtE, ast.LtE: ast.GtE}


class FileAnalyzer:
    """Walks one module, tracking the Revit years each node can run in."""

    def __init__(self, path, source, tree, catalog, years, bundle_reasons):
        self.path = path
        self.source = source
        self.tree = tree
        self.catalog = catalog
        self.base_years = years
        self.bundle_reasons = bundle_reasons
        self.in_bundle = bool(bundle_reasons) or any(
            p.name.lower().endswith(COMPONENT_POSTFIXES) for p in path.parents
        )
        self.findings = []
        self.aliases = dict(DEFAULT_ALIASES)
        self.star_namespaces = []
        self.local_names = set()
        self.own_attributes = set()
        self.feature_vars = set()
        self.version_vars = {}
        self._resolving = set()
        self.is_cpython = source.lstrip("﻿").startswith("#!") and (
            "python3" in source.splitlines()[0]
        )
        self._stmt = None
        self._covered_types = []
        self._collect_bindings()

    def _collect_bindings(self):
        assignments = {}
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    for sub in ast.walk(target):
                        if isinstance(sub, ast.Name):
                            assignments.setdefault(sub.id, []).append(node)
        for name, nodes in assignments.items():
            node = nodes[0]
            if (
                len(nodes) == 1
                and isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                self.version_vars[name] = node.value
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        self.aliases[alias.asname] = self._rewrite(alias.name)
                    else:
                        root = alias.name.split(".")[0]
                        self.aliases[root] = root
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                module = self._rewrite(node.module)
                for alias in node.names:
                    if alias.name == "*":
                        self.star_namespaces.append(module)
                        continue
                    self.aliases[alias.asname or alias.name] = self._rewrite(
                        module + "." + alias.name
                    )
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                self.local_names.add(node.name)
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            self.own_attributes.add(item.name)
                        elif isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    self.own_attributes.add(target.id)
            elif isinstance(node, ast.Assign):
                probes = _is_feature_probe(node.value)
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.local_names.add(target.id)
                        if probes:
                            self.feature_vars.add(target.id)
                    elif (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        self.own_attributes.add(target.attr)
            elif isinstance(node, ast.arg):
                self.local_names.add(node.arg)

    @staticmethod
    def _rewrite(dotted):
        for prefix, target in REEXPORTED_NAMESPACES.items():
            if dotted == prefix or dotted.startswith(prefix + "."):
                return target + dotted[len(prefix) :]
        return dotted

    def qualified_name(self, node):
        """Fully qualified dotted name of a Name/Attribute chain, else None."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name):
            return None
        root = node.id
        if root in self.aliases:
            base = self.aliases[root]
        elif self.star_namespaces and root not in self.local_names:
            base = None
            for namespace in self.star_namespaces:
                candidate = namespace + "." + root
                if self.catalog.is_type(candidate) or self.catalog.namespace_entry(
                    candidate
                ):
                    base = candidate
                    break
            if base is None:
                return None
        else:
            return None
        full = self._rewrite(".".join([base] + list(reversed(parts))))
        if not full.startswith(API_ROOTS):
            return None
        return full

    def run(self):
        """Analyze the module and return its findings."""
        if not self.base_years:
            return self.findings
        self._visit_block(self.tree.body, _Ctx(self.base_years, False))
        return self.findings

    def _visit_block(self, statements, ctx):
        for stmt in statements:
            self._visit_stmt(stmt, ctx)
            ctx = self._after(stmt, ctx)

    def _after(self, stmt, ctx):
        if _is_failed_attempt_fallthrough(stmt):
            return ctx.guard()
        if not isinstance(stmt, ast.If):
            return ctx
        cond = self.condition(stmt.test, ctx)
        body_exits = _terminates(stmt.body)
        else_exits = bool(stmt.orelse) and _terminates(stmt.orelse)
        if body_exits and not else_exits:
            return ctx.narrow(cond.false, cond.feature)
        if else_exits and not body_exits:
            return ctx.narrow(cond.true, cond.feature)
        return ctx

    def _visit_stmt(self, stmt, ctx):
        previous = self._stmt
        self._stmt = stmt
        try:
            if isinstance(stmt, (ast.If, ast.While)):
                self._visit_expr(stmt.test, ctx)
                cond = self.condition(stmt.test, ctx)
                ironpython_branch = _ironpython_only_branch(stmt.test)
                body_ctx = ctx.narrow(cond.true, cond.feature)
                else_ctx = ctx.narrow(cond.false, cond.feature)
                if ironpython_branch is True:
                    body_ctx = body_ctx.ironpython()
                elif ironpython_branch is False:
                    else_ctx = else_ctx.ironpython()
                self._visit_block(stmt.body, body_ctx)
                self._visit_block(stmt.orelse, else_ctx)
            elif isinstance(stmt, ast.Try) or type(stmt).__name__ == "TryStar":
                guarded = _handlers_guard(stmt.handlers)
                inner = ctx.guard() if guarded else ctx
                self._visit_block(stmt.body, inner)
                for handler in stmt.handlers:
                    if handler.type is not None:
                        self._visit_expr(handler.type, ctx)
                    self._visit_block(handler.body, inner)
                self._visit_block(stmt.orelse, ctx)
                self._visit_block(stmt.finalbody, ctx)
            elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
                self._check_import(stmt, ctx)
            else:
                for _, value in ast.iter_fields(stmt):
                    if isinstance(value, list):
                        if value and isinstance(value[0], ast.stmt):
                            self._visit_block(value, ctx)
                        else:
                            for item in value:
                                self._visit_any(item, ctx)
                    else:
                        self._visit_any(value, ctx)
        finally:
            self._stmt = previous

    def _visit_any(self, value, ctx):
        if isinstance(value, ast.expr):
            self._visit_expr(value, ctx)
        elif isinstance(value, ast.AST):
            for _, child in ast.iter_fields(value):
                if isinstance(child, list):
                    for item in child:
                        if isinstance(item, ast.stmt):
                            self._visit_stmt(item, ctx)
                        else:
                            self._visit_any(item, ctx)
                else:
                    self._visit_any(child, ctx)

    def _visit_expr(self, node, ctx):
        if isinstance(node, ast.IfExp):
            self._visit_expr(node.test, ctx)
            cond = self.condition(node.test, ctx)
            self._visit_expr(node.body, ctx.narrow(cond.true, cond.feature))
            self._visit_expr(node.orelse, ctx.narrow(cond.false, cond.feature))
            return
        if isinstance(node, ast.BoolOp):
            current = ctx
            for value in node.values:
                self._visit_expr(value, current)
                cond = self.condition(value, current)
                if isinstance(node.op, ast.And):
                    current = current.narrow(cond.true, cond.feature)
                else:
                    current = current.narrow(cond.false, cond.feature)
            return
        if isinstance(node, ast.Attribute):
            full = self.qualified_name(node)
            if full is not None:
                self._check_qualified(node, full, ctx)
                return
            self._check_instance(node, node.attr, ctx)
            self._visit_expr(node.value, ctx)
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in self.aliases or self.star_namespaces:
                full = self.qualified_name(node)
                if full is not None and full not in DEFAULT_ALIASES.values():
                    self._check_qualified(node, full, ctx)
            return
        covered = self._check_call(node, ctx) if isinstance(node, ast.Call) else None
        if covered:
            self._covered_types.append(covered)
        try:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._visit_expr(child, ctx)
                elif isinstance(child, ast.AST):
                    self._visit_any(child, ctx)
        finally:
            if covered:
                self._covered_types.pop()

    def condition(self, node, ctx):
        """Classify a test expression's effect on the reachable years."""
        universe = ctx.years
        unknown = _Condition(universe, universe)
        if self.feature_vars and any(
            isinstance(n, ast.Name) and n.id in self.feature_vars
            for n in ast.walk(node)
        ):
            return _Condition(universe, universe, True)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            inner = self.condition(node.operand, ctx)
            return _Condition(inner.false, inner.true, inner.feature)
        if isinstance(node, ast.BoolOp):
            parts = [self.condition(v, ctx) for v in node.values]
            feature = any(p.feature for p in parts)
            if isinstance(node.op, ast.And):
                true = frozenset.intersection(*[p.true for p in parts])
                false = frozenset.union(*[p.false for p in parts])
            else:
                true = frozenset.union(*[p.true for p in parts])
                false = frozenset.intersection(*[p.false for p in parts])
            return _Condition(true, false, feature)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FEATURE_TEST_CALLS:
                return _Condition(universe, universe, True)
            if (
                isinstance(func, ast.Name)
                and func.id == "getattr"
                and len(node.args) >= 3
            ):
                return _Condition(universe, universe, True)
            if isinstance(func, ast.Attribute) and func.attr in HOST_VERSION_METHODS:
                return self._host_check(node, universe) or unknown
        if (
            isinstance(node, ast.Name)
            and node.id in self.version_vars
            and node.id not in self._resolving
        ):
            self._resolving.add(node.id)
            try:
                resolved = self.condition(self.version_vars[node.id], ctx)
            finally:
                self._resolving.discard(node.id)
            if resolved.true != universe or resolved.false != universe:
                return resolved
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = _terminal_name(node)
            if name in NETCORE_FLAGS:
                core = frozenset(y for y in universe if y >= NETCORE_FIRST_YEAR)
                framework = universe - core
                if NETCORE_FLAGS[name]:
                    return _Condition(core, framework)
                return _Condition(framework, core)
        if isinstance(node, ast.Compare):
            return self._compare(node, universe) or unknown
        return unknown

    @staticmethod
    def _host_check(node, universe):
        if not node.args:
            return None
        year = _year_literal(node.args[0])
        if year is None:
            return None
        method = node.func.attr
        if method == "is_newer_than":
            or_equal = False
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                or_equal = bool(node.args[1].value)
            for keyword in node.keywords:
                if keyword.arg == "or_equal" and isinstance(
                    keyword.value, ast.Constant
                ):
                    or_equal = bool(keyword.value.value)
            true = frozenset(
                y for y in universe if y > year or (or_equal and y == year)
            )
        elif method == "is_older_than":
            true = frozenset(y for y in universe if y < year)
        else:
            true = frozenset(y for y in universe if y == year)
        return _Condition(true, universe - true)

    @staticmethod
    def _compare(node, universe):
        operands = [node.left] + list(node.comparators)
        true = universe
        matched = False
        for left, op, right in zip(operands, node.ops, operands[1:]):
            if isinstance(op, (ast.In, ast.NotIn)) and _is_version_value(left):
                if isinstance(right, (ast.Tuple, ast.List, ast.Set)):
                    members = {_year_literal(e) for e in right.elts}
                    if None in members:
                        return None
                    years = frozenset(y for y in universe if y in members)
                    if isinstance(op, ast.NotIn):
                        years = universe - years
                    true = true & years
                    matched = True
                    continue
                return None
            if _is_version_value(left) and _year_literal(right) is not None:
                years = _compare_years(op, _year_literal(right), universe)
            elif _is_version_value(right) and _year_literal(left) is not None:
                flipped = _FLIPPED.get(type(op), type(op))()
                years = _compare_years(flipped, _year_literal(left), universe)
            else:
                return None
            if years is None:
                return None
            true = true & years
            matched = True
        if not matched:
            return None
        return _Condition(true, universe - true)

    def _report(self, node, code, severity, message, fix, years=None):
        finding = Finding(
            self.path,
            getattr(node, "lineno", 1),
            getattr(node, "col_offset", 0) + 1,
            code,
            severity,
            message,
            fix,
            years,
        )
        if self._stmt is not None:
            finding.stmt_span = _header_span(self._stmt)
        self.findings.append(finding)

    def _evaluate(self, node, label, entry, ctx, code="API-MISSING", parent=None):
        """Report an entry's missing or deprecated years against ctx.

        Returns True when something was reported.
        """
        if ctx.guarded:
            return False
        avail = self.catalog.avail(entry)
        missing = ctx.years - avail
        partial = self.catalog.partial(entry) & missing
        tier = entry.get("tier") or (parent or {}).get("tier")
        if missing:
            severity = tier or ERROR
            self._report(
                node,
                code,
                severity,
                "{} {}".format(label, _describe_missing(missing, avail, partial)),
                self._fix(entry, missing, avail, parent, partial=partial),
                missing,
            )
            return True
        deprecated = ctx.years & self.catalog.obsolete_years(entry)
        if deprecated and ctx.years == self.base_years:
            obsolete = entry.get("obsolete") or {}
            note = obsolete.get("message") or ""
            self._report(
                node,
                "API-DEPRECATED",
                WARNING,
                "{} is deprecated in Revit {}{}".format(
                    label,
                    format_years(deprecated),
                    " ({})".format(_first_sentence_after(note, "deprecated"))
                    if note
                    else "",
                ),
                self._fix(entry, frozenset(), avail, parent, note),
                deprecated,
            )
            return True
        return False

    def _fix(self, entry, missing, avail, parent=None, note="", partial=frozenset()):
        hints = []
        curated = entry.get("fix") or (parent or {}).get("fix")
        if curated:
            hints.append(curated)
        elif note:
            replacement = _replacement_from_message(note)
            if replacement:
                hints.append("use {}".format(replacement))
        if missing:
            removed = min(missing) > max(avail) if avail else False
            added = max(missing) < min(avail) if avail else False
            if removed:
                first_missing = min(missing)
                hints.append(
                    "guard with `if HOST_APP.is_older_than({}):`".format(first_missing)
                )
                if self.in_bundle:
                    hints.append(
                        "or cap the bundle with `max_revit_version: {}`".format(
                            first_missing - 1
                        )
                    )
            elif added:
                first_available = min(avail)
                hints.append(
                    "guard with `if HOST_APP.is_newer_than({}, or_equal=True):`".format(
                        first_available
                    )
                )
                if self.in_bundle:
                    hints.append(
                        "or require it with `min_revit_version: {}`".format(
                            first_available
                        )
                    )
            elif avail:
                hints.append(
                    "guard the use with a HOST_APP version check (available in "
                    "Revit {})".format(format_years(avail))
                )
            else:
                hints.append("this API is not available in any cataloged Revit")
        if partial:
            hints.append(
                "only some Revit {} updates have it and a HOST_APP year check "
                "cannot tell updates apart, so use `hasattr(...)` feature "
                "detection there".format(format_years(partial))
            )
        return "; ".join(hints)

    def _check_qualified(self, node, full, ctx):
        """Check a fully qualified reference; returns True if it reported."""
        namespace = self.catalog.namespace_entry(full)
        if namespace is not None:
            name, entry = namespace
            return self._evaluate(
                node, "`{}`".format(name), entry, ctx, entry.get("code", "DOTNET")
            )
        split = self.catalog.split_qualified(full)
        if split is None:
            return False
        type_name, member, rest = split
        if any(type_name in covered for covered in self._covered_types):
            return False
        type_entry = self.catalog.types[type_name]
        code = type_entry.get("code", "API-MISSING")
        short = _short(type_name)
        if not ctx.guarded:
            missing = ctx.years - self.catalog.avail(type_entry)
            if missing or member is None:
                if self._evaluate(node, "`{}`".format(short), type_entry, ctx, code):
                    return True
        if member is not None:
            member_entry, owner_entry = self.catalog.member_entry(type_name, member)
            if member_entry is not None:
                if self._evaluate(
                    node,
                    "`{}.{}`".format(short, member),
                    member_entry,
                    ctx,
                    member_entry.get("code", code),
                    owner_entry,
                ):
                    return True
            elif self._evaluate(node, "`{}`".format(short), type_entry, ctx, code):
                return True
        for attr in rest:
            self._check_instance(node, attr, ctx)
        return False

    def _check_instance(self, node, attr, ctx, receiver=None):
        if attr in self.own_attributes:
            return
        entry = self.catalog.instance_members.get(attr)
        if not entry or entry.get("match") is False:
            return
        if entry.get("bcl") and entry.get("match") is not True:
            return
        if receiver is None and isinstance(node, ast.Attribute):
            receiver = node.value
        if receiver is not None:
            if _terminal_name(receiver) == "self":
                return
            exempt = entry.get("receiver_exempt")
            if exempt and re.search(exempt, ast.unparse(receiver)):
                return
        self._evaluate(
            node, "`.{}`".format(attr), entry, ctx, entry.get("code", "API-MISSING")
        )

    def _check_call(self, node, ctx):
        """Check getattr-by-name and removed overloads.

        Returns:
            (set): Revit type names already reported as overload arguments,
            so the argument's own type finding is not repeated.
        """
        func = node.func
        if isinstance(func, ast.Name) and func.id == "getattr" and len(node.args) == 2:
            name = node.args[1]
            if isinstance(name, ast.Constant) and isinstance(name.value, str):
                self._check_instance(node, name.value, ctx, node.args[0])
            return None
        if not isinstance(func, ast.Attribute):
            return None
        arg_types = self._argument_types(node)
        if not arg_types:
            return None
        full = self.qualified_name(func)
        if full is not None:
            split = self.catalog.split_qualified(full)
            if split is None or split[1] is None:
                return None
            type_entry = self.catalog.types[split[0]]
            entry = type_entry.get("members", {}).get(split[1], {})
            label = "{}.{}".format(_short(split[0]), split[1])
        else:
            entry = self.catalog.instance_members.get(func.attr, {})
            if entry.get("match") is False:
                return None
            label = ".{}".format(func.attr)
        params = entry.get("overload_params", {})
        covered = set()
        for arg_type in sorted(arg_types):
            if arg_type not in params:
                continue
            type_fix = self.catalog.types.get(arg_type, {}).get("fix")
            synthetic = {"avail": params[arg_type], "fix": entry.get("fix") or type_fix}
            if self._evaluate(
                node,
                "`{}(...)` overload taking `{}`".format(label, _short(arg_type)),
                synthetic,
                ctx,
                "API-OVERLOAD",
            ):
                covered.add(arg_type)
        return covered

    def _argument_types(self, call):
        types = set()
        values = list(call.args) + [k.value for k in call.keywords]
        for value in values:
            for sub in ast.walk(value):
                if isinstance(sub, (ast.Attribute, ast.Name)):
                    full = self.qualified_name(sub)
                    if full is None:
                        continue
                    split = self.catalog.split_qualified(full)
                    if split is not None:
                        types.add(split[0])
        return types

    def _check_import(self, stmt, ctx):
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if self.is_cpython and alias.name.split(".")[0] in (
                    self.catalog.cpython_unavailable_modules
                ):
                    self._engine_finding(stmt, alias.name, ctx)
                full = self._rewrite(alias.name)
                if full.startswith(API_ROOTS):
                    self._check_qualified(stmt, full, ctx)
            return
        if not stmt.module or stmt.level:
            return
        if self.is_cpython and stmt.module.split(".")[0] in (
            self.catalog.cpython_unavailable_modules
        ):
            self._engine_finding(stmt, stmt.module, ctx)
        module = self._rewrite(stmt.module)
        if not module.startswith(API_ROOTS):
            return
        if self._check_qualified(stmt, module, ctx):
            return
        for alias in stmt.names:
            if alias.name != "*":
                self._check_qualified(stmt, module + "." + alias.name, ctx)

    def _engine_finding(self, stmt, module, ctx):
        if ctx.guarded or ctx.ironpython_only:
            return
        fix = self.catalog.cpython_unavailable_modules.get(module.split(".")[0], "")
        self._report(
            stmt,
            "ENGINE",
            ERROR,
            "`{}` is IronPython-only but this script runs on CPython "
            "(#! python3)".format(module),
            fix,
        )


class _Ctx:
    """Reachable Revit years, feature-guard state and engine reachability."""

    __slots__ = ("years", "guarded", "ironpython_only")

    def __init__(self, years, guarded, ironpython_only=False):
        self.years = years
        self.guarded = guarded
        self.ironpython_only = ironpython_only

    def narrow(self, years, feature=False):
        """Context restricted to years, guarded if this test probes features."""
        return _Ctx(self.years & years, self.guarded or feature, self.ironpython_only)

    def guard(self):
        """Context inside a feature guard or fallback."""
        return _Ctx(self.years, True, self.ironpython_only)

    def ironpython(self):
        """Context only reachable on an IronPython engine."""
        return _Ctx(self.years, self.guarded, True)


IRONPYTHON_FLAGS = {"IRONPY", "IRONPY2", "IRONPY3", "PY2"}


def _ironpython_only_branch(test):
    """True if a test's body runs only on IronPython, False for its else."""
    negated = False
    while isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        negated = not negated
        test = test.operand
    if _terminal_name(test) in IRONPYTHON_FLAGS and isinstance(
        test, (ast.Name, ast.Attribute)
    ):
        return not negated
    return None


def _short(full_name):
    for prefix in ("Autodesk.Revit.DB.", "Autodesk.Revit.UI.", "Autodesk.Revit."):
        if full_name.startswith(prefix):
            return full_name[len(prefix) :]
    return full_name


def _describe_missing(missing, avail, partial=frozenset()):
    """Phrase the missing years; ``partial`` years exist in some updates only."""
    if not avail:
        if partial:
            return "exists only in some updates of Revit {}".format(
                format_years(partial)
            )
        return "does not exist in any cataloged Revit"
    if min(missing) > max(avail):
        if min(missing) in partial:
            return "was removed during Revit {} (its later updates lack it)".format(
                min(missing)
            )
        return "was removed in Revit {} (exists up to {})".format(
            min(missing), max(avail)
        )
    if max(missing) < min(avail):
        if max(missing) in partial:
            return (
                "was added in a Revit {} update (earlier updates lack it), "
                "missing in Revit {}".format(max(missing), format_years(missing))
            )
        return "was added in Revit {}, missing in Revit {}".format(
            min(avail), format_years(missing)
        )
    text = "is missing in Revit {}".format(format_years(missing))
    if partial:
        text += " (Revit {} has it in some updates only)".format(format_years(partial))
    return text


def _first_sentence_after(message, keyword):
    sentence = message.split(". ")
    for part in sentence:
        if keyword in part.lower():
            continue
        return part.strip().rstrip(".")
    return sentence[0].strip().rstrip(".")


_REPLACEMENT_RE = re.compile(
    r"(?i)(?:please\s+)?use\s+(?:the\s+)?(.+?)(?:\s+instead|\.\s|\.$|$)"
)


def _replacement_from_message(message):
    match = _REPLACEMENT_RE.search(message or "")
    return match.group(1).strip().rstrip(".") if match else ""


def _is_exit_call(node):
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    name = _terminal_name(call.func)
    if name in EXIT_CALL_NAMES:
        return True
    for keyword in call.keywords:
        if (
            keyword.arg == "exitscript"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
        ):
            return True
    return False


def _terminates(statements):
    if not statements:
        return False
    last = statements[-1]
    return isinstance(last, (ast.Return, ast.Raise, ast.Continue, ast.Break)) or (
        _is_exit_call(last)
    )


def _is_feature_probe(node):
    """True for ``hasattr(...)`` or ``getattr(obj, name, default)`` calls."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return False
    if node.func.id in FEATURE_TEST_CALLS:
        return True
    return node.func.id == "getattr" and len(node.args) >= 3


def _is_failed_attempt_fallthrough(stmt):
    """True when code after stmt runs only because a guarded attempt failed.

    That is a ``try`` that returns on success and swallows the failure, or an
    ``if``/``else`` whose every branch either returns or is such an attempt.
    """
    if isinstance(stmt, ast.Try):
        return (
            _handlers_guard(stmt.handlers)
            and _terminates(stmt.body)
            and not all(_terminates(h.body) for h in stmt.handlers)
        )
    if isinstance(stmt, ast.If) and stmt.body and stmt.orelse:
        branches = [stmt.body, stmt.orelse]
        attempts = [_is_failed_attempt_fallthrough(b[-1]) for b in branches]
        return any(attempts) and all(
            attempt or _terminates(branch)
            for attempt, branch in zip(attempts, branches)
        )
    return False


def _handlers_guard(handlers):
    for handler in handlers:
        if handler.type is None:
            return True
        names = {
            _terminal_name(n)
            for n in ast.walk(handler.type)
            if isinstance(n, (ast.Name, ast.Attribute))
        }
        if names & GUARDING_EXCEPTIONS:
            return True
    return False


def _header_span(stmt):
    """Return the line span a suppression pragma may sit on for a statement.

    That is all of a simple statement, or the header (up to the body) of a
    compound one, so formatter reflows of long headers keep the pragma
    attached.
    """
    end = getattr(stmt, "end_lineno", None) or stmt.lineno
    body = getattr(stmt, "body", None)
    if isinstance(body, list) and body and isinstance(body[0], ast.stmt):
        end = max(stmt.lineno, body[0].lineno - 1)
    return stmt.lineno, end


def _read_comments(source):
    comments = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return comments


def apply_suppressions(path, source, findings):
    """Drop suppressed findings; add findings for invalid or unused pragmas."""
    pragmas = {}
    extra = []
    for line, text in _read_comments(source).items():
        match = SUPPRESS_RE.search(text)
        if not match:
            continue
        reason = (match.group("reason") or "").strip()
        ids = {i.strip() for i in (match.group("ids") or "").split(",") if i.strip()}
        if not reason:
            extra.append(
                Finding(
                    path,
                    line,
                    1,
                    "SUPPRESS",
                    ERROR,
                    "`# compat-ignore` needs a justification: "
                    "`# compat-ignore: <why this is safe>`",
                )
            )
            continue
        pragmas[line] = {"ids": ids, "used": False}
    kept = []
    for finding in findings:
        suppressed = False
        first, last = finding.stmt_span
        candidates = [finding.line] + list(range(first, last + 1))
        for line in candidates:
            pragma = pragmas.get(line)
            if pragma and (not pragma["ids"] or finding.code in pragma["ids"]):
                pragma["used"] = True
                suppressed = True
                break
        if not suppressed:
            kept.append(finding)
    for line, pragma in sorted(pragmas.items()):
        if not pragma["used"]:
            extra.append(
                Finding(
                    path,
                    line,
                    1,
                    "SUPPRESS",
                    WARNING,
                    "unused `# compat-ignore`; remove it",
                )
            )
    return kept + extra


def check_file(path, catalog, bundles):
    """Return findings for one Python file."""
    try:
        with tokenize.open(path) as handle:
            source = handle.read()
    except (OSError, SyntaxError, UnicodeDecodeError) as err:
        return [Finding(path, 1, 1, "PARSE", WARNING, "cannot read: {}".format(err))]
    years, reasons = bundles.years_for(path)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(source, filename=str(path))
    except SyntaxError as err:
        cpython = (
            source.lstrip("﻿").startswith("#!")
            and "python3" in (source.splitlines() or [""])[0]
        )
        return [
            Finding(
                path,
                err.lineno or 1,
                1,
                "PARSE",
                ERROR if cpython else WARNING,
                "not analyzed: does not parse as Python 3 ({}){}".format(
                    err.msg,
                    ""
                    if cpython
                    else "; run check_py3_compat.py for the language axis",
                ),
            )
        ]
    analyzer = FileAnalyzer(path, source, tree, catalog, years, reasons)
    return apply_suppressions(path, source, analyzer.run())


def iter_python_files(roots, excludes=()):
    """Yield .py files under roots; raises FileNotFoundError on a bad root."""
    for root in roots:
        if not root.exists():
            raise FileNotFoundError("path does not exist: {}".format(root))
        if root.is_file():
            yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
            for filename in sorted(filenames):
                if not filename.endswith(".py"):
                    continue
                path = Path(dirpath) / filename
                posix = path.as_posix()
                if any(fnmatch.fnmatch(posix, pattern) for pattern in excludes):
                    continue
                yield path


def lint_paths(roots, catalog, universe=None, excludes=()):
    """Lint files under roots; returns (findings, scanned file count)."""
    bundles = BundleRanges(universe or catalog.universe)
    findings = []
    count = 0
    for path in iter_python_files(roots, excludes):
        count += 1
        findings.extend(check_file(path, catalog, bundles))
    findings.extend(bundles.problems)
    return findings, count


def clone_repo(url, destination, ref=None):
    """Shallow-clone a repository without prompts, hooks or submodules.

    The checkout is only parsed, never executed.
    """
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="echo")
    command = [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "core.longpaths=true",
        "clone",
        "--depth",
        "1",
        "--quiet",
    ]
    if ref:
        command += ["--branch", ref]
    command += ["--", url, str(destination)]
    subprocess.run(command, check=True, env=env, timeout=600, capture_output=True)


def _remove_tree(path):
    """Delete a directory tree, including git's read-only object files."""

    def _make_writable_and_retry(func, target, _):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_make_writable_and_retry)
    else:
        shutil.rmtree(path, onerror=_make_writable_and_retry)


def _clone_dir_name(name):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._") or "repo"
    return safe if safe.endswith(".extension") else safe + ".extension"


def _print_text(groups, show_fix=True):
    for label, findings, base in groups:
        if label:
            print("\n== {} ==".format(label))
        by_file = {}
        for finding in findings:
            by_file.setdefault(finding.shown_path(base), []).append(finding)
        for shown in sorted(by_file):
            print("\n{}".format(shown))
            for finding in sorted(
                by_file[shown], key=lambda f: (f.line, f.col, f.code)
            ):
                print(
                    "  {}:{}  {:<7} {:<14} {}".format(
                        finding.line,
                        finding.col,
                        finding.severity,
                        finding.code,
                        finding.message,
                    )
                )
                if show_fix and finding.fix:
                    print("        fix: {}".format(finding.fix))


def _print_github(findings, base):
    for finding in findings:
        level = "error" if finding.severity == ERROR else "warning"
        message = finding.message + (" | fix: " + finding.fix if finding.fix else "")
        print(
            "::{} file={},line={},col={},title={}::{}".format(
                level,
                finding.shown_path(base),
                finding.line,
                finding.col,
                finding.code,
                message.replace("%", "%25").replace("\n", "%0A"),
            )
        )


def _parse_year_range(text):
    match = re.fullmatch(r"(\d{4})(?:-(\d{4}))?", text.strip())
    if not match:
        raise argparse.ArgumentTypeError("expected YEAR or YEAR-YEAR, got " + text)
    first = int(match.group(1))
    last = int(match.group(2) or first)
    if last < first:
        raise argparse.ArgumentTypeError("empty year range " + text)
    return frozenset(range(first, last + 1))


def _fingerprint(finding, base):
    return (finding.shown_path(base), finding.code, finding.message)


def load_baseline(path):
    """Return {(path, code, message): count} from a baseline file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    counts = {}
    for item in data.get("findings", []):
        key = (item["path"], item["code"], item["message"])
        counts[key] = counts.get(key, 0) + int(item.get("count", 1))
    return counts


def write_baseline(path, findings_with_base):
    """Write the given (finding, base) pairs as the new baseline."""
    counts = {}
    for finding, base in findings_with_base:
        key = _fingerprint(finding, base)
        counts[key] = counts.get(key, 0) + 1
    items = [
        {"path": k[0], "code": k[1], "message": k[2], "count": v}
        for k, v in sorted(counts.items())
    ]
    payload = {
        "about": "Known findings of check_revit_api_compat.py, accepted so CI "
        "fails only on new ones. Fix an entry, then run with "
        "--update-baseline to drop it; never add entries by hand.",
        "findings": items,
    }
    Path(path).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")


def apply_baseline(findings, base, remaining):
    """Drop findings covered by ``remaining`` counts (mutated in place)."""
    kept = []
    for finding in findings:
        key = _fingerprint(finding, base)
        if remaining.get(key, 0) > 0:
            remaining[key] -= 1
        else:
            kept.append(finding)
    return kept


def _summarize(findings):
    errors = sum(1 for f in findings if f.severity == ERROR)
    return errors, len(findings) - errors


def main(argv=None):
    """Run the checker CLI and return its process exit code."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="files/directories to lint (default: {})".format(
            ", ".join(DEFAULT_SCAN_ROOTS)
        ),
    )
    parser.add_argument(
        "--extensions",
        choices=["all"],
        help="clone and lint every extension in extensions/extensions.json",
    )
    parser.add_argument(
        "--git-url",
        action="append",
        default=[],
        metavar="URL",
        help="clone a repository to a temp dir and lint it (repeatable)",
    )
    parser.add_argument("--git-ref", help="branch or tag to clone with --git-url")
    parser.add_argument(
        "--revit-years",
        type=_parse_year_range,
        metavar="YEAR[-YEAR]",
        help="Revit years an unconstrained script must support "
        "(default: every cataloged year)",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="GLOB", help="skip files"
    )
    parser.add_argument("--format", choices=["text", "json", "github"], default="text")
    parser.add_argument(
        "--strict", action="store_true", help="fail on warnings as well as errors"
    )
    parser.add_argument(
        "--errors-only", action="store_true", help="hide warnings from the report"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        nargs="?",
        const=BASELINE_PATH,
        help="ignore findings recorded in this baseline (default file: "
        "revit_api_catalog/baseline.json)",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="rewrite the --baseline file from the current findings and exit 0",
    )
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--overrides", type=Path, default=OVERRIDES_PATH)
    parser.add_argument(
        "--keep-clones", type=Path, help="clone into this directory and keep it"
    )
    args = parser.parse_args(argv)

    try:
        catalog = Catalog.load(args.catalog, args.overrides)
    except (OSError, ValueError) as err:
        print("error: cannot load catalog: {}".format(err), file=sys.stderr)
        return 2
    universe = catalog.universe
    if args.revit_years:
        universe = args.revit_years & catalog.universe
        if not universe:
            print("error: --revit-years is outside the catalog", file=sys.stderr)
            return 2

    targets = []
    for path in args.paths:
        targets.append(
            (None, [path if path.is_absolute() else Path.cwd() / path], None)
        )
    remote = []
    if args.extensions == "all":
        try:
            entries = json.loads(EXTENSIONS_CATALOG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            print(
                "error: cannot read extension catalog: {}".format(err), file=sys.stderr
            )
            return 2
        for entry in entries.get("extensions", []):
            if entry.get("url") and entry.get("type", "extension") == "extension":
                remote.append((entry.get("name") or entry["url"], entry["url"], None))
    for url in args.git_url:
        remote.append(
            (url.rstrip("/").split("/")[-1].removesuffix(".git"), url, args.git_ref)
        )
    if not targets and not remote:
        targets.append((None, [REPO_ROOT / p for p in DEFAULT_SCAN_ROOTS], REPO_ROOT))

    clone_root = None
    failures = []
    if remote:
        if args.keep_clones:
            clone_root = args.keep_clones
            clone_root.mkdir(parents=True, exist_ok=True)
        else:
            clone_root = Path(tempfile.mkdtemp(prefix="revit-api-compat-"))
        for name, url, ref in remote:
            destination = clone_root / _clone_dir_name(name)
            if destination.exists():
                _remove_tree(destination)
            print("cloning {} ...".format(url), file=sys.stderr)
            try:
                clone_repo(url, destination, ref)
            except (subprocess.SubprocessError, OSError) as err:
                detail = getattr(err, "stderr", b"") or b""
                failures.append(
                    (name, url, detail.decode(errors="replace").strip() or str(err))
                )
                continue
            targets.append((name, [destination], destination))

    baseline = None
    if args.update_baseline and not args.baseline:
        print("error: --update-baseline needs --baseline", file=sys.stderr)
        return 2
    if args.baseline and not args.update_baseline:
        try:
            baseline = load_baseline(args.baseline)
        except (OSError, ValueError, KeyError) as err:
            print("error: cannot load baseline: {}".format(err), file=sys.stderr)
            return 2

    groups = []
    all_findings = []
    raw = []
    file_count = 0
    try:
        for label, roots, base in targets:
            findings, count = lint_paths(roots, catalog, universe, args.exclude)
            raw.extend((f, base) for f in findings)
            if baseline is not None:
                findings = apply_baseline(findings, base, baseline)
            if args.errors_only:
                findings = [f for f in findings if f.severity == ERROR]
            file_count += count
            groups.append((label, findings, base, count))
            all_findings.extend(findings)
    except FileNotFoundError as err:
        print("error: {}".format(err), file=sys.stderr)
        return 2
    finally:
        if clone_root is not None and not args.keep_clones:
            _remove_tree(clone_root)

    if args.update_baseline:
        write_baseline(args.baseline, raw)
        print(
            "wrote {} with {} finding(s)".format(args.baseline, len(raw)),
            file=sys.stderr,
        )
        return 0

    if args.format == "json":
        print(
            json.dumps(
                {
                    "catalog_years": catalog.years,
                    "targets": [
                        {
                            "name": label,
                            "files": count,
                            "findings": [f.as_dict(base) for f in findings],
                        }
                        for label, findings, base, count in groups
                    ],
                    "clone_failures": [
                        {"name": n, "url": u, "error": e} for n, u, e in failures
                    ],
                },
                indent=1,
            )
        )
    elif args.format == "github":
        for _, findings, base, _ in groups:
            _print_github(findings, base)
    else:
        _print_text([(label, findings, base) for label, findings, base, _ in groups])

    for name, url, error in failures:
        print("clone failed: {} ({}): {}".format(name, url, error), file=sys.stderr)
    if file_count == 0 and not failures:
        print("error: scanned 0 files", file=sys.stderr)
        return 2

    errors, warns = _summarize(all_findings)
    stale = sum(baseline.values()) if baseline else 0
    if stale:
        print(
            "note: {} baselined finding(s) no longer occur; run with "
            "--update-baseline to drop them".format(stale),
            file=sys.stderr,
        )
    if len(groups) > 1:
        print("", file=sys.stderr)
        for label, findings, _, count in groups:
            e, w = _summarize(findings)
            print(
                "  {:<40} {:>5} files  {:>4} errors  {:>4} warnings".format(
                    label or "(paths)", count, e, w
                ),
                file=sys.stderr,
            )
    print(
        "\nscanned {} files across Revit {}; {} error(s), {} warning(s)".format(
            file_count, format_years(universe), errors, warns
        ),
        file=sys.stderr,
    )
    if errors or (args.strict and warns):
        return 1
    if failures and not groups:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
