"""Shared modal input dialogs and their public convenience functions."""

import datetime
import os.path as op

from pyrevit import framework
from pyrevit.framework import System
from .base import (
    WPFWindow,
    XAML_FILES_DIR,
    DEFAULT_INPUTWINDOW_WIDTH,
    DEFAULT_INPUTWINDOW_HEIGHT,
)
from . import _backend


class TemplateUserInputWindow(WPFWindow):
    """Base class for pyRevit user input standard forms.

    Args:
        context (any): window context element(s)
        title (str): window title
        width (int): window width
        height (int): window height
        **kwargs (Any): other arguments to be passed to :func:`_setup`
    """

    xaml_source = "BaseWindow.xaml"
    default_title_key = "pyRevit.DefaultWindowTitle"

    def __init__(self, context, title, width, height, **kwargs):
        """Initialize user input window."""
        _backend.validate_input(kwargs.get("value_type", "string"))
        try:
            WPFWindow.__init__(
                self, op.join(XAML_FILES_DIR, self.xaml_source), handle_esc=True
            )
            if title:
                self.Title = title
            else:
                localized_title = self.get_locale_string(
                    self.default_title_key, "User Input"
                )
                self.Title = (
                    localized_title
                    if isinstance(localized_title, str)
                    else "User Input"
                )
            self.Width = width
            self.Height = height

            self._context = context
            self.response = None

            # parent window?
            owner = kwargs.get("owner", None)
            if owner:
                # set wpf windows directly
                self.Owner = _backend.unwrap(owner)
                self.WindowStartupLocation = (
                    framework.Windows.WindowStartupLocation.CenterOwner
                )

            self._setup(**kwargs)
        except Exception:
            _backend.dispose(self)
            raise

    def _setup(self, **kwargs):
        """Private method to be overriden by subclasses for window setup."""
        pass

    @classmethod
    def show(
        cls,
        context,  # pylint: disable=W0221
        title=None,
        width=DEFAULT_INPUTWINDOW_WIDTH,
        height=DEFAULT_INPUTWINDOW_HEIGHT,
        **kwargs
    ):  # fmt: skip
        """Show user input window.

        Args:
            context (any): window context element(s)
            title (str): window title
            width (int): window width
            height (int): window height
            **kwargs (any): other arguments to be passed to window
        """
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class GetValueWindow(TemplateUserInputWindow):
    """Collect a modal value; cancellation returns None.

    Note:
        CPython supports the string, dropdown, date and slider inputs; other
        value types are rejected before any native control is created.
    """

    xaml_source = "GetValueWindow.xaml"
    resolve_theme = True

    def _setup(self, **kwargs):
        self.Width = 400
        # determine value type
        self.value_type = kwargs.get("value_type", "string")
        value_prompt = kwargs.get("prompt", None)
        value_default = kwargs.get("default", None)
        self.reserved_values = kwargs.get("reserved_values", [])

        # customize window based on type
        if self.value_type == "string":
            self.show_element(self.stringPanel_dp)
            self.stringValue_tb.Text = value_default if value_default else ""
            self.stringValue_tb.Focus()
            self.stringValue_tb.SelectAll()
            self.stringPrompt.Text = value_prompt if value_prompt else "Enter string:"
            if self.reserved_values:
                self.string_value_changed(None, None)
        elif self.value_type == "dropdown":
            self.show_element(self.dropdownPanel_db)
            self.dropdownPrompt.Text = (
                value_prompt if value_prompt else "Pick one value:"
            )
            self.dropdown_cb.ItemsSource = _backend.items_source(self._context)
            if value_default:
                self.dropdown_cb.SelectedItem = value_default
        elif self.value_type == "date":
            self.show_element(self.datePanel_dp)
            self.datePrompt.Text = value_prompt if value_prompt else "Pick date:"
            if isinstance(value_default, datetime.datetime):
                self.datePicker.SelectedDate = System.DateTime(
                    value_default.year, value_default.month, value_default.day
                )
        elif self.value_type == "slider":
            self.show_element(self.sliderPanel_sp)
            self.sliderPrompt.Text = value_prompt
            self.numberPicker.Minimum = kwargs.get("min", 0)
            self.numberPicker.Maximum = kwargs.get("max", 100)
            self.numberPicker.TickFrequency = kwargs.get("interval", 1)
            self.numberPicker.Value = (
                value_default
                if isinstance(value_default, (float, int))
                else self.numberPicker.Minimum
            )

    def string_value_changed(self, sender, args):  # pylint: disable=unused-argument
        """Handle string vlaue update event."""
        filtered_rvalues = sorted(
            [x for x in self.reserved_values if self.stringValue_tb.Text == str(x)]
        )
        similar_rvalues = sorted(
            [x for x in self.reserved_values if self.stringValue_tb.Text in str(x)],
            reverse=True,
        )
        filtered_rvalues.extend(similar_rvalues)
        if filtered_rvalues:
            self.reservedValuesList.ItemsSource = _backend.items_source(
                filtered_rvalues
            )
            self.show_element(self.reservedValuesListPanel)
            self.okayButton.IsEnabled = self.stringValue_tb.Text not in filtered_rvalues
        else:
            self.reservedValuesList.ItemsSource = _backend.items_source([])
            self.hide_element(self.reservedValuesListPanel)
            self.okayButton.IsEnabled = True

    def select(self, sender, args):  # pylint: disable=W0613
        """Process input data and set the response."""
        if self.value_type == "string":
            self.response = self.stringValue_tb.Text
        elif self.value_type == "dropdown":
            self.response = self.dropdown_cb.SelectedItem
        elif self.value_type == "date":
            if self.datePicker.SelectedDate:
                selected = self.datePicker.SelectedDate
                self.response = datetime.datetime(
                    selected.Year, selected.Month, selected.Day
                )
            else:
                self.response = None
        elif self.value_type == "slider":
            self.response = self.numberPicker.Value
        self.Close()


def ask_for_string(default=None, prompt=None, title=None, **kwargs):
    """Ask user to select a string value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    string data types. kwargs can be used to pass on other arguments.

    Args:
        default (str): default unique string. must not be in reserved_values
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        (str): selected string value

    Examples:
        ```python
        forms.ask_for_string(
            default='some-tag',
            prompt='Enter new tag name:',
            title='Tag Manager')
        'new-tag'
        ```
    """
    return GetValueWindow.show(
        None, value_type="string", default=default, prompt=prompt, title=title, **kwargs
    )


def ask_for_unique_string(
    reserved_values, default=None, prompt=None, title=None, **kwargs
):
    """Ask user to select a unique string value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    unique string data types. kwargs can be used to pass on other arguments.

    Args:
        reserved_values (list[str]): list of reserved (forbidden) values
        default (str): default unique string. must not be in reserved_values
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        (str): selected unique string

    Examples:
        ```python
        forms.ask_for_unique_string(
            prompt='Enter a Unique Name',
            title=self.Title,
            reserved_values=['Ehsan', 'Gui', 'Guido'],
            owner=self)
        'unique string'
        ```

        In example above, owner argument is provided to be passed to underlying
        :obj:`GetValueWindow`.

    """
    return GetValueWindow.show(
        None,
        value_type="string",
        default=default,
        prompt=prompt,
        title=title,
        reserved_values=reserved_values,
        **kwargs
    )  # fmt: skip


def ask_for_date(default=None, prompt=None, title=None, **kwargs):
    """Ask user to select a date value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    date data types. kwargs can be used to pass on other arguments.

    Args:
        default (datetime.datetime): default selected date value
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        (datetime.datetime): selected date

    Examples:
        ```python
        forms.ask_for_date(default="", title="Enter deadline:")
        datetime.datetime(2019, 5, 17, 0, 0)
        ```
    """
    return GetValueWindow.show(
        None, value_type="date", default=default, prompt=prompt, title=title, **kwargs
    )


def ask_for_number_slider(
    default=None, min=0, max=100, interval=1, prompt=None, title=None, **kwargs
):
    """Ask user to select a number value.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    numbers. kwargs can be used to pass on other arguments.

    Args:
        default (str): default unique string. must not be in reserved_values
        min (int): minimum value on slider
        max (int): maximum value on slider
        interval (int): number interval between values
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        (str): selected string value

    Examples:
        ```python
        forms.ask_for_number_slider(
            default=50,
            min = 0,
            max = 100,
            interval = 5,
            prompt='Select a number:',
            title='test title')
        '50'
        ```

    In this example, the slider will allow values such as '40, 45, 50, 55, 60' etc
    """
    return GetValueWindow.show(
        None,
        value_type="slider",
        default=default,
        prompt=prompt,
        title=title,
        max=max,
        min=min,
        interval=interval,
        **kwargs
    )  # fmt: skip


def ask_for_one_item(items, default=None, prompt=None, title=None, **kwargs):
    """Ask user to select an item from a list of items.

    This is a shortcut function that configures :obj:`GetValueWindow` for
    'single-select' data types. kwargs can be used to pass on other arguments.

    Args:
        items (list[str]): list of items to choose from
        default (str): default selected item
        prompt (str): prompt message
        title (str): title message
        kwargs (type): other arguments to be passed to :obj:`GetValueWindow`

    Returns:
        (str): selected item

    Examples:
        ```python
        forms.ask_for_one_item(
            ['test item 1', 'test item 2', 'test item 3'],
            default='test item 2',
            prompt='test prompt',
            title='test title'
        )
        'test item 1'
        ```
    """
    return GetValueWindow.show(
        items,
        value_type="dropdown",
        default=default,
        prompt=prompt,
        title=title,
        **kwargs
    )  # fmt: skip
