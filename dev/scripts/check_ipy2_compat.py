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
suspenders line of defense: it scans every ``pyrevitlib/`` Python file and
fails the commit if ``**kwargs,`` ever appears anywhere - including in
modules that load before ``_ipy.py`` at IronPython startup - so the same bug
cannot land again under a different path.

Run standalone for local checks::

    python dev/scripts/check_ipy2_compat.py path/to/file.py ...
"""

import re
import sys


PATTERN = re.compile(r"^\s+\*\*kwargs,\s*$", re.MULTILINE)


def _scan(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    hits = []
    for match in PATTERN.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        hits.append((line, match.group(0).rstrip()))
    return hits


def main(paths):
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
