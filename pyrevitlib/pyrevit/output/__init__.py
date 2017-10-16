from __future__ import print_function

from pyrevit import EXEC_PARAMS
from pyrevit.platform import AppDomain
from pyrevit.platform import Drawing, Windows
from pyrevit.coreutils import prepare_html_str
from pyrevit.coreutils import rvtprotocol, markdown, charts
from pyrevit.coreutils.emoji import emojize
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.loadertypes import EnvDictionaryKeys


logger = get_logger(__name__)


class PyRevitOutputMgr:
    def __init__(self):
        pass

    @staticmethod
    def _get_all_open_output_windows():
        output_list_entryname = EnvDictionaryKeys.outputWindows
        return list(AppDomain.CurrentDomain.GetData(output_list_entryname))

    @staticmethod
    def _reset_outputwindow_cache():
        output_list_entryname = EnvDictionaryKeys.outputWindows
        return AppDomain.CurrentDomain.SetData(output_list_entryname, None)

    @staticmethod
    def get_all_outputs(command=None):
        if command:
            return [x for x in PyRevitOutputMgr._get_all_open_output_windows()
                    if x.OutputId == command]
        else:
            return PyRevitOutputMgr._get_all_open_output_windows()

    @staticmethod
    def close_all_outputs():
        for output_wnd in PyRevitOutputMgr._get_all_open_output_windows():
            output_wnd.Close()

        _reset_outputwindow_cache()


class PyRevitOutputWindow:
    """Wrapper to interact with the output output window."""

    def __init__(self, window_handle):
        """Sets up the wrapper from the input dot net window handler"""
        EXEC_PARAMS.window_handle.UrlHandler = self._handle_protocol_url

    @property
    def renderer(self):
        return EXEC_PARAMS.window_handle.renderer

    @staticmethod
    def _handle_protocol_url(url):
        """
        This is a function assgined to the ScriptOutput.UrlHandler which
         is a delegate. Everytime WebBrowser is asked to handle a link with
         a protocol other than http, it'll call this function.
        System.Windows.Forms.WebBrowser returns a string with misc stuff
         before the actual link, when it can't recognize the protocol.
        This function cleans up the link for the pyRevit protocol handler.

        Args:
            url (str): the url coming from Forms.WebBrowser
        """
        try:
            if rvtprotocol.PROTOCOL_NAME in url:
                cleaned_url = url.split(rvtprotocol.PROTOCOL_NAME)[1]
                # get rid of the slash at the end
                if cleaned_url.endswith('/'):
                    cleaned_url = cleaned_url.replace('/', '')

                # process cleaned data
                rvtprotocol.process_url(cleaned_url)
        except Exception as exec_err:
            logger.error('Error handling link | {}'.format(exec_err))

    def _get_head_element(self):
        return self.renderer.Document.GetElementsByTagName('head')[0]

    def self_destruct(self, seconds):
        EXEC_PARAMS.window_handle.SelfDestructTimer(seconds * 1000)

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
        EXEC_PARAMS.window_handle.Text = new_title

    def set_width(self, width):
        EXEC_PARAMS.window_handle.Width = width

    def set_height(self, height):
        EXEC_PARAMS.window_handle.Height = height

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
        return EXEC_PARAMS.window_handle.Text

    def get_width(self):
        return EXEC_PARAMS.window_handle.Width

    def get_height(self):
        return EXEC_PARAMS.window_handle.Height

    def close(self):
        EXEC_PARAMS.window_handle.Close()

    def close_others(self, all_open_outputs=False):
        if all_open_outputs:
            output_wnds = PyRevitOutputMgr.get_all_outputs()
        else:
            output_wnds = PyRevitOutputMgr.\
                get_all_outputs(command=EXEC_PARAMS.window_handle.OutputId)

        for output_wnd in output_wnds:
            if output_wnd != EXEC_PARAMS.window_handle:
                output_wnd.Close()

    def hide(self):
        EXEC_PARAMS.window_handle.Hide()

    def show(self):
        EXEC_PARAMS.window_handle.Show()

    def lock_size(self):
        EXEC_PARAMS.window_handle.LockSize()

    def save_contents(self, dest_file):
        html = self.renderer.Document.Body.OuterHtml.encode('ascii', 'ignore')
        doc_txt = self.renderer.DocumentText
        full_html = doc_txt.lower().replace('<body></body>', html)
        with open(dest_file, 'w') as output_file:
            output_file.write(full_html)

    def open_url(self, dest_url):
        self.renderer.Navigate(dest_url, False)

    def update_progress(self, cur_value, max_value):
        EXEC_PARAMS.window_handle.UpdateProgressBar(cur_value, max_value)

    def reset_progress(self):
        EXEC_PARAMS.window_handle.UpdateProgressBar(0, 1)

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
        return prepare_html_str(rvtprotocol.make_url(args))

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
    return PyRevitOutputWindow(EXEC_PARAMS.window_handle)
