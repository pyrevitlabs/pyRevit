"""Provide access to output window and its functionality.

This module provides access to the output window for the currently running
pyRevit command. The proper way to access this wrapper object is through
the :func:`get_output` of :mod:`pyrevit.script` module. This method, in return
uses the `pyrevit.output` module to get access to the output wrapper.

Example:
    >>> from pyrevit import script
    >>> output = script.get_output()

Here is the source of :func:`pyrevit.script.get_output`. As you can see this
functions calls the :func:`pyrevit.output.get_output` to receive the
output wrapper.

.. literalinclude:: ../../../pyrevitlib/pyrevit/script.py
    :pyobject: get_output
"""

from __future__ import print_function
import os.path as op
import itertools

from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils import logger
from pyrevit.coreutils import markdown, charts
from pyrevit.coreutils import envvars
from pyrevit.runtime.types import ScriptConsoleManager
from pyrevit.output import linkmaker
from pyrevit.userconfig import user_config
from pyrevit import DB


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


DEFAULT_STYLESHEET_NAME = 'outputstyles.css'


def docclosing_eventhandler(sender, args):  #pylint: disable=W0613
    """Close all output window on document closing."""
    ScriptConsoleManager.CloseActiveOutputWindows()


def setup_output_closer():
    """Setup document closing event listener."""
    HOST_APP.app.DocumentClosing += \
        framework.EventHandler[DB.Events.DocumentClosingEventArgs](
            docclosing_eventhandler
            )


def set_stylesheet(stylesheet):
    """Set active css stylesheet used by output window.

    Args:
        stylesheet (str): full path to stylesheet file
    """
    if op.isfile(stylesheet):
        envvars.set_pyrevit_env_var(envvars.OUTPUT_STYLESHEET_ENVVAR,
                                    stylesheet)
        user_config.output_stylesheet = stylesheet


def get_stylesheet():
    """Return active css stylesheet used by output window."""
    return envvars.get_pyrevit_env_var(envvars.OUTPUT_STYLESHEET_ENVVAR)


def get_default_stylesheet():
    """Return default css stylesheet used by output window."""
    return op.join(op.dirname(__file__), DEFAULT_STYLESHEET_NAME)


def reset_stylesheet():
    """Reset active stylesheet to default."""
    envvars.set_pyrevit_env_var(envvars.OUTPUT_STYLESHEET_ENVVAR,
                                get_default_stylesheet())


# setup output window stylesheet
if not EXEC_PARAMS.doc_mode:
    active_stylesheet = \
        user_config.output_stylesheet or get_default_stylesheet()
    set_stylesheet(active_stylesheet)


class PyRevitOutputWindow(object):
    """Wrapper to interact with the output window."""

    @property
    def window(self):
        """``PyRevitLabs.PyRevit.Runtime.ScriptConsole``: Return output window object."""
        return EXEC_PARAMS.window_handle

    @property
    def renderer(self):
        """Return html renderer inside output window.

        Returns:
            ``System.Windows.Forms.WebBrowser`` (In current implementation)
        """
        if self.window:
            return self.window.renderer

    @property
    def output_id(self):
        """str: Return id of the output window.

        In current implementation, Id of output window is equal to the
        unique id of the pyRevit command it belongs to. This means that all
        output windows belonging to the same pyRevit command, will have
        identical output_id values.
        """
        if self.window:
            return self.window.OutputId

    @property
    def output_uniqueid(self):
        """str: Return unique id of the output window.

        In current implementation, unique id of output window is a GUID string
        generated when the output window is opened. This id is unique to the
        instance of output window.
        """
        if self.window:
            return self.window.OutputUniqueId

    @property
    def is_closed_by_user(self):
        return self.window.ClosedByUser

    @property
    def debug_mode(self):
        """Set debug mode on output window and stream.

        This will cause the output window to print information about the
        buffer stream and other aspects of the output window mechanism.
        """
        return EXEC_PARAMS.output_stream.PrintDebugInfo

    @debug_mode.setter
    def debug_mode(self, value):
        EXEC_PARAMS.output_stream.PrintDebugInfo = value

    def _get_head_element(self):
        return self.renderer.Document.GetElementsByTagName('head')[0]

    def _get_body_element(self):
        return self.renderer.Document.GetElementsByTagName('body')[0]

    def self_destruct(self, seconds):
        """Set self-destruct (close window) timer.

        Args:
            seconds (int): number of seconds after which window is closed.
        """
        if self.window:
            self.window.SelfDestructTimer(seconds)

    def inject_to_head(self, element_tag, element_contents, attribs=None):
        """Inject html element to current html head of the output window.

        Args:
            element_tag (str): html tag of the element e.g. 'div'
            element_contents (str): html code of the element contents
            attribs (:obj:`dict`): dictionary of attribute names and value

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.inject_to_head('script',
                                      '',   # no script since it's a link
                                      {'src': js_script_file_path})
        """
        html_element = self.renderer.Document.CreateElement(element_tag)
        if element_contents:
            html_element.InnerHtml = element_contents

        if attribs:
            for attribute, value in attribs.items():
                html_element.SetAttribute(attribute, value)

        # inject the script into head
        head_el = self._get_head_element()
        head_el.AppendChild(html_element)

    def inject_to_body(self, element_tag, element_contents, attribs=None):
        """Inject html element to current html body of the output window.

        Args:
            element_tag (str): html tag of the element e.g. 'div'
            element_contents (str): html code of the element contents
            attribs (:obj:`dict`): dictionary of attribute names and value

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.inject_to_body('script',
                                      '',   # no script since it's a link
                                      {'src': js_script_file_path})
        """
        html_element = self.renderer.Document.CreateElement(element_tag)
        if element_contents:
            html_element.InnerHtml = element_contents

        if attribs:
            for attribute, value in attribs.items():
                html_element.SetAttribute(attribute, value)

        # inject the script into body
        body_el = self._get_body_element()
        body_el.AppendChild(html_element)

    def inject_script(self, script_code, attribs=None, body=False):
        """Inject script tag into current head (or body) of the output window.

        Args:
            script_code (str): javascript code
            attribs (:obj:`dict`): dictionary of attribute names and value
            body (bool, optional): injects script into body instead of head

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.inject_script('',   # no script since it's a link
                                     {'src': js_script_file_path})
        """
        if body:
            self.inject_to_body('script', script_code, attribs=attribs)
        else:
            self.inject_to_head('script', script_code, attribs=attribs)

    def add_style(self, style_code, attribs=None):
        """Inject style tag into current html head of the output window.

        Args:
            style_code (str): css styling code
            attribs (:obj:`dict`): dictionary of attribute names and value

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.add_style('body { color: blue; }')
        """
        self.inject_to_head('style', style_code, attribs=attribs)

    def get_head_html(self):
        """str: Return inner code of html head element."""
        return self._get_head_element().InnerHtml

    def set_title(self, new_title):
        """Set window title to the new title."""
        if self.window:
            self.window.Title = new_title

    def set_width(self, width):
        """Set window width to the new width."""
        if self.window:
            self.window.Width = width

    def set_height(self, height):
        """Set window height to the new height."""
        if self.window:
            self.window.Height = height

    def set_font(self, font_family, font_size):
        """Set window font family to the new font family and size.

        Args:
            font_family (str): font family name e.g. 'Courier New'
            font_size (int): font size e.g. 16
        """
        self.renderer.Font = \
            framework.Drawing.Font(font_family,
                                   font_size,
                                   framework.Drawing.FontStyle.Regular,
                                   framework.Drawing.GraphicsUnit.Point)

    def resize(self, width, height):
        """Resize window to the new width and height."""
        self.set_width(width)
        self.set_height(height)

    def center(self):
        """Center the output window on the screen"""
        screen_area = HOST_APP.proc_screen_workarea
        left = \
            (abs(screen_area.Right - screen_area.Left) / 2) \
                - (self.get_width() / 2)
        top = \
            (abs(screen_area.Top - screen_area.Bottom) / 2) \
                - (self.get_height() / 2)
        self.window.Left = left
        self.window.Top = top

    def get_title(self):
        """str: Return current window title."""
        if self.window:
            return self.window.Text

    def get_width(self):
        """int: Return current window width."""
        if self.window:
            return self.window.Width

    def get_height(self):
        """int: Return current window height."""
        if self.window:
            return self.window.Height

    def close(self):
        """Close the window."""
        if self.window:
            self.window.Close()

    def close_others(self, all_open_outputs=False):
        """Close all other windows that belong to the current command.

        Args:
            all_open_outputs (bool): Close all any other windows if True
        """
        if all_open_outputs:
            ScriptConsoleManager.CloseActiveOutputWindows(self.window)
        else:
            ScriptConsoleManager.CloseActiveOutputWindows(self.window,
                                                         self.output_id)

    def hide(self):
        """Hide the window."""
        if self.window:
            self.window.Hide()

    def show(self):
        """Show the window."""
        if self.window:
            self.window.Show()

    def lock_size(self):
        """Lock window size."""
        if self.window:
            self.window.LockSize()

    def unlock_size(self):
        """Unock window size."""
        if self.window:
            self.window.UnlockSize()

    def freeze(self):
        """Freeze output content update."""
        if self.window:
            self.window.Freeze()

    def unfreeze(self):
        """Unfreeze output content update."""
        if self.window:
            self.window.Unfreeze()

    def save_contents(self, dest_file):
        """Save html code of the window.

        Args:
            dest_file (str): full path of the destination html file
        """
        if self.renderer:
            html = \
                self.renderer.Document.Body.OuterHtml.encode('ascii', 'ignore')
            doc_txt = self.renderer.DocumentText
            full_html = doc_txt.lower().replace('<body></body>', html)
            with open(dest_file, 'w') as output_file:
                output_file.write(full_html)

    def open_url(self, dest_url):
        """Open url page in output window.

        Args:
            dest_url (str): web url of the target page
        """
        if self.renderer:
            self.renderer.Navigate(dest_url, False)

    def open_page(self, dest_file):
        """Open html page in output window.

        Args:
            dest_file (str): full path of the target html file
        """
        self.show()
        self.open_url('file:///' + dest_file)

    def update_progress(self, cur_value, max_value):
        """Activate and update the output window progress bar.

        Args:
            cur_value (float): current progress value e.g. 50
            max_value (float): total value e.g. 100

        Example:
            >>> output = pyrevit.output.get_output()
            >>> for i in range(100):
            >>>     output.update_progress(i, 100)
        """
        if self.window:
            self.window.UpdateActivityBar(cur_value, max_value)

    def reset_progress(self):
        """Reset output window progress bar to zero."""
        if self.window:
            self.window.UpdateActivityBar(0, 1)

    def hide_progress(self):
        """Hide output window progress bar."""
        if self.window:
            self.window.SetActivityBarVisibility(False)

    def unhide_progress(self):
        """Unhide output window progress bar."""
        if self.window:
            self.window.SetActivityBarVisibility(True)

    def indeterminate_progress(self, state):
        """Show or hide indeterminate progress bar. """
        if self.window:
            self.window.UpdateActivityBar(state)

    def show_logpanel(self):
        """Show output window logging panel."""
        if self.window:
            self.window.SetActivityBarVisibility(True)

    def hide_logpanel(self):
        """Hide output window logging panel."""
        if self.window:
            self.show_logpanel()
            self.window.SetActivityBarVisibility(False)

    def log_debug(self, message):
        """Report DEBUG message into output logging panel."""
        if self.window:
            self.show_logpanel()
            self.window.activityBar.ConsoleLog(message)

    def log_success(self, message):
        """Report SUCCESS message into output logging panel."""
        if self.window:
            self.show_logpanel()
            self.window.activityBar.ConsoleLogOK(message)

    def log_info(self, message):
        """Report INFO message into output logging panel."""
        if self.window:
            self.show_logpanel()
            self.window.activityBar.ConsoleLogInfo(message)

    def log_warning(self, message):
        """Report WARNING message into output logging panel."""
        if self.window:
            self.show_logpanel()
            self.window.activityBar.ConsoleLogWarning(message)

    def log_error(self, message):
        """Report ERROR message into output logging panel."""
        if self.window:
            self.show_logpanel()
            self.window.activityBar.ConsoleLogError(message)

    def set_icon(self, iconpath):
        """Sets icon on the output window."""
        if self.window:
            self.window.SetIcon(iconpath)

    def reset_icon(self):
        """Sets icon on the output window."""
        if self.window:
            self.window.ResetIcon()

    @staticmethod
    def print_html(html_str):
        """Add the html code to the output window.

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.print_html('<strong>Title</strong>')
        """
        print(coreutils.prepare_html_str(html_str),
              end="")

    @staticmethod
    def print_code(code_str):
        """Print code to the output window with special formatting.

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.print_code('value = 12')
        """
        code_div = '<div class="code">{}</div>'
        print(
            coreutils.prepare_html_str(
                code_div.format(
                    code_str.replace('    ', '&nbsp;'*4)
                    )
                ),
            end=""
            )

    @staticmethod
    def print_md(md_str):
        """Process markdown code and print to output window.

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.print_md('### Title')
        """
        tables_ext = 'pyrevit.coreutils.markdown.extensions.tables'
        markdown_html = markdown.markdown(md_str, extensions=[tables_ext])
        markdown_html = markdown_html.replace('\n', '').replace('\r', '')
        html_code = coreutils.prepare_html_str(markdown_html)
        print(html_code, end="")

    def print_table(self, table_data, columns=None, formats=None,
                    title='', last_line_style=''):
        """Print provided data in a table in output window.

        Args:
            table_data (:obj:`list` of iterables): 2D array of data
            title (str): table title
            columns (:obj:`list` str): list of column names
            formats (:obj:`list` str): column data formats
            last_line_style (str): css style of last row

        Example:
            >>> data = [
            ... ['row1', 'data', 'data', 80 ],
            ... ['row2', 'data', 'data', 45 ],
            ... ]
            >>> output.print_table(
            ... table_data=data,
            ... title="Example Table",
            ... columns=["Row Name", "Column 1", "Column 2", "Percentage"],
            ... formats=['', '', '', '{}%'],
            ... last_line_style='color:red;'
            ... )
        """
        if not columns:
            columns = []
        if not formats:
            formats = []

        if last_line_style:
            self.add_style('tr:last-child {{ {style} }}'
                           .format(style=last_line_style))

        zipper = itertools.izip_longest #pylint: disable=E1101
        adjust_base_col = '|'
        adjust_extra_col = ':---|'
        base_col = '|'
        extra_col = '{data}|'

        # find max column count
        max_col = max([len(x) for x in table_data])

        header = ''
        if columns:
            header = base_col
            for idx, col_name in zipper(range(max_col), columns, fillvalue=''): #pylint: disable=W0612
                header += extra_col.format(data=col_name)

            header += '\n'

        justifier = adjust_base_col
        for idx in range(max_col):
            justifier += adjust_extra_col

        justifier += '\n'

        rows = ''
        for entry in table_data:
            row = base_col
            for idx, attrib, attr_format \
                    in zipper(range(max_col), entry, formats, fillvalue=''):
                if attr_format:
                    value = attr_format.format(attrib)
                else:
                    value = attrib
                row += extra_col.format(data=value)
            rows += row + '\n'

        table = header + justifier + rows
        self.print_md('### {title}'.format(title=title))
        self.print_md(table)

    def print_image(self, image_path):
        r"""Prints given image to the output.

        Example:
            >>> output = pyrevit.output.get_output()
            >>> output.print_image(r'C:\image.gif')
        """
        self.print_html(
            "<span><img src=\"file:///{0}\"></span>".format(
                image_path
            )
        )

    def insert_divider(self, level=''):
        """Add horizontal rule to the output window."""
        self.print_md('%s\n-----' % level)

    def next_page(self):
        """Add hidden next page tag to the output window.

        This is helpful to silently separate the output to multiple pages
        for better printing.
        """
        self.print_html('<div class="nextpage"></div><div>&nbsp</div>')

    @staticmethod
    def linkify(element_ids, title=None):
        """Create clickable link for the provided element ids.

        This method, creates the link but does not print it directly.

        Args:
            element_ids (`ElementId`) or
            element_ids (:obj:`list` of `ElementId`): single or multiple ids
            title (str): tile of the link. defaults to list of element ids

        Example:
            >>> output = pyrevit.output.get_output()
            >>> for idx, elid in enumerate(element_ids):
            >>>     print('{}: {}'.format(idx+1, output.linkify(elid)))
        """
        return coreutils.prepare_html_str(
            linkmaker.make_link(element_ids, contents=title)
            )

    def make_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return chart object."""
        return charts.PyRevitOutputChart(self, version=version)

    def make_line_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return line chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.LINE_CHART,
            version=version
            )

    def make_stacked_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return stacked chart object."""
        chart = charts.PyRevitOutputChart(
            self,
            chart_type=charts.LINE_CHART,
            version=version
            )
        chart.options.scales = {'yAxes': [{'stacked': True, }]}
        return chart

    def make_bar_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return bar chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.BAR_CHART,
            version=version
            )

    def make_radar_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return radar chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.RADAR_CHART,
            version=version
            )

    def make_polar_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return polar chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.POLAR_CHART,
            version=version
            )

    def make_pie_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return pie chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.PIE_CHART,
            version=version
            )

    def make_doughnut_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return dougnut chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.DOUGHNUT_CHART,
            version=version
            )

    def make_bubble_chart(self, version=None):
        """:obj:`PyRevitOutputChart`: Return bubble chart object."""
        return charts.PyRevitOutputChart(
            self,
            chart_type=charts.BUBBLE_CHART,
            version=version
            )


def get_output():
    """:obj:`pyrevit.output.PyRevitOutputWindow` : Return output window."""
    return PyRevitOutputWindow()
