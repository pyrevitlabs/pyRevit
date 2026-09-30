from pyrevit import MISC_LIB_DIR, MAIN_LIB_DIR
from pyrevit import coreutils
from pyrevit import framework
from pyrevit import script

# No AddReference("IronPython") here: the IronPython engine host has already
# loaded IronPython - it is what is running this very script - and the shipped
# assembly is named pyRevitLabs.IronPython.dll (that is framework.ipy_dllpath,
# built from engine.EnginePrefix), so the name-only overload raised
# "Could not add reference to assembly IronPython" and the test never reached
# the engine loop it exists to measure. Importing the namespaces below is the
# real proof that the reference is in place.
import IronPython.Hosting
import IronPython.Runtime


output = script.get_output()


TEST_UNIT = 100
MAX_TESTS = 5 * TEST_UNIT
script = "import sys; print(sys.path)"


def run(engine, runtime):
    scope = runtime.CreateScope()
    co = engine.GetCompilerOptions(scope)
    # co.Module &= ~IronPython.Runtime.ModuleOptions.Optimized
    source = engine.CreateScriptSourceFromString(script)
    comped = source.Compile()
    comped.Execute(scope)


def make_engine():
    options = {"Frames": True, "FullFrames": True, "LightweightScopes": True}
    engine = IronPython.Hosting.Python.CreateEngine(options)
    engine.SetSearchPaths(framework.List[str]([MISC_LIB_DIR, MAIN_LIB_DIR]))
    runtime = engine.Runtime
    return engine, runtime


def shutdown(runtime):
    runtime.Shutdown()


engine_times = []
output_times = []

for idx in range(1, MAX_TESTS):
    engine, runtime = make_engine()
    engine_timer = coreutils.Timer()
    run(engine, runtime)
    eng_time = engine_timer.get_time()
    shutdown(runtime)
    engine_times.append(eng_time)

    output_timer = coreutils.Timer()
    print("Engine {}: {}".format(idx, eng_time))
    output_times.append(output_timer.get_time())


chart = output.make_line_chart()
# chart.options.scales = {'xAxes': [{'ticks': {'fixedStepSize': 5}, 'type': 'category', 'position': 'bottom'}],
#                         'yAxes': [{'ticks': {'fixedStepSize': 10}}]}

chart.data.labels = [x for x in range(0, MAX_TESTS + 1)]

engine_dataset = chart.data.new_dataset("engine_timer")
engine_dataset.set_color(0xC3, 0x10, 0x10, 0.4)
engine_dataset.data = engine_times

output_dataset = chart.data.new_dataset("output_timer")
output_dataset.set_color(0xF0, 0xA7, 0x19, 0.4)
output_dataset.data = output_times

chart.draw()
