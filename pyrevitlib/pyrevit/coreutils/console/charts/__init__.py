import os.path as op
from json import JSONEncoder

from pyrevit import MAIN_LIB_DIR
from pyrevit.coreutils import timestamp


# chart.js chart types
LINE_CHART = 'line'
BAR_CHART = 'bar'
RADAR_CHART = 'radar'
POLAR_CHART = 'polarArea'
PIE_CHART = 'pie'
DOUGHNUT_CHART = 'doughnut'
BUBBLE_CHART = 'bubble'


CHARTS_JS_PATH = op.join(MAIN_LIB_DIR, 'pyrevit', 'coreutils', 'console', 'charts', 'Chart.js')


SCRIPT_TEMPLATE = "var ctx = document.getElementById('{}').getContext('2d');var chart = new Chart(ctx, {});"


class ChartsDataSetEncode(JSONEncoder):
    def default(self, dataset_obj):
        data_dict = dataset_obj.__dict__.copy()
        for key, value in data_dict.items():
            if key.startswith('_') or value == '' or value == []:
                data_dict.pop(key)

        return data_dict


class PyRevitOutputChartOptions:
    def __init__(self):
        pass


class PyRevitOutputChartDataset:
    def __init__(self, label):
        self.label = label
        self.data = []
        self.backgroundColor = ''

    def set_background(self, r, g, b, a):
        self.backgroundColor = 'rgba({},{},{},{})'.format(r, g, b, a)


class PyRevitOutputChartData:
    def __init__(self):
        self.labels = ''
        self.datasets = []

    def new_dataset(self, dataset_label):
        new_dataset = PyRevitOutputChartDataset(dataset_label)
        self.datasets.append(new_dataset)
        return new_dataset


class PyRevitOutputChart:
    def __init__(self, output, chart_type=LINE_CHART):
        self._output = output

        self.type = chart_type
        self.data = PyRevitOutputChartData()
        self.options = PyRevitOutputChartOptions()

    def _setup_charts(self):
        cur_head = self._output.get_head_html()
        if CHARTS_JS_PATH not in cur_head:
            self._output.inject_script('', {'src': CHARTS_JS_PATH})

    @staticmethod
    def _make_canvas_unique_id():
        return 'chart{}'.format(timestamp())

    @staticmethod
    def _make_canvas_code(canvas_id):
        return '<canvas id="{}"></canvas>'.format(canvas_id)

    def _make_charts_script(self, canvas_id):
        return SCRIPT_TEMPLATE.format(canvas_id, ChartsDataSetEncode().encode(self))

    def draw(self):
        self._setup_charts()
        # setup canvas
        canvas_id = self._make_canvas_unique_id()
        canvas_code = self._make_canvas_code(canvas_id)
        self._output.print_html(canvas_code)
        # make the code
        js_code = self._make_charts_script(canvas_id)
        self._output.inject_script(js_code)