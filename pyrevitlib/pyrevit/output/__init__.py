from __future__ import print_function

from pyrevit import EXEC_PARAMS
from pyrevit.framework import AppDomain
from pyrevit.framework import Drawing, Windows
from pyrevit.coreutils import prepare_html_str
from pyrevit.coreutils import markdown, charts
from pyrevit.coreutils.emoji import emojize
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.loadertypes import EnvDictionaryKeys
from pyrevit.output import urlscheme


logger = get_logger(__name__)


class PyRevitOutputMgr:
    def __init__(self):
        pass

    @staticmethod
    def _get_all_open_output_windows():
        output_list_entryname = EnvDictionaryKeys.outputWindows
        output_list = AppDomain.CurrentDomain.GetData(output_list_entryname)
        if output_list:
            return list(output_list)
        else:
            return []

    @staticmethod
    def _reset_outputwindow_cache():
        output_list_entryname = EnvDictionaryKeys.outputWindows
        return AppDomain.CurrentDomain.SetData(output_list_entryname, None)

    @staticmethod
    def get_all_outputs(command=None):
        open_outputs = PyRevitOutputMgr._get_all_open_output_windows()
        if command:
            return [x for x in open_outputs if x.OutputId == command]
        else:
            return open_outputs

    @staticmethod
    def close_all_outputs():
        for output_wnd in PyRevitOutputMgr._get_all_open_output_windows():
            output_wnd.Close()
        PyRevitOutputMgr._reset_outputwindow_cache()


class PyRevitOutputWindow:
    """Wrapper to interact with the output output window."""

    def __init__(self):
        """Sets up the wrapper from the input dot net window handler"""
        if EXEC_PARAMS.window_handle:
            EXEC_PARAMS.window_handle.UrlHandler = \
                urlscheme.handle_scheme_url

    @property
    def window(self):
        return EXEC_PARAMS.window_handle

    @property
    def renderer(self):
        if self.window:
            return self.window.renderer

    def _get_head_element(self):
        return self.renderer.Document.GetElementsByTagName('head')[0]

    def self_destruct(self, seconds):
        if self.window:
            self.window.SelfDestructTimer(seconds)

    def inject_to_head(self, element_tag, element_contents, attribs=None):
        html_element = self.renderer.Document.CreateElement(element_tag)
        if element_contents:
            html_element.InnerHtml = element_contents

        if attribs:
            for attribute, value in attribs.items():
                html_element.SetAttribute(attribute, value)

        # inject the script into head
        head_el = self._get_head_element()
        head_el.AppendChild(html_element)

    def inject_script(self, script_code, attribs=None):
        self.inject_to_head("<script></script>", script_code, attribs=attribs)

    def add_style(self, style_code, attribs=None):
        self.inject_to_head("<style></style>", style_code, attribs=attribs)

    def get_head_html(self):
        return self._get_head_element().InnerHtml

    def set_title(self, new_title):
        if self.window:
            self.window.Text = new_title

    def set_width(self, width):
        if self.window:
            self.window.Width = width

    def set_height(self, height):
        if self.window:
            self.window.Height = height

    def set_font(self, font_family_name, font_size):
        # noinspection PyUnresolvedReferences
        self.renderer.Font = \
            Drawing.Font(font_family_name,
                         font_size,
                         Drawing.FontStyle.Regular,
                         Drawing.GraphicsUnit.Point)

    def resize(self, width, height):
        self.set_width(width)
        self.set_height(height)

    def get_title(self):
        if self.window:
            return self.window.Text

    def get_width(self):
        if self.window:
            return self.window.Width

    def get_height(self):
        if self.window:
            return self.window.Height

    def close(self):
        if self.window:
            self.window.Close()

    def close_others(self, all_open_outputs=False):
        if all_open_outputs:
            output_wnds = PyRevitOutputMgr.get_all_outputs()
        elif self.window:
            output_wnds = PyRevitOutputMgr.\
                get_all_outputs(command=self.window.OutputId)

        if output_wnds:
            for output_wnd in output_wnds:
                if self.window and output_wnd != self.window:
                    output_wnd.Close()

    def hide(self):
        if self.window:
            self.window.Hide()

    def show(self):
        if self.window:
            self.window.Show()

    def lock_size(self):
        if self.window:
            self.window.LockSize()

    def save_contents(self, dest_file):
        if self.renderer:
            html = \
                self.renderer.Document.Body.OuterHtml.encode('ascii', 'ignore')
            doc_txt = self.renderer.DocumentText
            full_html = doc_txt.lower().replace('<body></body>', html)
            with open(dest_file, 'w') as output_file:
                output_file.write(full_html)

    def open_url(self, dest_url):
        if self.renderer:
            self.renderer.Navigate(dest_url, False)

    def update_progress(self, cur_value, max_value):
        if self.window:
            self.window.UpdateProgressBar(cur_value, max_value)

    def reset_progress(self):
        if self.window:
            self.window.UpdateProgressBar(0, 1)

    @staticmethod
    def emojize(md_str):
        print(emojize(md_str), end="")

    @staticmethod
    def print_html(html_str):
        print(prepare_html_str(emojize(html_str)), end="")

    @staticmethod
    def print_code(code_str):
        nbsp = '&nbsp;'
        code_div = '<div style="font-family:courier new;' \
                   'border-style: solid;' \
                   'border-width:0 0 0 5;' \
                   'border-color:#87b012;' \
                   'background:#ececec;' \
                   'color:#3e3d3d;' \
                   'line-height: 150%;' \
                   'padding:10;' \
                   'margin:10 0 10 0">' \
                   '{}' \
                   '</div>'

        print(prepare_html_str(code_div.format(code_str.replace('    ',
                                                                nbsp*4))),
              end="")

    @staticmethod
    def print_md(md_str):
        tables_ext = 'pyrevit.coreutils.markdown.extensions.tables'
        markdown_html = markdown.markdown(md_str, extensions=[tables_ext])
        markdown_html = markdown_html.replace('\n', '').replace('\r', '')
        html_code = emojize(prepare_html_str(markdown_html))
        print(html_code, end="")

    def insert_divider(self):
        self.print_md('-----')

    def next_page(self):
        self.print_html('<div style="page-break-after:always;">'
                        '</div>'
                        '<div>'
                        '&nbsp'
                        '</div>')

    @staticmethod
    def linkify(*args):
        return prepare_html_str(urlscheme.make_url(args))

    def make_chart(self):
        return charts.PyRevitOutputChart(self)

    def make_line_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.LINE_CHART)

    def make_stacked_chart(self):
        chart = charts.PyRevitOutputChart(self, chart_type=charts.LINE_CHART)
        chart.options.scales = {'yAxes': [{'stacked': True, }]}
        return chart

    def make_bar_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.BAR_CHART)

    def make_radar_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.RADAR_CHART)

    def make_polar_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.POLAR_CHART)

    def make_pie_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.PIE_CHART)

    def make_doughnut_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.DOUGHNUT_CHART)

    def make_bubble_chart(self):
        return charts.PyRevitOutputChart(self, chart_type=charts.BUBBLE_CHART)


def get_output():
    return PyRevitOutputWindow()
