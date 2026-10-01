"""Exercise IronPython assembly compilation when the active runtime supports it."""

import sys
import os.path as op
import clr

from System import NotSupportedException

from pyrevit import USER_SYS_TEMP
from pyrevit import script

source = script.get_bundle_file("ipycompiletest.py")
dest = op.join(USER_SYS_TEMP, "compiledipytest.dll")

try:
    clr.CompileModules(dest, source)
except (NotImplementedError, NotSupportedException):
    print("SKIPPED: IronPython cannot emit assemblies on this .NET runtime.")
    script.exit()

if not op.isfile(dest):
    raise RuntimeError("Compilation completed without creating: {}".format(dest))

sys.path.append(USER_SYS_TEMP)
clr.AddReferenceToFileAndPath(dest)

import ipycompiletest

ipycompiletest.compile_test("Compiled function works.")

ipycompiletest.CompiledType("Compiled type works.")

print("IronPython assembly compilation test passed.")
