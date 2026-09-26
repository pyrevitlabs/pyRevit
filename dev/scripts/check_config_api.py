r"""Static checker for the Python config API naming contract.

Enforces the contract documented in ``docs/config-api.md`` (issue #3645)
against the source tree, so the decisions recorded there cannot drift:

* the canonical spelling on a typed section is the PascalCase C# property
  name, so every flat alias must resolve to a property the section schema
  actually declares;
* the flat aliases are a frozen set - no additions, no removals - and each
  one must stay a statically declared property, which is what keeps it
  visible to autocomplete, hover documentation, and LSP-based tooling;
* the escape hatches for anything outside the typed schema stay declared;
* no snake_case/PascalCase translation layer is introduced, because that
  would mint a second spelling for every setting.

Nothing here imports pyrevit: the check is pure source analysis so it runs
under CPython 3.9 or newer - `ast.unparse` sets that floor - and needs no
Revit, no labs assemblies, and no user config.

Usage::

    pipenv run check-config-api
    pipenv run check-config-api --census

Exit code is nonzero when findings exist.

Check codes:
    SCHEMA-MISSING   a typed section the contract names has no C# schema, so
                     the alias targets cannot be validated at all
    ALIAS-SCHEMA     a flat alias points at a property the section schema does
                     not declare; the wrapper falls back to a raw option, so
                     this degrades to a runtime failure or a stray key rather
                     than a build failure
    ALIAS-RENAME     a flat alias whose target is not mechanically derivable
                     and is not one of the documented renames
    ALIAS-NEW        a flat alias the contract does not list
    ALIAS-GONE       a documented flat alias that is no longer declared
    ALIAS-DYNAMIC    a documented flat alias no longer statically declared, so
                     it can only resolve through dynamic dispatch
    SECTION-DYNAMIC  a typed-section accessor no longer statically declared
    ESCAPE-HATCH     a documented escape-hatch method is missing
    NAMING-TRANSLATOR a snake_case/PascalCase mapping table or conversion
                     helper has appeared in the config bridge
    SECTION-SNAKE    a first-party call site uses a snake_case attribute on a
                     typed section, which silently stores a raw option instead
                     of setting the typed property
"""

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

USERCONFIG_REL = "pyrevitlib/pyrevit/userconfig.py"
CONFIGPARSER_REL = "pyrevitlib/pyrevit/coreutils/configparser.py"
SECTIONS_REL = "dev/pyRevitLabs/pyRevitLabs.Configurations/Sections"

TYPED_SECTIONS = ("core", "routes", "telemetry")

SECTION_ACCESSORS = ("core", "routes", "telemetry", "environment")

IDENTITY_PROPERTIES = ("config_service", "is_readonly")

SECTION_MEMBER_EXEMPT = ("get_option", "set_option", "has_option", "remove_option")

BARE_DELEGATIONS = {
    "apptelemetry_event_flags": ("telemetry", "AppTelemetryEventFlags"),
    "apptelemetry_server_url": ("telemetry", "AppTelemetryServerUrl"),
    "apptelemetry_status": ("telemetry", "AppTelemetryStatus"),
    "auto_update": ("core", "AutoUpdate"),
    "bin_cache": ("core", "BinCache"),
    "check_updates": ("core", "CheckUpdates"),
    "colorize_docs": ("core", "ColorizeDocs"),
    "cpython_engine_version": ("core", "CpythonEngineVersion"),
    "file_logging": ("core", "FileLogging"),
    "load_beta": ("core", "LoadBeta"),
    "load_core_api": ("routes", "LoadCoreApi"),
    "min_host_drivefreespace": ("core", "MinHostDriveFreeSpace"),
    "output_close_others": ("core", "CloseOtherOutputs"),
    "output_stylesheet": ("core", "OutputStyleSheet"),
    "read_script_metadata": ("core", "ReadScriptMetadata"),
    "required_host_build": ("core", "RequiredHostBuild"),
    "rocket_mode": ("core", "RocketMode"),
    "routes_host": ("routes", "Host"),
    "routes_port": ("routes", "Port"),
    "routes_server": ("routes", "Status"),
    "startuplog_timeout": ("core", "StartupLogTimeout"),
    "telemetry_file_dir": ("telemetry", "TelemetryFileDir"),
    "telemetry_include_hooks": ("telemetry", "TelemetryIncludeHooks"),
    "telemetry_server_url": ("telemetry", "TelemetryServerUrl"),
    "telemetry_status": ("telemetry", "TelemetryStatus"),
    "telemetry_utc_timestamp": ("telemetry", "TelemetryUseUtcTimeStamps"),
    "tooltip_debug_info": ("core", "TooltipDebugInfo"),
    "user_can_config": ("core", "UserCanConfig"),
    "user_can_extend": ("core", "UserCanExtend"),
    "user_can_update": ("core", "UserCanUpdate"),
    "user_locale": ("core", "UserLocale"),
}

SECTION_DERIVED_ALIASES = ("log_level", "output_close_mode_enum")

NON_SECTION_ALIASES = ("config_file", "config_type")

FLAT_ALIASES = (
    frozenset(BARE_DELEGATIONS)
    | set(SECTION_DERIVED_ALIASES)
    | set(NON_SECTION_ALIASES)
)

RENAMED_ALIASES = frozenset(
    {
        "apptelemetry_event_flags",
        "apptelemetry_server_url",
        "apptelemetry_status",
        "min_host_drivefreespace",
        "output_close_others",
        "output_stylesheet",
        "routes_host",
        "routes_port",
        "routes_server",
        "startuplog_timeout",
        "telemetry_utc_timestamp",
    }
)

ESCAPE_HATCHES = (
    (
        USERCONFIG_REL,
        "PyRevitConfig",
        ("get_section", "add_section", "has_section", "remove_section"),
    ),
    (
        USERCONFIG_REL,
        "_SectionCompatWrapper",
        ("get_option", "set_option", "has_option", "remove_option"),
    ),
    (
        CONFIGPARSER_REL,
        "ConfigSection",
        (
            "get_option",
            "set_option",
            "has_option",
            "remove_option",
            "add_subsection",
            "get_subsections",
            "get_subsection",
            "has_subsection",
        ),
    ),
)

DEFAULT_SCAN_ROOTS = ["pyrevitlib/pyrevit", "extensions"]

EXCLUDED_DIRS = (
    "pyrevitlib/pyrevit/coreutils/markdown",
    "pyrevitlib/rpw",
    "pyrevitlib/rjm",
    "pyrevitlib/rpws",
    "pyrevitlib/rsparam",
    "dev/modules",
    "site-packages",
)

_SECTION_NAME_RE = re.compile(r'\[SectionName\("(?P<name>\w+)"\)\]')
_PROPERTY_RE = re.compile(
    r"public\s+[\w?<>,\[\]\.\s]+?\s+(?P<name>\w+)\s*\{\s*get;\s*set;\s*\}"
)
_SNAKE_NAME_RE = re.compile(r"^_{0,2}[a-z][a-z0-9]*(?:_[a-z0-9]+)+_{0,2}$")
_TRANSLATOR_NAME_RE = re.compile(r"pascal|snake|camel|to_title|_case_", re.IGNORECASE)
_USER_CONFIG_ATTR_RE = re.compile(r"\buser_config\s*\.\s*(?P<name>\w+)")


def pascal_case(name):
    """Return the mechanically derived PascalCase spelling of a snake_case name.

    This is the rule that covers 20 of the 31 bare delegations. The other 11
    are renames and are listed in RENAMED_ALIASES, so a mismatch against this
    function is expected for them and a finding for anything else.
    """
    return "".join(part[:1].upper() + part[1:] for part in name.split("_"))


class Finding(object):
    """One contract violation, rendered as a single reviewable line."""

    def __init__(self, code, path, line, message):
        self.code = code
        self.path = path
        self.line = line
        self.message = message

    def __str__(self):
        return "{}:{}: [{}] {}".format(self.path, self.line, self.code, self.message)


def _relative(path):
    """Render a path repo-relative with forward slashes, for stable output."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_section_schema(sections_dir):
    """Map each INI section name to the set of C# properties it declares.

    Returns:
        (dict[str, set[str]]): section name -> declared property names

    Raises:
        FileNotFoundError: if the sections directory does not exist
    """
    if not sections_dir.is_dir():
        raise FileNotFoundError(
            "section schema directory not found: {}".format(sections_dir)
        )

    schema = {}
    for path in sorted(sections_dir.glob("*Section.cs")):
        source = path.read_text(encoding="utf-8")
        name_match = _SECTION_NAME_RE.search(source)
        if not name_match:
            continue
        properties = schema.setdefault(name_match.group("name").lower(), set())
        for line in source.splitlines():
            prop_match = _PROPERTY_RE.search(line)
            if prop_match:
                properties.add(prop_match.group("name"))
    return schema


def _class_node(tree, class_name):
    """Return the named class definition in a parsed module, or None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _strip_docstring(node):
    """Return a function body without its leading docstring expression."""
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _property_kind(node):
    """Classify a PyRevitConfig member as a property getter, setter, or neither."""
    decorators = [ast.unparse(d) for d in node.decorator_list]
    if "property" in decorators:
        return "get"
    if any(d.endswith(".setter") for d in decorators):
        return "set"
    return None


def _reads_section(node, sections):
    """Whether a node reads or writes any typed-section property."""
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Attribute)
            and isinstance(child.value.value, ast.Name)
            and child.value.value.id == "self"
            and child.value.attr in sections
        ):
            return True
    return False


def _bare_delegation(getter, sections):
    """Return the (section, property) a getter is a bare read of, or None."""
    body = _strip_docstring(getter)
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return None
    value = body[0].value
    if (
        not isinstance(value, ast.Attribute)
        or not isinstance(value.value, ast.Attribute)
        or not isinstance(value.value.value, ast.Name)
        or value.value.value.id != "self"
        or value.value.attr not in sections
    ):
        return None
    return (value.value.attr, value.attr)


def classify_config_class(tree):
    """Describe the public property surface of ``PyRevitConfig``.

    Returns:
        (tuple): declared names mapped to their line numbers; the bare
        delegations as ``alias -> (section, property)``; the names with a
        static property; the names that read a section without being a bare
        delegation; and whether the class defines ``__getattr__`` at all.
    """
    class_node = _class_node(tree, "PyRevitConfig")
    if class_node is None:
        raise ValueError("PyRevitConfig is not defined in the config bridge")

    getters = {}
    declared = {}
    for node in class_node.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        declared[node.name] = node.lineno
        if _property_kind(node) == "get":
            getters[node.name] = node

    sections = set(TYPED_SECTIONS)
    static_properties = set()
    bare = {}
    derived = set()
    for name, getter in getters.items():
        if name.startswith("_"):
            continue
        static_properties.add(name)
        target = _bare_delegation(getter, sections)
        if target is not None:
            bare[name] = target
        elif _reads_section(getter, sections):
            derived.add(name)

    dynamic_dispatch = any(
        name in declared for name in ("__getattr__", "__getattribute__")
    )
    return declared, bare, static_properties, derived, dynamic_dispatch


def _check_schema(sections_dir):
    """Validate that the typed sections this contract names still have schemas."""
    findings = []
    schema = load_section_schema(sections_dir)
    for section in TYPED_SECTIONS:
        if not schema.get(section):
            findings.append(
                Finding(
                    "SCHEMA-MISSING",
                    _relative(sections_dir),
                    0,
                    "no C# section schema declares [{}]; alias targets for it "
                    "cannot be validated".format(section),
                )
            )
    return schema, findings


def _check_aliases(schema, bare, static_properties, derived, dynamic_dispatch, line_of):
    """Compare the derived flat-alias mapping against the contract.

    Args:
        schema: section name -> declared C# property names
        bare: alias -> (section, property) for every bare delegation found
        static_properties: names declared as a static property
        derived: names that read a section without being a bare delegation
        dynamic_dispatch: whether PyRevitConfig defines __getattr__ at all
        line_of: name -> line number in the config bridge, for finding output
    """
    findings = []
    rel = USERCONFIG_REL

    for alias in sorted(bare):
        section, prop = bare[alias]
        declared = schema.get(section, set())
        expected = pascal_case(alias)
        if prop not in declared:
            hint = ""
            if expected in declared:
                hint = (
                    "; the schema does declare {}, which is what the name "
                    "converts to".format(expected)
                )
            findings.append(
                Finding(
                    "ALIAS-SCHEMA",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} delegates to {}.{}, which the C# schema does "
                    "not declare{}; _SectionCompatWrapper falls back to a raw "
                    "option, so a stale target reads back as a missing setting "
                    "instead of failing here".format(alias, section, prop, hint),
                )
            )
            continue
        if prop == expected and alias in RENAMED_ALIASES:
            findings.append(
                Finding(
                    "ALIAS-RENAME",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} is listed as a rename but now targets {}.{}, "
                    "which its own name converts to mechanically; drop it from "
                    "RENAMED_ALIASES".format(alias, section, prop),
                )
            )
        elif alias in RENAMED_ALIASES:
            recorded = BARE_DELEGATIONS.get(alias)
            if recorded is not None and recorded != (section, prop):
                findings.append(
                    Finding(
                        "ALIAS-RENAME",
                        rel,
                        line_of.get(alias, 0),
                        "user_config.{} is recorded as a rename to {}.{}, but now "
                        "targets {}.{}; a rename is a documented decision, so moving "
                        "its target needs one".format(
                            alias, recorded[0], recorded[1], section, prop
                        ),
                    )
                )
        elif prop != expected:
            findings.append(
                Finding(
                    "ALIAS-RENAME",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} targets {}.{}, which is not {}; either the "
                    "alias was retargeted or a new hand-written mapping crept "
                    "in, and both need a documented decision".format(
                        alias, section, prop, expected
                    ),
                )
            )

    for alias in sorted(BARE_DELEGATIONS):
        if alias in bare:
            continue
        if alias in static_properties:
            findings.append(
                Finding(
                    "ALIAS-SCHEMA",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} no longer delegates straight to {}.{}; it is "
                    "still a declared property, so a reader is unaffected, but a "
                    "transformation in the getter is a contract change".format(
                        alias, BARE_DELEGATIONS[alias][0], BARE_DELEGATIONS[alias][1]
                    ),
                )
            )
        elif alias in derived:
            continue
        elif dynamic_dispatch:
            findings.append(
                Finding(
                    "ALIAS-DYNAMIC",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} is no longer a statically declared property, so "
                    "it can only resolve through __getattr__; that removes it from "
                    "autocomplete, hover docs, and LSP resolution".format(alias),
                )
            )
        else:
            findings.append(
                Finding(
                    "ALIAS-GONE",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} was removed; it is the documented spelling for "
                    "third-party extensions, so removing it needs its own "
                    "decision and a migration note".format(alias),
                )
            )

    for alias in sorted(SECTION_DERIVED_ALIASES):
        if alias not in static_properties:
            findings.append(
                Finding(
                    "ALIAS-GONE",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} is documented as a derived alias and is "
                    "missing".format(alias),
                )
            )
    for alias in sorted(NON_SECTION_ALIASES):
        if alias not in static_properties:
            findings.append(
                Finding(
                    "ALIAS-GONE",
                    rel,
                    line_of.get(alias, 0),
                    "user_config.{} is documented as an alias and is missing".format(
                        alias
                    ),
                )
            )

    for alias in sorted(static_properties):
        if alias in FLAT_ALIASES or alias in SECTION_ACCESSORS:
            continue
        if alias in IDENTITY_PROPERTIES:
            continue
        if alias in derived:
            continue
        findings.append(
            Finding(
                "ALIAS-NEW",
                rel,
                line_of.get(alias, 0),
                "user_config.{} is a new public property on PyRevitConfig; if it "
                "is a flat alias it must be added to the contract, and if it is "
                "a section accessor or identity property it belongs in "
                "SECTION_ACCESSORS or IDENTITY_PROPERTIES".format(alias),
            )
        )

    for accessor in SECTION_ACCESSORS:
        if accessor not in static_properties:
            findings.append(
                Finding(
                    "SECTION-DYNAMIC",
                    rel,
                    line_of.get(accessor, 0),
                    "user_config.{} is no longer a statically declared property; "
                    "the typed-section surface must stay explicit".format(accessor),
                )
            )
    for prop in IDENTITY_PROPERTIES:
        if prop not in static_properties:
            findings.append(
                Finding(
                    "ALIAS-GONE",
                    rel,
                    line_of.get(prop, 0),
                    "user_config.{} is documented and is missing".format(prop),
                )
            )
    return findings


def _check_escape_hatches(tree_by_rel):
    """Verify the documented escape hatches are still declared."""
    findings = []
    for rel, class_name, members in ESCAPE_HATCHES:
        tree = tree_by_rel.get(rel)
        if tree is None:
            findings.append(Finding("ESCAPE-HATCH", rel, 0, "file not found"))
            continue
        node = _class_node(tree, class_name)
        if node is None:
            findings.append(
                Finding(
                    "ESCAPE-HATCH",
                    rel,
                    0,
                    "{} is not defined; the escape hatches it carries are part of "
                    "the contract".format(class_name),
                )
            )
            continue
        declared = {
            member.name
            for member in node.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for member in members:
            if member not in declared:
                findings.append(
                    Finding(
                        "ESCAPE-HATCH",
                        rel,
                        node.lineno,
                        "{}.{} is missing; it is the documented way to reach a "
                        "setting outside the typed schema".format(class_name, member),
                    )
                )
    return findings


def _check_no_naming_translator(tree):
    """Forbid a snake_case/PascalCase translation layer in the config bridge.

    A mapping table or conversion helper is the shape both maintainers
    rejected in #3645: it mints a second spelling per setting, hides it from
    static tooling, and its typos only surface as runtime attribute misses.
    """
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            values = [v.value for v in node.values if isinstance(v, ast.Constant)]
            if (
                keys
                and values
                and len(keys) == len(values)
                and all(isinstance(k, str) for k in keys)
                and all(isinstance(v, str) for v in values)
                and any(_SNAKE_NAME_RE.match(k) for k in keys)
                and any(v[:1].isupper() for v in values)
            ):
                findings.append(
                    Finding(
                        "NAMING-TRANSLATOR",
                        USERCONFIG_REL,
                        getattr(node, "lineno", 0),
                        "a snake_case -> PascalCase mapping table has appeared in "
                        "the config bridge; #3645 settled on a single spelling per "
                        "setting",
                    )
                )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _TRANSLATOR_NAME_RE.search(node.name):
                findings.append(
                    Finding(
                        "NAMING-TRANSLATOR",
                        USERCONFIG_REL,
                        node.lineno,
                        "{}() looks like a case translator in the config bridge; "
                        "#3645 settled on a single spelling per setting".format(
                            node.name
                        ),
                    )
                )
    return findings


def _iter_python_files(roots, resolve_against):
    """Yield the Python files to scan, honoring the excluded trees."""
    for root in roots:
        root_path = root if root.is_absolute() else resolve_against / root
        if root_path.is_file():
            candidates = [root_path]
        else:
            candidates = sorted(root_path.rglob("*.py"))
        excluded = [resolve_against / e for e in EXCLUDED_DIRS]
        for path in candidates:
            if any(exc in path.parents or exc == path for exc in excluded):
                continue
            yield path


def _source_lines(path):
    """Read a file as text, returning None when it cannot be decoded."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _code_only_lines(source):
    """Return each line with comments and string literals blanked out.

    A docstring that shows the spelling to avoid is documentation, not a call
    site, and a commented-out line is not executed - so both have to go. But a
    string argument routinely shares its line with a real call, so the literal
    is blanked rather than the whole line dropped, which keeps that call
    visible. The blind spot this leaves is an f-string with a call inside the
    literal, which is blanked with the rest of the text.
    """
    lines = list(source.splitlines())
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return lines
    for token in tokens:
        if token.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        start_row, start_col = token.start
        end_row, end_col = token.end
        for row in range(start_row, end_row + 1):
            if row - 1 >= len(lines):
                continue
            line = lines[row - 1]
            col_start = start_col if row == start_row else 0
            col_end = end_col if row == end_row else len(line)
            if col_end <= col_start:
                continue
            lines[row - 1] = (
                line[:col_start] + " " * (col_end - col_start) + line[col_end:]
            )
    return lines


def check_call_sites(roots, resolve_against=REPO_ROOT):
    """Find first-party call sites that misuse a typed section's spelling.

    A snake_case attribute on a typed section is not rejected: the wrapper
    stores it as a raw option, so the write lands in the file under a key no
    reader looks at and the typed property keeps its old value. That is the
    failure mode the contract closes off, and it is invisible until someone
    wonders why a setting never took effect.
    """
    findings = []
    for path in _iter_python_files(roots, resolve_against):
        source = _source_lines(path)
        if source is None:
            continue
        if _relative(path) in (USERCONFIG_REL, CONFIGPARSER_REL):
            continue
        for line_no, line in enumerate(_code_only_lines(source), start=1):
            for match in _USER_CONFIG_ATTR_RE.finditer(line):
                name = match.group("name")
                if name not in TYPED_SECTIONS:
                    continue
                rest = line[match.end() :]
                attr = re.match(r"\.\s*(?P<attr>\w+)", rest)
                if not attr:
                    continue
                attr_name = attr.group("attr")
                if attr_name in SECTION_MEMBER_EXEMPT:
                    continue
                if not _SNAKE_NAME_RE.match(attr_name):
                    continue
                findings.append(
                    Finding(
                        "SECTION-SNAKE",
                        _relative(path),
                        line_no,
                        "user_config.{}.{} is snake_case on a typed section; the "
                        "write lands as a raw option instead of setting the "
                        "typed property. Use get_option/set_option for a "
                        "non-schema key".format(name, attr_name),
                    )
                )
    return findings


def census_call_sites(roots, resolve_against=REPO_ROOT):
    """Count first-party flat-alias reads and writes, per alias.

    The deprecation decision in #3645 is a question about migration cost, and
    third-party extension call sites are not greppable from here. This census
    measures the part that is, so the first-party cost of any future change
    can be stated rather than guessed.
    """
    reads = {}
    writes = {}
    for path in _iter_python_files(roots, resolve_against):
        source = _source_lines(path)
        if source is None:
            continue
        for line in _code_only_lines(source):
            for match in _USER_CONFIG_ATTR_RE.finditer(line):
                name = match.group("name")
                if name not in FLAT_ALIASES:
                    continue
                rest = line[match.end() :]
                if re.match(r"=[^=]", rest.lstrip()) and not rest.lstrip().startswith(
                    "=="
                ):
                    writes[name] = writes.get(name, 0) + 1
                else:
                    reads[name] = reads.get(name, 0) + 1
    return reads, writes


def main():
    """Run the checker CLI and return its process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="files or directories to scan for call sites",
    )
    parser.add_argument(
        "--census",
        action="store_true",
        help="print the first-party flat-alias read/write census instead of "
        "checking it",
    )
    args = parser.parse_args()

    if args.paths:
        roots = args.paths
        resolve_against = Path.cwd()
    else:
        roots = [Path(p) for p in DEFAULT_SCAN_ROOTS]
        resolve_against = REPO_ROOT

    if args.census:
        reads, writes = census_call_sites(roots, resolve_against)
        for name in sorted(FLAT_ALIASES):
            r = reads.get(name, 0)
            w = writes.get(name, 0)
            if r or w:
                print("{:<28} read={:<5} write={}".format(name, r, w))
        print(
            "\n{} alias(es) with first-party call sites; {} read, {} write".format(
                len([n for n in FLAT_ALIASES if reads.get(n) or writes.get(n)]),
                sum(reads.values()),
                sum(writes.values()),
            )
        )
        return 0

    try:
        schema, findings = _check_schema(REPO_ROOT / SECTIONS_REL)
        userconfig_path = REPO_ROOT / USERCONFIG_REL
        trees = {}
        for rel in (USERCONFIG_REL, CONFIGPARSER_REL):
            path = REPO_ROOT / rel
            if path.is_file():
                trees[rel] = ast.parse(path.read_text(encoding="utf-8"))
        if USERCONFIG_REL not in trees:
            print("error: {} not found".format(USERCONFIG_REL), file=sys.stderr)
            return 2

        (
            line_of,
            bare,
            static_properties,
            _derived,
            dynamic_dispatch,
        ) = classify_config_class(trees[USERCONFIG_REL])
        findings += _check_aliases(
            schema, bare, static_properties, _derived, dynamic_dispatch, line_of
        )
        findings += _check_escape_hatches(trees)
        findings += _check_no_naming_translator(trees[USERCONFIG_REL])
        findings += check_call_sites(roots, resolve_against)
    except (FileNotFoundError, SyntaxError, ValueError) as err:
        print("error: {}".format(err), file=sys.stderr)
        return 2

    for finding in findings:
        print(finding)

    counts = {}
    for finding in findings:
        counts[finding.code] = counts.get(finding.code, 0) + 1
    summary = ", ".join(
        "{}: {}".format(code, count) for code, count in sorted(counts.items())
    )
    print(
        "\n{} finding(s){}".format(
            len(findings), " ({})".format(summary) if summary else ""
        )
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())