"""Charts engine for output window."""
# pylint: disable=C0103
from json import JSONEncoder

from pyrevit.coreutils import timestamp, random_rgba_color

# CHARTS_ENGINE = 'Chart.js'
CHARTS_ENGINE = 'Chart.bundle.js'

# chart.js chart types
LINE_CHART = 'line'
BAR_CHART = 'bar'
RADAR_CHART = 'radar'
POLAR_CHART = 'polarArea'
PIE_CHART = 'pie'
DOUGHNUT_CHART = 'doughnut'
BUBBLE_CHART = 'bubble'


CHARTS_JS_PATH = \
    "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/{version}/Chart.min.js"


SCRIPT_TEMPLATE = \
    "var ctx = document.getElementById('{canvas_id}').getContext('2d');" \
    "var chart = new Chart(ctx, {canvas_code});"


class _ChartsDataSetEncode(JSONEncoder):
    """JSON encoder for chart data sets."""
    def default(self, dataset_obj):  # pylint: disable=E0202, W0221
        data_dict = dataset_obj.__dict__.copy()
        for key, value in data_dict.items():
            if key.startswith('_') or value == '' or value == []:
                data_dict.pop(key)

        return data_dict


class PyRevitOutputChartOptions(object):
    """Chart options wrapper object."""
    def __init__(self):
        pass


class PyRevitOutputChartDataset(object):
    """Chart dataset wrapper object."""
    def __init__(self, label):
        self.label = label
        self.data = []
        self.backgroundColor = ''

    def set_color(self, *args):
        """Set dataset color.

        Arguments are expected to be R, G, B, A values.

        Examples:
            ```python
            dataset_obj.set_color(0xFF, 0x8C, 0x8D, 0.8)
            ```
        """
        if len(args) == 4:
            self.backgroundColor = 'rgba({},{},{},{})'.format(args[0],
                                                              args[1],
                                                              args[2],
                                                              args[3])
        elif len(args) == 1:
            self.backgroundColor = '{}'.format(args[0])


class PyRevitOutputChartData(object):
    """Chart data wrapper object."""
    def __init__(self):
        self.labels = ''
        self.datasets = []

    def new_dataset(self, dataset_label):
        """Create new data set.

        Args:
            dataset_label (str): dataset label

        Returns:
            (PyRevitOutputChartDataset): dataset wrapper object

        Examples:
            ```python
            chart.data.new_dataset('set_a')
            ```
        """
        new_dataset = PyRevitOutputChartDataset(dataset_label)
        self.datasets.append(new_dataset)
        return new_dataset


class PyRevitOutputChart(object):
    """Chart wrapper object for output window.

    Attributes:
        output (pyrevit.output.PyRevitOutputWindow):
            output window wrapper object
        chart_type (str): chart type name
    """
    def __init__(self, output, chart_type=LINE_CHART, version=None):
        self._output = output
        self._style = None
        self._width = self._height = None
        self._version = version or '2.8.0'

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
        # # Position of the title. Possible values are 'top',
        # # 'left', 'bottom' and 'right'.
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
        # # if true, the tooltip mode applies only when the mouse
        # # position intersects with an element.
        # # If false, the mode will be applied at all times
        # chart.options.tooltips = {'enabled': True,
        #                           'intersect': True,
        #                           'backgroundColor': 'rgba(0,0,0,0.8)',
        #                           'caretSize': 5,
        #                           'displayColors': True}

    def _setup_charts(self):
        cur_head = self._output.get_head_html()
        charts_js_path = CHARTS_JS_PATH.format(version=self._version)
        if charts_js_path not in cur_head:
            self._output.inject_script('', {'src': charts_js_path})

    @staticmethod
    def _make_canvas_unique_id():
        return 'chart{}'.format(timestamp())

    def _make_canvas_code(self, canvas_id):
        attribs = ''
        attribs += ' id="{}"'.format(canvas_id)
        if self._style:
            attribs += ' style="{}"'.format(self._style)
        else:
            if self._width:
                attribs += ' width="{}px"'.format(self._width)
            if self._height:
                attribs += ' height="{}px"'.format(self._height)

        return '<canvas {}></canvas>'.format(attribs)

    def _make_charts_script(self, canvas_id):
        return SCRIPT_TEMPLATE.format(
            canvas_id=canvas_id,
            canvas_code=_ChartsDataSetEncode().encode(self))

    def randomize_colors(self):
        """Randomize chart datasets colors."""
        if self.type in [POLAR_CHART, PIE_CHART, DOUGHNUT_CHART]:
            for dataset in self.data.datasets:
                dataset.backgroundColor = [random_rgba_color()
                                           for _ in range(0, len(dataset.data))]
        else:
            for dataset in self.data.datasets:
                dataset.backgroundColor = random_rgba_color()

    def set_width(self, width):
        """Set chart width on output window."""
        self._width = width

    def set_height(self, height):
        """Set chart height on output window."""
        self._height = height

    def set_style(self, html_style):
        """Set chart styling.

        Args:
            html_style (str): inline html css styling string

        Examples:
            ```python
            chart.set_style('height:150px')
            ```
        """
        self._style = html_style

    def draw(self):
        """Request chart to draw itself on output window."""
        self._setup_charts()
        # setup canvas
        canvas_id = self._make_canvas_unique_id()
        canvas_code = self._make_canvas_code(canvas_id)
        self._output.print_html(canvas_code)
        # make the code
        js_code = self._make_charts_script(canvas_id)
        self._output.inject_script(js_code, body=True)
