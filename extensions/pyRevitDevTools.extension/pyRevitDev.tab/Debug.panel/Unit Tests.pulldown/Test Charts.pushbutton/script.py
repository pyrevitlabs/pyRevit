from pyrevit.output import charts
from pyrevit import script

__context__ = 'zero-doc'


output = script.get_output()


output.set_width(900)


test1_types = [charts.LINE_CHART,
               charts.BAR_CHART,
               charts.RADAR_CHART]

test2_types = [charts.BUBBLE_CHART]

test3_types = [charts.POLAR_CHART]

test4_types = [charts.PIE_CHART,
               charts.DOUGHNUT_CHART]


def get_test_chart(chart_type):
    chart = output.make_chart(version='2.8.0')
    chart.type = chart_type
    # chart.set_style('height:150px')

    # chart.options.maintainAspectRatio = True
    chart.options.title = {'display': True,
                           'text': '{} chart'.format(chart_type).upper(),
                           'fontSize': 18,
                           'fontColor': '#000',
                           'fontStyle': 'bold'}

    chart.options.scales = {
        'xAxes': [{
            'display': True,
            'scaleLabel': {
                'display': True,
                'labelString': 'Month'
                }}],
        'yAxes': [{
            'display': True,
            'scaleLabel': {
                'display': True,
                'labelString': 'Value'
                }}]}

    return chart


def test1_chart(chart_type):
    chart = get_test_chart(chart_type)
    # chart.options.scales = {'yAxes': [{'stacked': True}]}
    # chart.set_height(100)

    chart.data.labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                         'Friday', 'Saturday', 'Sunday']

    set_a = chart.data.new_dataset('set_a')
    set_a.data = [12, 19, 3, 17, 6, 3, 7]
    # set_a.set_color(0xFF, 0x8C, 0x8D, 0.8)

    set_b = chart.data.new_dataset('set_b')
    set_b.data = [2, 29, 5, 5, 2, 3, 10]
    # set_b.set_color(0xFF, 0xCE, 0x56, 0.8)
    # set_b.fill = False

    set_c = chart.data.new_dataset('set_c')
    set_c.data = [55, 12, 2, 20, 18, 6, 22]
    # set_c.set_color(0x36, 0xA2, 0xEB, 0.8)

    chart.randomize_colors()
    chart.draw()


def test2_chart(chart_type):
    import random

    chart = get_test_chart(chart_type)

    set_a = chart.data.new_dataset('set_a')
    # set_a.set_color(0xFF, 0x8C, 0x8D, 0.8)
    set_a.data = []
    for idx in range(1, 10):
        x = random.randint(1, 40)
        y = random.randint(1, 10)
        r = random.randint(1, 20)
        value = {'x': x, 'y': y, 'r': r}
        set_a.data.append(value)

    set_b = chart.data.new_dataset('set_b')
    # set_b.set_color(0xFF, 0xCE, 0x56, 0.8)
    set_b.data = []
    for idx in range(1, 10):
        x = random.randint(1, 40)
        y = random.randint(1, 10)
        r = random.randint(1, 20)
        value = {'x': x, 'y': y, 'r': r}
        set_b.data.append(value)

    set_c = chart.data.new_dataset('set_c')
    # set_c.set_color(0x36, 0xA2, 0xEB, 0.8)
    set_c.data = []
    for idx in range(1, 10):
        x = random.randint(1, 40)
        y = random.randint(1, 10)
        r = random.randint(1, 20)
        value = {'x': x, 'y': y, 'r': r}
        set_c.data.append(value)

    chart.randomize_colors()
    chart.draw()


def test3_chart(chart_type):
    chart = get_test_chart(chart_type)

    chart.data.labels = ['A', 'B', 'C', 'D', 'E', 'F']

    set_a = chart.data.new_dataset('set_a')
    set_a.data = [100, 20, 50, 35, 70, 20]
    # set_a.backgroundColor = ["#446119", "#547720", "#6b942d",
    #                          "#7cad31", "#86c12b", "#8dd61c"]

    chart.randomize_colors()
    chart.draw()


def test4_chart(chart_type):
    chart = get_test_chart(chart_type)

    chart.data.labels = ['A', 'B', 'C']

    set_a = chart.data.new_dataset('set_a')
    set_a.data = [100, 20, 50]
    # set_a.backgroundColor = ["#560764", "#1F6CB0", "#F98B60"]

    set_b = chart.data.new_dataset('set_b')
    set_b.data = [50, 30, 80]
    # set_b.backgroundColor = ["#913175", "#70A3C4", "#FFC057"]
    set_b.fill = False

    set_c = chart.data.new_dataset('set_c')
    set_c.data = [40, 20, 10]
    # set_c.backgroundColor = ["#DD5B82", "#E7E8F5", "#FFE084"]

    chart.randomize_colors()
    chart.draw()


for ct_type in test1_types:
    test1_chart(ct_type)

for ct_type in test2_types:
    test2_chart(ct_type)

for ct_type in test3_types:
    test3_chart(ct_type)

for ct_type in test4_types:
    test4_chart(ct_type)
