#! python3
"""Run engine-portability unit tests on the CPython engine.

Requires an open project document. Compare results against the IronPython twin
button to spot per-engine gaps.
"""

import os.path as op
import sys

from pyrevit import EXEC_PARAMS
from pyrevit.unittests import test_py3_compat
from pyrevit.unittests.runner import run_module_tests


print("Python engine: {}".format(sys.version))
print("Py3 compatibility suite revision: 6")

test_py3_compat.FAMILY_FILE = op.normpath(
    op.join(
        EXEC_PARAMS.command_path,
        "..",
        "..",
        "Bundle Tests.pulldown",
        "Test Content Bundle.content",
        "North Symbol_content.rfa",
    )
)
run_module_tests(test_py3_compat)
