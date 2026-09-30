"""A query that never finishes on its own.

Run with --timeout 5 on each engine (--engine ironpython, --engine cpython).
Expected: after about 5 seconds, status error, error.type timeout, and Revit
responsive again. The bare except is narrowed to Exception, so the script can't swallow the stop.
"""

while True:
    try:
        pass
    except:  # noqa: E722
        pass
