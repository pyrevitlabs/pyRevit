import clr

from pyrevit import PYTHON_LIB_DIR, MAIN_LIB_DIR
from pyrevit.coreutils import Timer

clr.AddReference('System')
clr.AddReference('IronPython')
from System.Collections.Generic import List
import IronPython as ipy
import IronPython.Hosting as ipyh


script = "import random; random.randint(1,10)"


def run():
    # set up script environment
    options = { "Frames": True , "FullFrames": True }
    engine = ipyh.Python.CreateEngine(options)
    engine.SetSearchPaths(List[str]([PYTHON_LIB_DIR, MAIN_LIB_DIR]))
    runtime = engine.Runtime
    scope = runtime.CreateScope()
    source = engine.CreateScriptSourceFromString(script)
    comped = source.Compile()
    comped.Execute(scope)
    runtime.Shutdown()


for idx in range(1, 200):
    timer = Timer()
    run()
    print('Engine {}: {}'.format(idx, timer.get_time()))
