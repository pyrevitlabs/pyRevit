from pyrevit.coreutils.console import charts

from scriptutils import this_script
this_script.output.set_width(500)


print('Testing Charts.js charts...')


test1_types = [charts.LINE_CHART,
               charts.BAR_CHART,
               charts.RADAR_CHART]

test2_types = [charts.BUBBLE_CHART]

test3_types = [charts.POLAR_CHART,
               charts.PIE_CHART,
               charts.DOUGHNUT_CHART]


def get_test_chart(chart_type):
    print('\nTesting {} charts...'.format(chart_type))
    chart = this_script.output.make_chart()
    chart.type = chart_type
    return chart


def test1_chart(chart_type):
    chart = get_test_chart(chart_type)

    chart.data.labels = ['M', 'T', 'W', 'T', 'F', 'S', 'S']

    apples = chart.data.new_dataset('apples')
    apples.data = [12, 19, 3, 17, 6, 3, 7]
    apples.set_background(153, 255, 51, 0.4)

    oranges = chart.data.new_dataset('oranges')
    oranges.data = [2, 29, 5, 5, 2, 3, 10]
    oranges.set_background(255, 153, 0, 0.4)
    oranges.fill = False

    pears = chart.data.new_dataset('pears')
    pears.data = [55, 12, 2, 20, 18, 6, 22]
    pears.set_background(0, 153, 255, 0.4)

    chart.draw()


def test2_chart(chart_type):
    chart = get_test_chart(chart_type)

    apples = chart.data.new_dataset('apples')
    apples.data = [{'x': 1, 'y': 2, 'r': 3}, {'x': 4, 'y': 5, 'r': 6}, {'x': 7, 'y': 8, 'r': 9}]
    apples.set_background(153, 255, 51, 0.4)

    oranges = chart.data.new_dataset('oranges')
    oranges.data = [{'x': 10, 'y': 11, 'r': 12}, {'x': 13, 'y': 14, 'r': 15}, {'x': 16, 'y': 17, 'r': 18}]
    oranges.set_background(255, 153, 0, 0.4)

    pears = chart.data.new_dataset('pears')
    pears.data = [{'x': 19, 'y': 20, 'r': 21}, {'x': 22, 'y': 23, 'r': 24}]
    pears.set_background(0, 153, 255, 0.4)

    chart.draw()


def test3_chart(chart_type):
    chart = get_test_chart(chart_type)

    chart.data.labels = ['Red', 'Blue', 'Green']

    apples = chart.data.new_dataset('apples')
    apples.data = [300, 20, 50]
    apples.backgroundColor = ["#FF6384", "#36A2EB", "#FFCE56"]

    oranges = chart.data.new_dataset('oranges')
    oranges.data = [50, 30, 80]
    oranges.backgroundColor = ["#FF6384", "#36A2EB", "#FFCE56"]

    pears = chart.data.new_dataset('pears')
    pears.data = [40, 20, 10]
    pears.backgroundColor = ["#FF6384", "#36A2EB", "#FFCE56"]

    chart.draw()


for ct_type in test1_types:
    test1_chart(ct_type)

for ct_type in test2_types:
    test2_chart(ct_type)

for ct_type in test3_types:
    test3_chart(ct_type)