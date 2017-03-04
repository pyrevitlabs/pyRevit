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
        self._style = None

        self.type = chart_type
        self.data = PyRevitOutputChartData()

        self.options = PyRevitOutputChartOptions()
        # # common chart options and their default values
        # chart.options.responsive = True
        # chart.options.responsiveAnimationDuration = 0
        # chart.options.maintainAspectRatio = True
        #
        # # layout options
        # chart.options.layout = {'padding': 0}
        #
        # # title options
        # # position:
        # # Position of the title. Possible values are 'top', 'left', 'bottom' and 'right'.
        # chart.options.title = {'display': False,
        #                        'position': 'top',
        #                        'fullWidth': True,
        #                        'fontSize': 12,
        #                        'fontFamily': 'Arial',
        #                        'fontColor': '#666',
        #                        'fontStyle': 'bold',
        #                        'padding': 10,
        #                        'text': ''
        #                        }
        #
        # # legend options
        # chart.options.legend = {'display': True,
        #                         'position': 'top',
        #                         'fullWidth': True,
        #                         'reverse': False,
        #                         'labels': {'boxWidth': 40,
        #                                    'fontSize': 12,
        #                                    'fontStyle': 'normal',
        #                                    'fontColor': '#666',
        #                                    'fontFamily': 'Arial',
        #                                    'padding': 10,
        #                                    'usePointStyle': True
        #                                    }
        #                         }
        #
        # # tooltips options
        # # intersect:
        # # if true, the tooltip mode applies only when the mouse position intersects with an element.
        # # If false, the mode will be applied at all times
        # chart.options.tooltips = {'enabled': True,
        #                           'intersect': True,
        #                           'backgroundColor': 'rgba(0,0,0,0.8)',
        #                           'caretSize': 5,
        #                           'displayColors': True}

    def _setup_charts(self):
        cur_head = self._output.get_head_html()
        if CHARTS_JS_PATH not in cur_head:
            self._output.inject_script('', {'src': CHARTS_JS_PATH})

    @staticmethod
    def _make_canvas_unique_id():
        return 'chart{}'.format(timestamp())

    def _make_canvas_code(self, canvas_id):
        if self._style:
            return '<canvas id="{}" style="{}"></canvas>'.format(canvas_id, self._style)
        else:
            return '<canvas id="{}"></canvas>'.format(canvas_id)

    def _make_charts_script(self, canvas_id):
        return SCRIPT_TEMPLATE.format(canvas_id, ChartsDataSetEncode().encode(self))

    def set_style(self, html_style):
        self._style = html_style

    def draw(self):
        self._setup_charts()
        # setup canvas
        canvas_id = self._make_canvas_unique_id()
        canvas_code = self._make_canvas_code(canvas_id)
        self._output.print_html(canvas_code)
        # make the code
        js_code = self._make_charts_script(canvas_id)
        self._output.inject_script(js_code)
