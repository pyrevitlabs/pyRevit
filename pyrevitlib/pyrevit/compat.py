"""python engine compatibility module."""

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY2:
    safe_strtype = unicode  # noqa
