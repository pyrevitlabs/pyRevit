"""Pre-commit hook: reject Python syntax that IronPython 2.7.12 cannot parse.

pyRevit's default runtime is IronPython 2.7.12, whose parser predates PEP 448
(Additional Unpacking Generalizations, Python 3.5). The most common regression
this causes is a trailing comma after ``**kwargs`` in a multi-line signature or
call: ``ruff format`` emits ``**kwargs,`` whenever a multi-line parameter list
ends with **kwargs (PEP 448 grammar), but IPY2 raises ``SyntaxError: unexpected
token ','`` at parse time, which makes the entire ``pyrevit.forms`` module
unloadable.

The formatter is opted out for ``pyrevitlib/pyrevit/forms/_ipy.py`` via a
separate ``[tool.ruff] extend-exclude`` entry. This hook is the belt-and-
suspenders line of defense: it tokenizes every ``pyrevitlib/`` Python file and
fails the commit if executable code includes ``**kwargs,`` - including in
modules that load before ``_ipy.py`` at IronPython startup - so the same bug
cannot land again under a different path.

Run standalone for local checks::

    python dev/scripts/check_ipy2_compat.py path/to/file.py ...

Use ``--fix`` to remove only the incompatible trailing commas after formatting::

    python dev/scripts/check_ipy2_compat.py --fix path/to/file.py ...
"""

import io
import sys
import tokenize


def _read_source(path):
    try:
        with open(path, "rb") as source:
            encoding, _ = tokenize.detect_encoding(source.readline)
        with open(path, encoding=encoding, newline="") as source:
            return source.read(), encoding
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None, None


def _find_incompatible_commas(source):
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return []

    commas = []
    for index in range(len(tokens) - 3):
        unpacking, name, comma, following = tokens[index : index + 4]
        if (
            unpacking.type == tokenize.OP
            and unpacking.string == "**"
            and name.type == tokenize.NAME
            and comma.type == tokenize.OP
            and comma.string == ","
            and unpacking.start[0] == name.start[0] == comma.start[0]
            and following.type in (tokenize.COMMENT, tokenize.NEWLINE, tokenize.NL)
        ):
            commas.append((comma, name))
    return commas


def _scan(path):
    source, _ = _read_source(path)
    if source is None:
        return []
    return [
        (comma.start[0], "**{},".format(name.string))
        for comma, name in _find_incompatible_commas(source)
    ]


def _remove_incompatible_commas(path):
    source, encoding = _read_source(path)
    if source is None:
        return []

    commas = _find_incompatible_commas(source)
    if not commas:
        return []

    line_offsets = []
    offset = 0
    for line in source.splitlines(keepends=True):
        line_offsets.append(offset)
        offset += len(line)

    source_chars = list(source)
    for comma, _ in reversed(commas):
        source_chars.pop(line_offsets[comma.start[0] - 1] + comma.start[1])

    with open(path, "w", encoding=encoding, newline="") as output:
        output.write("".join(source_chars))
    return [(comma.start[0], "**{},".format(name.string)) for comma, name in commas]


def main(paths):
    """Check paths for unsupported syntax, optionally removing the commas."""
    fix = paths[:1] == ["--fix"]
    if fix:
        paths = paths[1:]
        for path in paths:
            _remove_incompatible_commas(path)

    findings = [(p, line, snippet) for p in paths for line, snippet in _scan(p)]
    if not findings:
        return 0
    for path, line, snippet in findings:
        print("{}:{}: {}".format(path, line, snippet), file=sys.stderr)
    print(
        "\nIronPython 2.7.12 cannot parse **kwargs, in multi-line "
        "signatures or calls (pre-PEP-448 grammar). Drop the trailing comma.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
