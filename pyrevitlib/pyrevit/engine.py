"""Access loading engine properties."""
#pylint: disable=W0703,C0302,C0103,W0614,E0401,W0611,C0413,ungrouped-imports
import os.path as op
import clr

try:
    clr.AddReference('PyRevitLoader')
except Exception:
    # probably older IronPython engine not being able to
    # resolve to an already loaded assembly.
    # PyRevitLoader is executing this script so it should be referabe.
    pass

try:
    import PyRevitLoader
    ScriptExecutor = PyRevitLoader.ScriptExecutor
    EnginePrefix = ScriptExecutor.EnginePrefix
    EngineVersion = ScriptExecutor.EngineVersion
    EnginePath = op.dirname(
        clr.GetClrType(ScriptExecutor).Assembly.Location
        )
except ImportError:
    # this means that pyRevit is _not_ being loaded from a pyRevit engine
    # e.g. when importing from RevitPythonShell
    PyRevitLoader = ScriptExecutor = None
    EnginePrefix = ''
    EngineVersion = 000
    EnginePath = ''
