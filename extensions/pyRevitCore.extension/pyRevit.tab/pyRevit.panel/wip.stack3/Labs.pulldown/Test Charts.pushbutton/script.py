import os
import os.path as op
from pyrevit import MAIN_LIB_DIR

from scriptutils import this_script
this_script.output.set_width(500)

def get_head():
    return this_script.output.__winhandle__.txtStdOut.Document.GetElementsByTagName('head')[0]


def make_script_element(script):
    scr_el = this_script.output.__winhandle__.txtStdOut.Document.CreateElement("<script></script>")
    if script:
        scr_el.InnerHtml = script
    return scr_el


def make_canvas_element(canvas_id):
    print('\nTesting {}...'.format(canvas_id))
    canvas = """<canvas id="{}"></canvas><br/>""".format(canvas_id)
    this_script.output.print_html(canvas)


print('Testing Charts.js charts...')


head = get_head()
# setup charts.js header
charts_sc_el = make_script_element('')
charts_path = op.join(MAIN_LIB_DIR, 'pyrevit', 'coreutils', 'console', 'charts', 'Chart.js')
charts_sc_el.SetAttribute('src', charts_path)
head.AppendChild(charts_sc_el)


make_canvas_element('linechart')
line_chart_script = """
var ctx = document.getElementById('linechart').getContext('2d');
var myChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['M', 'T', 'W', 'T', 'F', 'S', 'S'],
    datasets: [{
      label: 'apples',
      data: [12, 19, 3, 17, 6, 3, 7],
      backgroundColor: "rgba(153,255,51,0.4)"
    }, {
      label: 'oranges',
      data: [2, 29, 5, 5, 2, 3, 10],
      backgroundColor: "rgba(255,153,0,0.4)"
    }]
  }
});
"""
head.AppendChild(make_script_element(line_chart_script))


make_canvas_element('barchart')
bar_chart_script = """
var ctx = document.getElementById("barchart").getContext('2d');
var myChart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ["M", "T", "W", "R", "F", "S", "S"],
    datasets: [{
      label: 'apples',
      data: [12, 19, 3, 17, 28, 24, 7],
      backgroundColor: "rgba(153,255,51,0.4)"
    }, {
      label: 'oranges',
      data: [30, 29, 5, 5, 20, 3, 10],
      backgroundColor: "rgba(255,153,0,0.4)"
    }]
  }
});
"""
head.AppendChild(make_script_element(bar_chart_script))


make_canvas_element('polarchart')
polar_chart_script = """
var ctx = document.getElementById("polarchart").getContext('2d');
var myChart = new Chart(ctx, {
  type: 'polarArea',
  data: {
    labels: ["M", "T", "W", "T", "F", "S", "S"],
    datasets: [{
      backgroundColor: [
        "#2ecc71",
        "#3498db",
        "#95a5a6",
        "#9b59b6",
        "#f1c40f",
        "#e74c3c",
        "#34495e"
      ],
      data: [12, 19, 3, 17, 28, 24, 7]
    }]
  }
});
"""
head.AppendChild(make_script_element(polar_chart_script))


make_canvas_element('piechart')
pie_chart_script = """
var ctx = document.getElementById("piechart").getContext('2d');
var myChart = new Chart(ctx, {
  type: 'pie',
  data: {
    labels: ["M", "T", "W", "T", "F", "S", "S"],
    datasets: [{
      backgroundColor: [
        "#2ecc71",
        "#3498db",
        "#95a5a6",
        "#9b59b6",
        "#f1c40f",
        "#e74c3c",
        "#34495e"
      ],
      data: [12, 19, 3, 17, 28, 24, 7]
    }]
  }
});
"""
head.AppendChild(make_script_element(pie_chart_script))

# this_script.output.__winhandle__.txtStdOut.Document.InvokeScript("drawStuff")
