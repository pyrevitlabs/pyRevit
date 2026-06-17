"""Provide access to output window and its functionality.

This module provides access to the output window for the currently running
pyRevit command. The proper way to access this wrapper object is through
the :func:`get_output` of :mod:`pyrevit.script` module. This method, in return
uses the `pyrevit.output` module to get access to the output wrapper.

Examples:
    ```python
    from pyrevit import script
    output = script.get_output()
    ```
"""

import os.path as op

from pyrevit import HOST_APP, EXEC_PARAMS, DB
from pyrevit import framework
from pyrevit.compat import PY3, safe_strtype
from pyrevit.coreutils import envvars
from pyrevit.coreutils import charts
from pyrevit.runtime.types import ScriptConsoleManager, ScriptOutput
from pyrevit.userconfig import user_config
from pyrevit.output import linkmaker
from pyrevit import coreutils

if PY3:
    from urllib.parse import quote as urlquote
else:
    from urllib import quote as urlquote


DEFAULT_STYLESHEET_NAME = 'outputstyles.css'


def docclosing_eventhandler(sender, args):
    """Close all output windows on document closing."""
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
active_stylesheet = user_config.output_stylesheet or get_default_stylesheet()
set_stylesheet(active_stylesheet)


class PyRevitOutputWindow(object):
    """Wrapper to interact with the output window.

    The output window is an html-rendering console that scripts print to. This
    wrapper exposes the documented Python API for it: printing (html, markdown,
    code, tables, images), drawing charts, managing window geometry and icon,
    driving the progress bar and log panel, and saving the rendered contents.

    Each wrapper binds at construction to one ``ScriptOutput``: the running
    command's own window, or the shared session window when no command is
    running (e.g. session load). The binding is cached for the wrapper's
    lifetime, so retaining the wrapper also retains the correct output for
    deferred and modeless callbacks after the command returns.

    Members not listed here are forwarded to the underlying ``ScriptOutput``
    .NET object.

    Examples:
        ```python
        from pyrevit import script
        output = script.get_output()
        output.set_title('My Report')
        output.print_md('### Results')
        for i in range(10):
            output.update_progress(i + 1, 10)
        ```
    """

    def __init__(self):
        # Deferred callbacks must retain the command output selected while the
        # command runtime is still active.
        self._runtime_output()

    def _runtime_output(self):
        """Return the runtime ``ScriptOutput`` this wrapper is bound to.

        The binding is resolved during wrapper construction and reused for the
        wrapper's lifetime.
        """
        out = self.__dict__.get('_rt_out')
        if out is None:
            # bind to the output of the running command; outside of a command
            # (e.g. during session load) fall back to the session output
            runtime = EXEC_PARAMS.script_runtime
            if runtime:
                out = getattr(runtime, 'OutputService', None)
            if out is None:
                out = ScriptOutput.GetDefault()
            object.__setattr__(self, '_rt_out', out)
        return out

    def __getattr__(self, name):
        """Forward unknown attribute reads to the bound ``ScriptOutput``."""
        return getattr(self._runtime_output(), name)

    def __setattr__(self, name, value):
        """Forward attribute writes to the bound ``ScriptOutput``.

        Private (``_``-prefixed) names and anything the runtime object rejects
        are stored on the wrapper instead.
        """
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        try:
            setattr(self._runtime_output(), name, value)
        except Exception:
            object.__setattr__(self, name, value)

    @property
    def window(self):
        """``PyRevitLabs.PyRevit.Runtime.ScriptConsole``: Return output window object."""
        return self._runtime_output().window

    @property
    def renderer(self):
        """Return html renderer inside output window.

        Returns:
            (System.Windows.Forms.WebBrowser): HTML renderer
        """
        return self._runtime_output().renderer

    @property
    def output_id(self):
        """str: Return id of the output window.

        In current implementation, Id of output window is equal to the
        unique id of the pyRevit command it belongs to. This means that all
        output windows belonging to the same pyRevit command, will have
        identical output_id values.
        """
        return self._runtime_output().output_id

    @property
    def output_uniqueid(self):
        """str: Return unique id of the output window.

        In current implementation, unique id of output window is a GUID string
        generated when the output window is opened. This id is unique to the
        instance of output window.
        """
        return self._runtime_output().output_uniqueid

    @property
    def is_closed_by_user(self):
        """Whether the window has been closed by the user."""
        return self._runtime_output().is_closed_by_user

    @property
    def last_line(self):
        """Last line of the output window."""
        return self._runtime_output().last_line

    @property
    def debug_mode(self):
        """Set debug mode on output window and stream.

        This will cause the output window to print information about the
        buffer stream and other aspects of the output window mechanism.
        """
        return self._runtime_output().debug_mode

    @debug_mode.setter
    def debug_mode(self, value):
        self._runtime_output().debug_mode = value

    def self_destruct(self, seconds):
        """Set self-destruct (close window) timer.

        Args:
            seconds (int): number of seconds after which window is closed.
        """
        return self._runtime_output().self_destruct(seconds)

    def inject_to_head(self, element_tag, element_contents, attribs=None):
        """Inject html element to current html head of the output window.

        Args:
            element_tag (str): html tag of the element e.g. 'div'
            element_contents (str): html code of the element contents
            attribs (:obj:`dict`): dictionary of attribute names and value

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.inject_to_head('script',
                                  '',   # no script since it's a link
                                  {'src': js_script_file_path})
            ```
        """
        return self._runtime_output().inject_to_head(
            element_tag,
            element_contents,
            attribs
            )

    def inject_to_body(self, element_tag, element_contents, attribs=None):
        """Inject html element to current html body of the output window.

        Args:
            element_tag (str): html tag of the element e.g. 'div'
            element_contents (str): html code of the element contents
            attribs (:obj:`dict`): dictionary of attribute names and value

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.inject_to_body('script',
                                  '',   # no script since it's a link
                                  {'src': js_script_file_path})
            ```
        """
        return self._runtime_output().inject_to_body(
            element_tag,
            element_contents,
            attribs
            )

    def inject_script(self, script_code, attribs=None, body=False):
        """Inject script tag into current head (or body) of the output window.

        Args:
            script_code (str): javascript code
            attribs (:obj:`dict`): dictionary of attribute names and value
            body (bool, optional): injects script into body instead of head

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.inject_script('',   # no script since it's a link
                                 {'src': js_script_file_path})
            ```
        """
        return self._runtime_output().inject_script(script_code, attribs, body)

    def add_style(self, style_code, attribs=None):
        """Inject style tag into current html head of the output window.

        Args:
            style_code (str): css styling code
            attribs (:obj:`dict`): dictionary of attribute names and value

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.add_style('body { color: blue; }')
            ```
        """
        return self._runtime_output().add_style(style_code, attribs)

    def get_head_html(self):
        """str: Return inner code of html head element."""
        return self._runtime_output().get_head_html()

    def set_title(self, new_title):
        """Set window title to the new title."""
        return self._runtime_output().set_title(new_title)

    def set_width(self, width):
        """Set window width to the new width."""
        return self._runtime_output().set_width(width)

    def set_height(self, height):
        """Set window height to the new height."""
        return self._runtime_output().set_height(height)

    def set_font(self, font_family, font_size):
        """Set window font family to the new font family and size.

        Args:
            font_family (str): font family name e.g. 'Courier New'
            font_size (int): font size e.g. 16
        """
        return self._runtime_output().set_font(font_family, font_size)

    def resize(self, width, height):
        """Resize window to the new width and height."""
        return self._runtime_output().resize(width, height)

    def center(self):
        """Center the output window on the screen."""
        return self._runtime_output().center()

    def get_title(self):
        """str: Return current window title."""
        return self._runtime_output().get_title()

    def get_width(self):
        """int: Return current window width."""
        return self._runtime_output().get_width()

    def get_height(self):
        """int: Return current window height."""
        return self._runtime_output().get_height()

    def close(self):
        """Close the window."""
        return self._runtime_output().close()

    def close_others(self, all_open_outputs=False):
        """Close all other windows that belong to the current command.

        Args:
            all_open_outputs (bool): Close all any other windows if True
        """
        return self._runtime_output().close_others(all_open_outputs)

    def hide(self):
        """Hide the window."""
        return self._runtime_output().hide()

    def show(self):
        """Show the window."""
        return self._runtime_output().show()

    def lock_size(self):
        """Lock window size."""
        return self._runtime_output().lock_size()

    def unlock_size(self):
        """Unlock window size."""
        return self._runtime_output().unlock_size()

    def freeze(self):
        """Freeze output content update."""
        return self._runtime_output().freeze()

    def unfreeze(self):
        """Unfreeze output content update."""
        return self._runtime_output().unfreeze()

    def save_contents(self, dest_file):
        """Save html code of the window.

        Args:
            dest_file (str): full path of the destination html file
        """
        return self._runtime_output().save_contents(dest_file)

    def open_url(self, dest_url):
        """Open url page in output window.

        Args:
            dest_url (str): web url of the target page
        """
        return self._runtime_output().open_url(dest_url)

    def open_page(self, dest_file):
        """Open html page in output window.

        Args:
            dest_file (str): full path of the target html file
        """
        return self._runtime_output().open_page(dest_file)

    def update_progress(self, cur_value, max_value):
        """Activate and update the output window progress bar.

        Args:
            cur_value (float): current progress value e.g. 50
            max_value (float): total value e.g. 100

        Examples:
            ```python
            output = pyrevit.output.get_output()
            for i in range(100):
                output.update_progress(i, 100)
            ```
        """
        return self._runtime_output().update_progress(cur_value, max_value)

    def reset_progress(self):
        """Reset output window progress bar to zero."""
        return self._runtime_output().reset_progress()

    def hide_progress(self):
        """Hide output window progress bar."""
        return self._runtime_output().hide_progress()

    def unhide_progress(self):
        """Unhide output window progress bar."""
        return self._runtime_output().unhide_progress()

    def indeterminate_progress(self, state):
        """Show or hide indeterminate progress bar."""
        return self._runtime_output().indeterminate_progress(state)

    def show_logpanel(self):
        """Show output window logging panel."""
        return self._runtime_output().show_logpanel()

    def hide_logpanel(self):
        """Hide output window logging panel."""
        return self._runtime_output().hide_logpanel()

    def log_debug(self, message):
        """Report DEBUG message into output logging panel."""
        return self._runtime_output().log_debug(safe_strtype(message))

    def log_success(self, message):
        """Report SUCCESS message into output logging panel."""
        return self._runtime_output().log_success(safe_strtype(message))

    def log_info(self, message):
        """Report INFO message into output logging panel."""
        return self._runtime_output().log_info(safe_strtype(message))

    def log_warning(self, message):
        """Report WARNING message into output logging panel."""
        return self._runtime_output().log_warning(safe_strtype(message))

    def log_error(self, message):
        """Report ERROR message into output logging panel."""
        return self._runtime_output().log_error(safe_strtype(message))

    def set_icon(self, iconpath):
        """Sets icon on the output window."""
        return self._runtime_output().set_icon(iconpath)

    def reset_icon(self):
        """Resets the output window icon to the default."""
        return self._runtime_output().reset_icon()

    def print_html(self, html_str):
        """Add the html code to the output window.

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_html('<strong>Title</strong>')
            ```
        """
        return self._runtime_output().print_html(safe_strtype(html_str))

    def print_code(self, code_str):
        """Print code to the output window with special formatting.

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_code('value = 12')
            ```
        """
        return self._runtime_output().print_code(safe_strtype(code_str))

    def print_md(self, md_str):
        """Process markdown code and print to output window.

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_md('### Title')
            ```
        """
        return self._runtime_output().print_md(safe_strtype(md_str))

    def print_table(self, table_data, columns=None, formats=None,
                    title='', last_line_style=''):
        """Print provided data in a table in output window.

        Args:
            table_data (list[iterable[Any]]): 2D array of data
            title (str): table title
            columns (list[str]): list of column names
            formats (list[str]): column data formats
            last_line_style (str): css style of last row

        Examples:
            ```python
            data = [
            ['row1', 'data', 'data', 80 ],
            ['row2', 'data', 'data', 45 ],
            ]
            output.print_table(
            table_data=data,
            title="Example Table",
            columns=["Row Name", "Column 1", "Column 2", "Percentage"],
            formats=['', '', '', '{}%'],
            last_line_style='color:red;'
            )
            ```
        """
        return self._runtime_output().print_table(
            table_data,
            columns,
            formats,
            title,
            last_line_style
            )

    def print_html_table(self, table_data, columns=None, formats=None,
                         title='', last_line_style='', **kwargs):
        """Print provided data in a HTML table in output window.

        The same window can output several tables, each with their own
        formatting options.

        Args:
            table_data (list[iterable[Any]]): 2D array of data
            title (str): table title
            columns (list[str]): list of column names
            formats (list[str]): column data formats using python string formatting
            last_line_style (str): css style of last row of data (NB applies to all tables in this output)
            **kwargs: extra formatting options:

                - column_head_align_styles (list[str]): css align-text styles for header row
                - column_data_align_styles (list[str]): css align-text styles for data rows
                - column_widths (list[str]): list of CSS widths in either px or %
                - column_vertical_border_style (str): CSS compact border definition
                - table_width_style (str): CSS width for the whole table, in either px or %
                - repeat_head_as_foot (bool): repeat the header row at the table foot (useful for long tables)
                - row_striping (bool): False to override the default white-grey row stripes and make all white

        Examples:
            ```python
            data = [
            ['row1', 'data', 'data', 80 ],
            ['row2', 'data', 'data', 45 ],
            ]
            output.print_html_table(
            table_data=data,
            title="Example Table",
            columns=["Row Name", "Column 1", "Column 2", "Percentage"],
            formats=['', '', '', '{}%'],
            last_line_style='color:red;',
            column_head_align_styles=["left", "left", "center", "right"],
            column_data_align_styles=["left", "left", "center", "right"],
            column_widths=["100px", "100px", "500px", "100px"],
            column_vertical_border_style="border:black solid 1px",
            table_width_style='width:100%',
            repeat_head_as_foot=True,
            row_striping=False
            )
            ```
        """
        return self._runtime_output().print_html_table(
            table_data,
            columns,
            formats,
            title,
            last_line_style,
            kwargs.get('column_head_align_styles', None),
            kwargs.get('column_data_align_styles', None),
            kwargs.get('column_widths', None),
            kwargs.get('column_vertical_border_style', None),
            kwargs.get('table_width_style', None),
            kwargs.get('repeat_head_as_foot', False),
            kwargs.get('row_striping', True)
            )

    def print_image(self, image_path):
        r"""Prints given image to the output.

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_image(r'C:\image.gif')
            ```
        """
        return self._runtime_output().print_image(image_path)

    @staticmethod
    def buttonify(uibutton, title=None):
        """Create an output-safe html button for a Revit ribbon button."""
        label = title \
            or getattr(uibutton, 'Text', None) \
            or getattr(uibutton, 'AutomationName', None) \
            or getattr(uibutton, 'Name', None) \
            or safe_strtype(uibutton)
        control_id = getattr(uibutton, 'Id', None) \
            or getattr(uibutton, 'Name', None) \
            or EXEC_PARAMS.command_controlid
        label = safe_strtype(label).replace('&', '&amp;') \
                                  .replace('<', '&lt;') \
                                  .replace('>', '&gt;')
        quoted_control_id = urlquote(safe_strtype(control_id))

        return coreutils.prepare_html_str(
            '<a href="revit://outputhelpers?command=button&controlid={}" '
            'style="display:inline-block;text-decoration:none;font:inherit;'
            'padding:4px 10px;border:1px solid #8a8f94;'
            'background:#f5f6f7;color:#233749;">{}</a>'
            .format(quoted_control_id, label)
            )

    def print_button(self, uibutton, title=None):
        """Print a Revit ribbon button as an embedded output button."""
        self.print_html(coreutils.reverse_html(self.buttonify(uibutton, title)))

    def insert_divider(self, level=''):
        """Add horizontal rule to the output window."""
        return self._runtime_output().insert_divider(level)

    def next_page(self):
        """Add hidden next page tag to the output window.

        This is helpful to silently separate the output to multiple pages
        for better printing.
        """
        return self._runtime_output().next_page()

    @staticmethod
    def linkify(element_ids, title=None):
        """Create clickable link for the provided element ids.

        This method, creates the link but does not print it directly.

        Args:
            element_ids (ElementId | list[ElementId]): single or multiple ids
            title (str): tile of the link. defaults to list of element ids

        Returns:
            (str): clickable link

        Examples:
            ```python
            output = pyrevit.output.get_output()
            for idx, elid in enumerate(element_ids):
                print('{}: {}'.format(idx+1, output.linkify(elid)))
            ```
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
        """:obj:`PyRevitOutputChart`: Return doughnut chart object."""
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
    """:obj:`PyRevitOutputWindow`: Return a wrapper bound to current output.

    Retain the returned wrapper when it will be used by a deferred or modeless
    callback after the current command returns.
    """
    return PyRevitOutputWindow()
