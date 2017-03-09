import clr

from pyrevit import PYTHON_LIB_DIR, MAIN_LIB_DIR
from pyrevit.coreutils import Timer

from scriptutils import this_script

clr.AddReference('System')
clr.AddReference('IronPython')
# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
import IronPython.Hosting


TEST_UNIT = 100
MAX_TESTS = 5 * TEST_UNIT
script = "import random; random.randint(1,10)"


def run():
    # set up script environment
    options = {"Frames": True, "FullFrames": True}
    engine = IronPython.Hosting.Python.CreateEngine(options)
    engine.SetSearchPaths(List[str]([PYTHON_LIB_DIR, MAIN_LIB_DIR]))
    runtime = engine.Runtime
    scope = runtime.CreateScope()
    source = engine.CreateScriptSourceFromString(script)
    comped = source.Compile()
    comped.Execute(scope)
    runtime.Shutdown()


engine_times = []
output_times = []

for idx in range(1, MAX_TESTS):
    engine_timer = Timer()
    run()
    eng_time = engine_timer.get_time()
    engine_times.append(eng_time)

    output_timer = Timer()
    print('Engine {}: {}'.format(idx, eng_time))
    output_times.append(output_timer.get_time())


chart = this_script.output.make_line_chart()
# chart.options.scales = {'xAxes': [{'ticks': {'fixedStepSize': 5}, 'type': 'category', 'position': 'bottom'}],
#                         'yAxes': [{'ticks': {'fixedStepSize': 10}}]}

chart.data.labels = [x for x in range(0, MAX_TESTS + 1)]

engine_dataset = chart.data.new_dataset('engine_timer')
engine_dataset.set_color(0xc3, 0x10, 0x10, 0.4)
engine_dataset.data = engine_times

output_dataset = chart.data.new_dataset('output_timer')
output_dataset.set_color(0xf0, 0xa7, 0x19, 0.4)
output_dataset.data = output_times

chart.draw()
