import sys
import os.path as op
import clr

from pyrevit import USER_SYS_TEMP
from pyrevit import script

source = script.get_bundle_file("ipycompiletest.py")
dest = op.join(USER_SYS_TEMP, "compiledipytest.dll")

compiled = op.isfile(dest)
if not compiled:
    try:
        clr.CompileModules(dest, source)
        compiled = True
    except Exception as cerr:
        # clr.CompileModules compiles through the CodeDom compiler, which the
        # .NET Core / .NET 10 runtime behind Revit 2025+ does not ship, so it
        # raises "Specified method is not supported." That is a legitimate
        # outcome for this test on such a runtime and worth stating plainly.
        # Falling through to the import step used to hide it behind a
        # "file does not exist" traceback for a DLL that was never written,
        # because the old `except IO.IOException` branch also swallowed this.
        print("Compilation not supported on this runtime: {}".format(cerr))

if compiled:
    # import test
    sys.path.append(USER_SYS_TEMP)
    clr.AddReferenceToFileAndPath(dest)

    import ipycompiletest

    ipycompiletest.compile_test("Compiled function works.")

    ipycompiletest.CompiledType("Compiled type works.")
else:
    print("SKIPPED import test: no assembly was produced.")
