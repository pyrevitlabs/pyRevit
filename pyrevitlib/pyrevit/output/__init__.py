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

Here is the source of :func:`pyrevit.script.get_output`. As you can see this
functions calls the :func:`pyrevit.output.get_output` to receive the
output wrapper.

.. literalinclude:: ../../pyrevitlib/pyrevit/script.py
    :pyobject: get_output
"""

from __future__ import print_function
import os.path as op
import sys
from pyrevit.compat import PY2, PY3
if PY2:
    from itertools import izip_longest as zip_longest
elif PY3:
    from itertools import zip_longest

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

mlogger = logger.get_logger(__name__)

DEFAULT_STYLESHEET_NAME = 'outputstyles.css'


def docclosing_eventhandler(sender, args):
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
        # do not store this setting forcefully
        # each repo should default to its own stylesheet
        # user_config.output_stylesheet = stylesheet


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
    """Wrapper to interact with the output window."""
	
    def __init__(self): 
        self._table_counter = 0
	
    @property
    def window(self):
        """``PyRevitLabs.PyRevit.Runtime.ScriptConsole``: Return output window object."""
        return EXEC_PARAMS.window_handle

    @property
    def renderer(self):
        """Return html renderer inside output window.

        Returns:
            (System.Windows.Forms.WebBrowser): HTML renderer
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
        """Whether the window has been closed by the user."""
        return self.window.ClosedByUser

    @property
    def last_line(self):
        """Last line of the output window."""
        return self.window.GetLastLine()

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

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.inject_to_head('script',
                                  '',   # no script since it's a link
                                  {'src': js_script_file_path})
            ```
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
        if self.window:
            self.window.WaitReadyBrowser()

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
        html_element = self.renderer.Document.CreateElement(element_tag)
        if element_contents:
            html_element.InnerHtml = element_contents

        if attribs:
            for attribute, value in attribs.items():
                html_element.SetAttribute(attribute, value)

        # inject the script into body
        body_el = self._get_body_element()
        body_el.AppendChild(html_element)
        if self.window:
            self.window.WaitReadyBrowser()

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
        if body:
            self.inject_to_body('script', script_code, attribs=attribs)
        else:
            self.inject_to_head('script', script_code, attribs=attribs)

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
        """Center the output window on the screen."""
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

        Examples:
            ```python
            output = pyrevit.output.get_output()
            for i in range(100):
                output.update_progress(i, 100)
            ```
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
        """Show or hide indeterminate progress bar."""
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

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_html('<strong>Title</strong>')
            ```
        """
        print(coreutils.prepare_html_str(html_str),
              end="")

    @staticmethod
    def print_code(code_str):
        """Print code to the output window with special formatting.

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_code('value = 12')
            ```
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

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_md('### Title')
            ```
        """
        tables_ext = 'pyrevit.coreutils.markdown.extensions.tables'
        markdown_html = markdown.markdown(md_str, extensions=[tables_ext])
        markdown_html = markdown_html.replace('\n', '').replace('\r', '')
        html_code = coreutils.prepare_html_str(markdown_html)
        print(html_code, end="")
        if PY3:
            sys.stdout.flush()


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
        if not columns:
            columns = []
        if not formats:
            formats = []

        if last_line_style:
            self.add_style('tr:last-child {{ {style} }}'
                           .format(style=last_line_style))

        zipper = zip_longest #pylint: disable=E1101
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


    def table_html_header(self, columns, table_uid, border_style):
        """Helper method for print_html_table() method

        Return html <thead><tr><th> row for the table header
        
        Args:
            columns (list[str]): list of column names
            table_uid (str): a unique ID for this table's CSS classes
            border_style (str): CSS border style string for table cells
        
        Returns:
            str: HTML string containing the table header row
            
        Examples:
            ```python
            output = pyrevit.output.get_output()
            
            # Basic usage - called internally by print_html_table()
            columns = ["Name", "Age", "City"]
            table_uid = 1
            border_style = "border: 1px solid black;"
            header_html = output.table_html_header(
                columns, table_uid, border_style)
            # Returns: "<thead><tr style='border: 1px solid black;'>" \
            #          "<th class='head_title-1-0' align='left'>Name</th>" \
            #          "<th class='head_title-1-1' align='left'>Age</th>" \
            #          "<th class='head_title-1-2' align='left'>City</th>" \
            #          "</tr></thead>"
            
            # Without border style
            header_html = output.table_html_header(
                columns, table_uid, "")
            # Returns: "<thead><tr>" \
            #          "<th class='head_title-1-0' align='left'>Name</th>" \
            #          "<th class='head_title-1-1' align='left'>Age</th>" \
            #          "<th class='head_title-1-2' align='left'>City</th>" \
            #          "</tr></thead>"
            ```
        """
        html_head = "<thead><tr {}>".format(border_style)
        for i, c in enumerate(columns):
            html_head += \
                "<th class='head_title-{}-{}' align='left'>{}</th>".format(
                    table_uid, i, c)
            # pyRevit original print_table uses align='left'.
            # This is now overridden by CSS if specified
        html_head += "</tr></thead>"

        return html_head


    def table_check_input_lists(self, 
                                table_data,
                                columns,
                                formats,
                                input_kwargs):
        """Helper method for print_html_table() method
        
        Check that the table_data is present and is a list
        Check that table_data rows are of the same length
        Check that all print_html_table() kwargs of type list are of correct length

        Args:
            table_data (list[list[Any]]): The whole table data as 2D list
            columns (list[str]): list of column names
            formats (list[str]): list of format strings for each column
            input_kwargs (list[list[Any]]): list of additional argument lists
        
        Returns:
            tuple: (bool, str) - (True/False, message) indicating result
            
        Examples:
            ```python
            output = pyrevit.output.get_output()
            
            # Valid table data
            table_data = [["John", 25, "NYC"], ["Jane", 30, "LA"]]
            columns = ["Name", "Age", "City"]
            formats = ["", "{} years", ""]
            input_kwargs = [["left", "center", "right"], 
                           ["100px", "80px", "120px"]]
            
            is_valid, message = output.table_check_input_lists(
                table_data, columns, formats, input_kwargs)
            # Returns: (True, "Inputs OK")
            
            # Invalid - mismatched column count
            table_data = [["John", 25], ["Jane", 30, "LA"]]  # Inconsistent
            is_valid, message = output.table_check_input_lists(
                table_data, columns, formats, input_kwargs)
            # Returns: (False, "Not all rows of table_data are of "
            #           "equal length")
            
            # Invalid - wrong number of columns
            columns = ["Name", "Age"]  # Only 2 columns but data has 3
            is_valid, message = output.table_check_input_lists(
                table_data, columns, formats, input_kwargs)
            # Returns: (False, "Column head list length not equal "
            #           "to data row")
            
            # Invalid - empty table data
            is_valid, message = output.table_check_input_lists(
                [], columns, formats, input_kwargs)
            # Returns: (False, "No table_data list")
            ```
        """
  
        # First check positional and named keyword args
        if not table_data:
            return False, "No table_data list"
        if not isinstance(table_data, list):
            return False, "table_data is not a list"
        # table_data is a list. The first sublist must also be a list
        first_data_row = list(table_data[0])
        if not isinstance(first_data_row, list):
            return False, "table_data's first row is not a list or tuple ({})".format(type(first_data_row))
        len_data_row = len(first_data_row)
        if not all(len(row) == len_data_row for row in table_data):
            return False, "Not all rows of table_data are of equal length"
            
        if columns and len_data_row != len(columns): # columns is allowed to be None
            return False, "Column head list length not equal to data row"
        
        if formats and len_data_row != len(formats): # formats is allowed to be None
            return False, "Formats list length not equal to data row"
        
        # Next check **kwargs
        # Loop through the lists and return if not a list or len not equal
        for kwarg_list in input_kwargs:
            if not kwarg_list: # No kwarg is OK beacause they are optional
                continue
            if not isinstance(kwarg_list, list):
                return False, "One of the print_html_table kwargs that should be a list is not a list ({})".format(kwarg_list)
            if len(kwarg_list) != len_data_row:
                return False, "print_html_table kwarg list length problem (should match {} columns)".format(len_data_row)

        return True, "Inputs OK"


    def print_html_table(self,
                    table_data,
                    columns=None,
                    formats=None,
                    title='',
                    last_line_style='',
                    **kwargs):
        """Print provided data in a HTML table in output window.
           The same window can output several tables, each with their own formatting options.

        Args:
            table_data (list[iterable[Any]]): 2D array of data
            title (str): table title
            columns (list[str]): list of column names
            formats (list[str]): column data formats using python string formatting
            last_line_style (str): css style of last row of data (NB applies to all tables in this output)
            column_head_align_styles (list[str]): list css align-text styles for header row
            column_data_align_styles (list[str]): list css align-text styles for data rows
            column_widths (list[str]): list of CSS widths in either px or % 
            column_vertical_border_style (str): CSS compact border definition
            table_width_style (str): CSS to use for width for the whole table, in either px or % 
            repeat_head_as_foot (bool): Repeat the header row at the table foot (useful for long tables)
            row_striping (bool): False to override the default white-grey row stripes and make all white)


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
            col_head_align_styles = ["left", "left", "center", "right"],
            col_data_align_styles = ["left", "left", "center", "right"],
            column_widths = ["100px", "100px", "500px", "100px"],
            column_vertical_border_style = "border:black solid 1px",
            table_width_style='width:100%', 
            repeat_head_as_foot=True,
            row_striping=False

            )
            Returns:
                Directly prints:
                    print_md of the title (str): 
                    print_html of the generated HTML table with formatting.
            ```
        """

        # Get user formatting options from kwargs
        column_head_align_styles     = kwargs.get("column_head_align_styles", None)
        column_data_align_styles     = kwargs.get("column_data_align_styles", None)
        column_widths                = kwargs.get("column_widths", None)
        column_vertical_border_style = kwargs.get("column_vertical_border_style", None)
        table_width_style            = kwargs.get("table_width_style", None)
        repeat_head_as_foot          = kwargs.get("repeat_head_as_foot", False)
        row_striping                 = kwargs.get("row_striping", True)


        # Get a unique ID for each table from _table_counter
        # This is used in HTML tags to define CSS classes for formatting per table
        self._table_counter += 1
        table_uid = self._table_counter

        # Validate input arguments should be lists:
        input_kwargs = [column_head_align_styles, column_data_align_styles, column_widths]
        inputs_ok, inputs_msg = self.table_check_input_lists(table_data,
                                             columns,
                                             formats,
                                             input_kwargs)

        if not inputs_ok:
            self.print_md('### :warning: {} '.format(inputs_msg))
            return

        
        if not row_striping:
            # Override default original pyRevit white-grey row striping. Makes all rows white.
            self.add_style('tr.data-row-{} {{ {style} }}'.format(table_uid, style="background-color: #ffffff"))

        if last_line_style:
            # Adds a CCS class to allow a last-row format per table (if several in the same output)
            self.add_style('tr.data-row-{}:last-child {{ {style} }}'.format(table_uid, style=last_line_style))

        if column_head_align_styles:
            for i, s in enumerate(column_head_align_styles):
                self.add_style('.head_title-{}-{} {{ text-align:{style} }}'.format(table_uid, i, style=s))

        if column_data_align_styles:
            for i, s in enumerate(column_data_align_styles):
                self.add_style('.data_cell-{}-{} {{ text-align:{style} }}'.format(table_uid, i, style=s))

        if table_width_style:
            self.add_style('.tab-{} {{ width:{} }}'.format(table_uid, table_width_style))

	
        # Open HTML table and its CSS class
        html = "<table class='tab-{}'>".format(table_uid)

        # Build colgroup if user argument specifies column widths
        if column_widths:
              COL = "<col style='width: {}'>"
              html += '<colgroup>'
              for w in column_widths:
                  html += COL.format(w)
              html += "</colgroup>"
        
        if column_vertical_border_style:
            border_style = "style='{}'".format(column_vertical_border_style)
        else:
            border_style = ""

        # Build header row (column titles) if requested
        if columns:
            html_head = self.table_html_header(columns, table_uid, border_style)
            html += html_head
        else:
            html_head =""
            repeat_head_as_foot = False

        
        # Build body rows from 2D python list table_data
        html += "<tbody>"
        for row in table_data:
            # Build an HTML data row with CSS class for this table
            html += "<tr class='data-row-{}'>".format(table_uid)
            for i, cell_data in enumerate(row):
                
                # Slight workaround to be backwards compatible with pyRevit original print_table
                # pyRevit documentation gives the example: formats=['', '', '', '{}%'],
                # Sometimes giving an empty string, sometimes a placeholder with string formatting
                if formats: # If format options provided
                    format_placeholder = formats[i] if formats[i] else "{}"
                    
                    cell_data = format_placeholder.format(cell_data) # Insert data with or without formatting

                html += "<td class='data_cell-{}-{}' {}>{}</td>".format(table_uid, i, border_style, cell_data)
            html += "</tr>"
        
        # Re-insert header row at the end, if requested and if column titles provided
        if repeat_head_as_foot:
            html += html_head


        html += "</tbody>"
        html += "</table>" # Close table

        if title:
            self.print_md('### {title}'.format(title=title))
        self.print_html(html)
    

    def print_image(self, image_path):
        r"""Prints given image to the output.

        Examples:
            ```python
            output = pyrevit.output.get_output()
            output.print_image(r'C:\image.gif')
            ```
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
