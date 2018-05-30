"""Reusable WPF forms for pyRevit."""

import sys
import os
import os.path as op
import string
from collections import OrderedDict
import threading
from functools import wraps

from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import framework
from pyrevit.framework import System
from pyrevit.framework import Threading
from pyrevit.framework import Interop
from pyrevit.framework import Input
from pyrevit.framework import wpf, Forms, Controls, Media
from pyrevit.api import AdWindows
from pyrevit import revit, UI, DB
from pyrevit.forms import utils


logger = get_logger(__name__)


DEFAULT_CMDSWITCHWND_WIDTH = 600
DEFAULT_SEARCHWND_WIDTH = 600
DEFAULT_SEARCHWND_HEIGHT = 100
DEFAULT_INPUTWINDOW_WIDTH = 500
DEFAULT_INPUTWINDOW_HEIGHT = 400


class WPFWindow(framework.Windows.Window):
    r"""WPF Window base class for all pyRevit forms.

    Args:
        xaml_source (str): xaml source filepath or xaml content
        literal_string (bool): xaml_source contains xaml content, not filepath
        handle_esc (bool): handle Escape button and close the window

    Example:
        >>> from pyrevit import forms
        >>> layout = '<Window ShowInTaskbar="False" ResizeMode="NoResize" ' \
        >>>          'WindowStartupLocation="CenterScreen" ' \
        >>>          'HorizontalContentAlignment="Center">' \
        >>>          '</Window>'
        >>> w = forms.WPFWindow(layout, literal_string=True)
        >>> w.show()
    """

    def __init__(self, xaml_source, literal_string=False, handle_esc=True):
        """Initialize WPF window and resources."""
        # self.Parent = self
        wih = Interop.WindowInteropHelper(self)
        wih.Owner = AdWindows.ComponentManager.ApplicationWindow

        if not literal_string:
            if not op.exists(xaml_source):
                wpf.LoadComponent(self,
                                  os.path.join(EXEC_PARAMS.command_path,
                                               xaml_source)
                                  )
            else:
                wpf.LoadComponent(self, xaml_source)
        else:
            wpf.LoadComponent(self, framework.StringReader(xaml_source))

        if handle_esc:
            self.PreviewKeyDown += self.handle_input_key

        #2c3e50 #noqa
        self.Resources['pyRevitDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50)

        #23303d #noqa
        self.Resources['pyRevitDarkerDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x23, 0x30, 0x3d)

        #ffffff #noqa
        self.Resources['pyRevitButtonColor'] = \
            Media.Color.FromArgb(0xFF, 0xff, 0xff, 0xff)

        #f39c12 #noqa
        self.Resources['pyRevitAccentColor'] = \
            Media.Color.FromArgb(0xFF, 0xf3, 0x9c, 0x12)

        self.Resources['pyRevitDarkBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitDarkColor'])
        self.Resources['pyRevitAccentBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitAccentColor'])

        self.Resources['pyRevitDarkerDarkBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitDarkerDarkColor'])

        self.Resources['pyRevitButtonForgroundBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitButtonColor'])

    def handle_input_key(self, sender, args):
        """Handle keyboard input and close the window on Escape."""
        if args.Key == Input.Key.Escape:
            self.Close()

    def show(self, modal=False):
        """Show window."""
        if modal:
            return self.ShowDialog()
        self.Show()

    def show_dialog(self):
        """Show modal window."""
        return self.ShowDialog()

    def set_image_source(self, element_name, image_file):
        """Set source file for image element.

        Args:
            element_name (str): xaml image element name
            image_file (str): image file path
        """
        wpfel = getattr(self, element_name)
        if not op.exists(image_file):
            # noinspection PyUnresolvedReferences
            wpfel.Source = \
                utils.bitmap_from_file(
                    os.path.join(EXEC_PARAMS.command_path,
                                 image_file)
                    )
            # wpfel.Source = \
            #     framework.Imaging.BitmapImage(
            #         framework.Uri(os.path.join(EXEC_PARAMS.command_path,
            #                                    image_file))
            #         )
        else:
            wpfel.Source = \
                framework.Imaging.BitmapImage(framework.Uri(image_file))

    @staticmethod
    def hide_element(*wpf_elements):
        """Collapse elements.

        Args:
            *wpf_elements (str): element names to be collaped
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = framework.Windows.Visibility.Collapsed

    @staticmethod
    def show_element(*wpf_elements):
        """Show collapsed elements.

        Args:
            *wpf_elements (str): element names to be set to visible.
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = framework.Windows.Visibility.Visible

    @staticmethod
    def toggle_element(*wpf_elements):
        """Toggle visibility of elements.

        Args:
            *wpf_elements (str): element names to be toggled.
        """
        for wpfel in wpf_elements:
            if wpfel.Visibility == framework.Windows.Visibility.Visible:
                self.hide_element(wpfel)
            elif wpfel.Visibility == framework.Windows.Visibility.Collapsed:
                self.show_element(wpfel)


class TemplateUserInputWindow(WPFWindow):
    """Base class for pyRevit user input standard forms.

    Args:
        context (any): window context element(s)
        title (str): window title
        width (int): window width
        height (int): window height
        **kwargs: other arguments to be passed to :func:`_setup`
    """

    xaml_source = 'BaseWindow.xaml'

    def __init__(self, context, title, width, height, **kwargs):
        """Initialize user input window."""
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), self.xaml_source),
                           handle_esc=True)
        self.Title = title
        self.Width = width
        self.Height = height

        self._context = context
        self.response = None

        self._setup(**kwargs)

    def _setup(self, **kwargs):
        """Private method to be overriden by subclasses for window setup."""
        pass

    @classmethod
    def show(cls, context,
             title='User Input',
             width=DEFAULT_INPUTWINDOW_WIDTH,
             height=DEFAULT_INPUTWINDOW_HEIGHT, **kwargs):
        """Show user input window.

        Args:
            context (any): window context element(s)
            title (type): window title
            width (type): window width
            height (type): window height
            **kwargs (type): other arguments to be passed to window
        """
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class TemplateListItem(object):
    """Base class for checkbox option wrapping another object."""

    def __init__(self, orig_item, checkable=True, name_attr=None):
        """Initialize the checkbox option and wrap given obj.

        Args:
            orig_item (any): object to wrap (must have name property
                             or be convertable to string with str()
        """
        self.item = orig_item
        self.state = False
        self._nameattr = name_attr
        self._checkable = checkable

    def __nonzero__(self):
        return self.state

    def __str__(self):
        return self.name or str(self.item)

    def __contains__(self, value):
        return value in self.name

    @property
    def name(self):
        """Name property."""
        # get custom attr, or name or just str repr
        if self._nameattr:
            return str(getattr(self.item, self._nameattr))
        elif hasattr(self.item, 'name'):
            return getattr(self.item, 'name', '')
        else:
            return safe_strtype(self.item)

    def unwrap(self):
        """Unwrap and return wrapped object."""
        return self.item

    def matches(self, filter_str):
        """Check if instance matches the filter string."""
        return filter_str in self.name.lower()

    @property
    def checkable(self):
        """List Item CheckBox Visibility."""
        return framework.Windows.Visibility.Visible if self._checkable \
            else framework.Windows.Visibility.Collapsed

    @checkable.setter
    def checkable(self, value):
        self._checkable = value

    @classmethod
    def is_checkbox(cls, item):
        """Check if the object has all necessary attribs for a checkbox."""
        return isinstance(item, TemplateListItem)


class SelectFromList(TemplateUserInputWindow):
    """Standard form to select from a list of items.

    Check box items passed in context to this standard form, must implement
    ``name`` and ``state`` parameter and ``__nonzero__`` method for truth
    value testing.

    Args:
        context (list[str]): list of items to be selected from
        title (str, optional): window title. see super class for defaults.
        width (int, optional): window width. see super class for defaults.
        height (int, optional): window height. see super class for defaults.
        button_name (str, optional):
            name of select button. defaults to 'Select'
        name_attr (str, optional):
            attribute that should be read as item name. defaults to None
        multiselect (bool, optional):
            allow multi-selection (uses check boxes). defaults to False
        return_all (bool, optional):
            return all items. This is handly when some input items have states
            and the script needs to check the state changes on all items.
            This options works in multiselect mode only. defaults to False
        filterfunc (function):
            filter function to be applied to context items. defaults to None
        group_selector_title (str):
            title for list group selector. defaults to 'List Group'
        default_group (str): name of defautl group to be selected


    Example:
        >>> from pyrevit import forms
        >>> items = ['item1', 'item2', 'item3']
        >>> forms.SelectFromList.show(items, button_name='Select Item')
        >>> ['item1']

        >>> from pyrevit import forms
        >>> class MyOption(object):
        ...     def __init__(self, name, state=False):
        ...         self.state = state
        ...         self.name = name
        ...
        ...     def __nonzero__(self):
        ...         return self.state
        ...
        ...     def __str__(self):
        ...         return self.name
        >>> ops = [MyOption('op1'), MyOption('op2', True), MyOption('op3')]
        >>> res = forms.SelectFromList.show(ops,
        ...                                 multiselect=True,
        ...                                 button_name='Select Item')
        >>> [bool(x) for x in res]  # or [x.state for x in res]
        [True, False, True]

        This module also provides a wrapper base class :obj:`BaseCheckBoxItem`
        for when the checkbox option is wrapping another element,
        e.g. a Revit ViewSheet. Derive from this base class and define the
        name property to customize how the checkbox is named on the dialog.

        >>> from pyrevit import forms
        >>> class MyOption(forms.BaseCheckBoxItem)
        ...    @property
        ...    def name(self):
        ...        return '{} - {}{}'.format(self.item.SheetNumber,
        ...                                  self.item.SheetNumber)
        >>> ops = [MyOption('op1'), MyOption('op2', True), MyOption('op3')]
        >>> res = forms.SelectFromList.show(ops,
        ...                                 multiselect=True,
        ...                                 button_name='Select Item')
        >>> [bool(x) for x in res]  # or [x.state for x in res]
        [True, False, True]

    """

    xaml_source = 'SelectFromList.xaml'

    def _setup(self, **kwargs):
        # custom button name?
        button_name = kwargs.get('button_name', 'Select')
        if button_name:
            self.select_b.Content = button_name

        # attribute to use as name?
        self._nameattr = kwargs.get('name_attr', None)

        # multiselect?
        if kwargs.get('multiselect', False):
            self.multiselect = True
            self.list_lb.SelectionMode = Controls.SelectionMode.Extended
            self.show_element(self.checkboxbuttons_g)
        else:
            self.multiselect = False
            self.list_lb.SelectionMode = Controls.SelectionMode.Single
            self.hide_element(self.checkboxbuttons_g)

        # return checked items only?
        self.return_all = kwargs.get('return_all', False)

        # filter function?
        self.filter_func = kwargs.get('filterfunc', None)

        # context group title?
        self.ctx_groups_title = \
            kwargs.get('group_selector_title', 'List Group')
        self.ctx_groups_title_tb.Text = self.ctx_groups_title

        self.ctx_groups_active = kwargs.get('default_group', None)

        # nicely wrap and prepare context for presentation, then present
        self._prepare_context()
        self._list_options()

        # setup search and filter fields
        self.hide_element(self.clrsearch_b)
        self.clear_search(None, None)

    def _prepare_context_items(self, ctx_items):
        new_ctx = []
        # filter context if necessary
        if self.filter_func:
            ctx_items = filter(self.filter_func, ctx_items)

        for item in ctx_items:
            if TemplateListItem.is_checkbox(item):
                item.checkable = self.multiselect
                new_ctx.append(item)
            else:
                new_ctx.append(
                    TemplateListItem(item,
                                     checkable=self.multiselect,
                                     name_attr=self._nameattr)
                    )

        return new_ctx

    def _prepare_context(self):
        if isinstance(self._context, dict) and self._context.keys():
            self._update_ctx_groups(self._context.keys())
            new_ctx = dict()
            for ctx_grp, ctx_items in self._context.items():
                new_ctx[ctx_grp] = self._prepare_context_items(ctx_items)
        else:
            new_ctx = self._prepare_context_items(self._context)

        self._context = new_ctx

    def _update_ctx_groups(self, ctx_group_names):
        self.show_element(self.ctx_groups_dock)
        self.ctx_groups_selector_cb.ItemsSource = ctx_group_names
        if self.ctx_groups_active in ctx_group_names:
            self.ctx_groups_selector_cb.SelectedIndex = \
                ctx_group_names.index(self.ctx_groups_active)
        else:
            self.ctx_groups_selector_cb.SelectedIndex = 0

    def _get_active_ctx_group(self):
        return self.ctx_groups_selector_cb.SelectedItem

    def _get_active_ctx(self):
        if isinstance(self._context, dict):
            return self._context[self._get_active_ctx_group()]
        else:
            return self._context

    def _list_options(self, option_filter=None):
        if option_filter:
            self.checkall_b.Content = 'Check'
            self.uncheckall_b.Content = 'Uncheck'
            self.toggleall_b.Content = 'Toggle'
            option_filter = option_filter.lower()
            self.list_lb.ItemsSource = \
                [x for x in self._get_active_ctx() if x.matches(option_filter)]
        else:
            self.checkall_b.Content = 'Check All'
            self.uncheckall_b.Content = 'Uncheck All'
            self.toggleall_b.Content = 'Toggle All'
            self.list_lb.ItemsSource = [x for x in self._get_active_ctx()]

    @staticmethod
    def _unwrap_options(options):
        unwrapped = []
        for op in options:
            if type(op) is TemplateListItem:
                unwrapped.append(op.unwrap())
            else:
                unwrapped.append(op)
        return unwrapped

    def _get_options(self):
        if self.multiselect:
            if self.return_all:
                return self._unwrap_options(
                    [x for x in self._get_active_ctx()]
                    )
            else:
                return self._unwrap_options(
                    [x for x in self._get_active_ctx()
                     if x.state or x in self.list_lb.SelectedItems]
                    )
        else:
            return self._unwrap_options([self.list_lb.SelectedItem])[0]

    def _set_states(self, state=True, flip=False, selected=False):
        all_items = self.list_lb.ItemsSource
        if selected:
            current_list = self.list_lb.SelectedItems
        else:
            current_list = self.list_lb.ItemsSource
        for checkbox in current_list:
            if flip:
                checkbox.state = not checkbox.state
            else:
                checkbox.state = state

        # push list view to redraw
        self.list_lb.ItemsSource = None
        self.list_lb.ItemsSource = all_items

    def toggle_all(self, sender, args):
        """Handle toggle all button to toggle state of all check boxes."""
        self._set_states(flip=True)

    def check_all(self, sender, args):
        """Handle check all button to mark all check boxes as checked."""
        self._set_states(state=True)

    def uncheck_all(self, sender, args):
        """Handle uncheck all button to mark all check boxes as un-checked."""
        self._set_states(state=False)

    def check_selected(self, sender, args):
        """Mark selected checkboxes as checked."""
        self._set_states(state=True, selected=True)

    def uncheck_selected(self, sender, args):
        """Mark selected checkboxes as unchecked."""
        self._set_states(state=False, selected=True)

    def button_select(self, sender, args):
        """Handle select button click."""
        self.response = self._get_options()
        self.Close()

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        """Clear search box."""
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.search_tb.Focus()


class CommandSwitchWindow(TemplateUserInputWindow):
    """Standard form to select from a list of command options.

    Args:
        context (list[str]): list of command options to choose from
        switches (list[str]): list of on/off switches
        message (str): window title message
        config (dict): dictionary of config dicts for options or switches

    Returns:
        str: name of selected option

    Returns:
        tuple(str, dict): if ``switches`` option is used, returns a tuple
        of selection option name and dict of switches

    Example:
        This is an example with series of command options:

        >>> from pyrevit import forms
        >>> ops = ['option1', 'option2', 'option3', 'option4']
        >>> forms.CommandSwitchWindow.show(ops, message='Select Option')
        'option2'

        A more advanced example of combining command options, on/off switches,
        and option or switch configuration options:

        >>> from pyrevit import forms
        >>> ops = ['option1', 'option2', 'option3', 'option4']
        >>> switches = ['switch1', 'switch2']
        >>> cfgs = {'option1': { 'background': '0xFF55FF'}}
        >>> rops, rswitches = forms.CommandSwitchWindow.show(
        ...     ops,
        ...     switches=switches
        ...     message='Select Option',
        ...     config=cfgs
        ...     )
        >>> rops
        'option2'
        >>> rswitches
        {'switch1': False, 'switch2': True}
    """

    xaml_source = 'CommandSwitchWindow.xaml'

    def _setup(self, **kwargs):
        self.selected_switch = ''
        self.Width = DEFAULT_CMDSWITCHWND_WIDTH
        self.Title = 'Command Options'

        message = kwargs.get('message', None)
        self._switches = kwargs.get('switches', [])

        configs = kwargs.get('config', None)

        self.message_label.Content = \
            message if message else 'Pick a command option:'

        # creates the switches first
        for switch in self._switches:
            my_togglebutton = framework.Controls.Primitives.ToggleButton()
            my_togglebutton.Content = switch
            if configs and option in configs:
                self._set_config(my_togglebutton, configs[switch])
            self.button_list.Children.Add(my_togglebutton)

        for option in self._context:
            my_button = framework.Controls.Button()
            my_button.Content = option
            my_button.Click += self.process_option
            if configs and option in configs:
                self._set_config(my_button, configs[option])
            self.button_list.Children.Add(my_button)

        self._setup_response()
        self.search_tb.Focus()
        self._filter_options()

    @staticmethod
    def _set_config(item, config_dict):
        bg = config_dict.get('background', None)
        if bg:
            bg = bg.replace('0x', '#')
            item.Background = Media.BrushConverter().ConvertFrom(bg)

    def _setup_response(self, response=None):
        if self._switches:
            switches = [x for x in self.button_list.Children
                        if hasattr(x, 'IsChecked')]
            self.response = response, {x.Content: x.IsChecked
                                       for x in switches}
        else:
            self.response = response

    def _filter_options(self, option_filter=None):
        if option_filter:
            self.search_tb.Tag = ''
            option_filter = option_filter.lower()
            for button in self.button_list.Children:
                if option_filter not in button.Content.lower():
                    button.Visibility = framework.Windows.Visibility.Collapsed
                else:
                    button.Visibility = framework.Windows.Visibility.Visible
        else:
            self.search_tb.Tag = \
                'Type to Filter / Tab to Select / Enter or Click to Run'
            for button in self.button_list.Children:
                button.Visibility = framework.Windows.Visibility.Visible

    def _get_active_button(self):
        buttons = []
        for button in self.button_list.Children:
            if button.Visibility == framework.Windows.Visibility.Visible:
                buttons.append(button)
        if len(buttons) == 1:
            return buttons[0]
        else:
            for x in buttons:
                if x.IsFocused:
                    return x

    def handle_click(self, sender, args):
        """Handle mouse click."""
        self.Close()

    def handle_input_key(self, sender, args):
        """Handle keyboard inputs."""
        if args.Key == Input.Key.Escape:
            if self.search_tb.Text:
                self.search_tb.Text = ''
            else:
                self.Close()
        elif args.Key == Input.Key.Enter:
            self.process_option(self._get_active_button(), None)
        elif args.Key != Input.Key.Tab \
                and args.Key != Input.Key.Space\
                and args.Key != Input.Key.LeftShift\
                and args.Key != Input.Key.RightShift:
            self.search_tb.Focus()

    def search_txt_changed(self, sender, args):
        """Handle text change in search box."""
        self._filter_options(option_filter=self.search_tb.Text)

    def process_option(self, sender, args):
        """Handle click on command option button."""
        self.Close()
        if sender:
            self._setup_response(response=sender.Content)


class TemplatePromptBar(WPFWindow):
    """Template context-manager class for creating prompt bars.

    Prompt bars are show at the top of the active Revit window and are
    designed for better prompt visibility.

    Args:
        height (int): window height
        **kwargs: other arguments to be passed to :func:`_setup`
    """

    xaml_source = 'TemplatePromptBar.xaml'

    def __init__(self, height=32, **kwargs):
        """Initialize user prompt window."""
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), self.xaml_source))

        self.user_height = height
        self.update_window()

        self._setup(**kwargs)

    def update_window(self):
        """Update the prompt bar to match Revit window."""
        screen_area = HOST_APP.proc_screen_workarea
        scale_factor = 1.0 / HOST_APP.proc_screen_scalefactor
        top = left = width = height = 0

        window_rect = revit.get_window_rectangle()

        # set width and height
        width = window_rect.Right - window_rect.Left
        height = self.user_height

        top = window_rect.Top
        # in maximized window, the top might be off the active screen
        # due to windows thicker window frames
        # lets cut the height and re-adjust the top
        top_diff = abs(screen_area.Top - top)
        if 10 > top_diff > 0 and top_diff < height:
            height -= top_diff
            top = screen_area.Top

        left = window_rect.Left
        # in maximized window, Left also might be off the active screen
        # due to windows thicker window frames
        # let's fix the width to accomodate the extra pixels as well
        left_diff = abs(screen_area.Left - left)
        if 10 > left_diff > 0 and left_diff < width:
            # deduct two times the left negative offset since this extra
            # offset happens on both left and right side
            width -= left_diff * 2
            left = screen_area.Left

        self.Top = top * scale_factor
        self.Left = left * scale_factor
        self.Width = width * scale_factor
        self.Height = height

    def _setup(self, **kwargs):
        """Private method to be overriden by subclasses for prompt setup."""
        pass

    def __enter__(self):
        self.Show()
        return self

    def __exit__(self, exception, exception_value, traceback):
        self.Close()


class WarningBar(TemplatePromptBar):
    """Show warning bar at the top of Revit window.

    Args:
        title (string): warning bar text

    Example:
        >>> with WarningBar(title='my warning'):
        ...    # do stuff
    """

    xaml_source = 'WarningBar.xaml'

    def _setup(self, **kwargs):
        self.message_tb.Text = kwargs.get('title', '')


class ProgressBar(TemplatePromptBar):
    """Show progress bar at the top of Revit window.

    Args:
        title (string): progress bar text, defaults to 0/100 progress format
        indeterminate (bool): create indeterminate progress bar
        cancellable (bool): add cancel button to progress bar
        step (int): update progress intervals

    Example:
        >>> from pyrevit import forms
        >>> count = 1
        >>> with forms.ProgressBar(title='my command progress message') as pb:
        ...    # do stuff
        ...    pb.update_progress(count, 100)
        ...    count += 1

        Progress bar title could also be customized to show the current and
        total progress values. In example below, the progress bar message
        will be in format "0 of 100"

        >>> with forms.ProgressBar(title='{value} of {max_value}') as pb:

        By default progress bar updates the progress every time the
        .update_progress method is called. For operations with a large number
        of max steps, the gui update process time will have a significate
        effect on the overall execution time of the command. In these cases,
        set the value of step argument to something larger than 1. In example
        below, the progress bar updates once per every 10 units of progress.

        >>> with forms.ProgressBar(title='message', steps=10):

        Progress bar could also be set to indeterminate for operations of
        unknown length. In this case, the progress bar will show an infinitely
        running ribbon:

        >>> with forms.ProgressBar(title='message', indeterminate=True):

        if cancellable is set on the object, a cancel button will show on the
        progress bar and .cancelled attribute will be set on the ProgressBar
        instance if users clicks on cancel button:

        >>> with forms.ProgressBar(title='message',
        ...                        cancellable=True) as pb:
        ...    # do stuff
        ...    if pb.cancelled:
        ...        # wrap up and cancel operation
    """

    xaml_source = 'ProgressBar.xaml'

    def _setup(self, **kwargs):
        self.max_value = 1
        self.new_value = 0
        self.step = kwargs.get('step', 0)

        self.cancelled = False
        has_cancel = kwargs.get('cancellable', False)
        if has_cancel:
            self.show_element(self.cancel_b)

        self.pbar.IsIndeterminate = kwargs.get('indeterminate', False)
        self._title = kwargs.get('title', '{value}/{max_value}')

    def _update_pbar(self):
        self.update_window()
        self.pbar.Maximum = self.max_value
        self.pbar.Value = self.new_value

        # updating title
        title_text = \
            string.Formatter().vformat(self._title,
                                       (),
                                       coreutils.SafeDict(
                                           {'value': self.new_value,
                                            'max_value': self.max_value}
                                           ))

        self.pbar_text.Text = title_text

    def _dispatch_updater(self):
        # ask WPF dispatcher for gui update
        self.pbar.Dispatcher.Invoke(System.Action(self._update_pbar),
                                    Threading.DispatcherPriority.Background)

    @staticmethod
    def _make_return_getter(f, ret):
        # WIP
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            ret.append(f(*args, **kwargs))
        return wrapped_f

    @property
    def title(self):
        """Progress bar title."""
        return self._title

    @title.setter
    def title(self, value):
        if type(value) == str:
            self._title = value

    @property
    def indeterminate(self):
        """Progress bar indeterminate state."""
        return self.pbar.IsIndeterminate

    @indeterminate.setter
    def indeterminate(self, value):
        self.pbar.IsIndeterminate = value

    def clicked_cancel(self, sender, args):
        """Handler for cancel button clicked event."""
        self.cancel_b.Content = 'Cancelling...'
        self.cancelled = True

    def wait_async(self, func, args=()):
        """Call a method asynchronosely and show progress."""
        returns = []
        self.indeterminate = True
        rgfunc = self._make_return_getter(func, returns)
        t = threading.Thread(target=rgfunc, args=args)
        t.start()
        while t.is_alive():
            self._dispatch_updater()

        return returns[0] if returns else None

    def reset(self):
        """Reset progress value to 0."""
        self.update_progress(0, 1)

    def update_progress(self, new_value, max_value=1):
        """Update progress bar state with given min, max values.

        Args:
            new_value (float): current progress value
            max_value (float): total progress value
        """
        self.max_value = max_value
        self.new_value = new_value
        if self.new_value == 0:
            self._dispatch_updater()
        elif self.step > 0:
            if self.new_value % self.step == 0:
                self._dispatch_updater()
        else:
            self._dispatch_updater()


class SearchPrompt(WPFWindow):
    """Standard prompt for pyRevit search.

    Args:
        search_db (list): list of possible search targets
        search_tip (str): text to show in grayscale when search box is empty
        switches (str): list of switches
        width (int): width of search prompt window
        height (int): height of search prompt window

    Returns:
        str, dict: matched strings, and dict of switches if provided
        str: matched string if switches are not provided.

    Example:
        >>> from pyrevit import forms
        >>> # assume search input of '/switch1 target1'
        >>> matched_str, args, switches = forms.SearchPrompt.show(
        ...     search_db=['target1', 'target2', 'target3', 'target4'],
        ...     switches=['/switch1', '/switch2'],
        ...     search_tip='pyRevit Search'
        ...     )
        ... matched_str
        'target1'
        ... args
        ['--help', '--branch', 'branchname']
        ... switches
        {'/switch1': True, '/switch2': False}
    """
    def __init__(self, search_db, width, height, **kwargs):
        """Initialize search prompt window."""
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), 'SearchPrompt.xaml'))
        self.Width = width
        self.MinWidth = self.Width
        self.Height = height

        self.search_tip = kwargs.get('search_tip', '')

        self._search_db = sorted(search_db)
        self._switches = kwargs.get('switches', [])
        self._setup_response()

        self.search_tb.Focus()
        self.hide_element(self.tab_icon)
        self.hide_element(self.return_icon)
        self.search_tb.Text = ''
        self.set_search_results()

    def _setup_response(self, response=None):
        switch_dict = dict.fromkeys(self._switches)
        for switch in self.search_term_switches:
            switch_dict[switch] = True
        arguments = self.search_term_args
        # remove first arg which is command name
        if len(arguments) >= 1:
            arguments = arguments[1:]

        self.response = response, arguments, switch_dict

    @property
    def search_input(self):
        """Current search input."""
        return self.search_tb.Text

    @search_input.setter
    def search_input(self, value):
        self.search_tb.Text = value
        self.search_tb.CaretIndex = len(value)

    @property
    def search_input_parts(self):
        """Current cleaned up search term."""
        return self.search_input.strip().split()

    @property
    def search_term(self):
        """Current cleaned up search term."""
        return self.search_input.lower().strip()

    @property
    def search_term_switches(self):
        """Find matching switches in search term."""
        switches = set()
        for stpart in self.search_input_parts:
            if stpart.lower() in self._switches:
                switches.add(stpart)
        return switches

    @property
    def search_term_args(self):
        """Find arguments in search term."""
        args = []
        switches = self.search_term_switches
        for spart in self.search_input_parts:
            if spart.lower() not in switches:
                args.append(spart)
        return args

    @property
    def search_term_main(self):
        """Current cleaned up search term without the listed switches."""
        if len(self.search_term_args) >= 1:
            return self.search_term_args[0]
        else:
            return ''

    @property
    def search_matches(self):
        """List of matches for the given search term."""
        # remove duplicates while keeping order
        # results = list(set(self._search_results))
        return OrderedDict.fromkeys(self._search_results).keys()

    def update_results_display(self, fill_match=False):
        """Update search prompt results based on current input text."""
        self.directmatch_tb.Text = ''
        self.wordsmatch_tb.Text = ''

        results = self.search_matches
        res_cout = len(results)

        logger.debug('unique results count: {}'.format(res_cout))
        logger.debug('unique results: {}'.format(results))

        if res_cout > 1:
            self.show_element(self.tab_icon)
            self.hide_element(self.return_icon)
        elif res_cout == 1:
            self.hide_element(self.tab_icon)
            self.show_element(self.return_icon)
        else:
            self.hide_element(self.tab_icon)
            self.hide_element(self.return_icon)

        if self._result_index >= res_cout:
            self._result_index = 0

        if self._result_index < 0:
            self._result_index = res_cout - 1

        if not self.search_input:
            self.directmatch_tb.Text = self.search_tip
            return

        if results:
            input_term = self.search_term
            cur_res = results[self._result_index]
            logger.debug('current result: {}'.format(cur_res))
            if fill_match:
                self.search_input = cur_res
            else:
                if cur_res.lower().startswith(input_term):
                    self.directmatch_tb.Text = \
                        self.search_input + cur_res[len(input_term):]
                    logger.debug('directmatch_tb.Text: {}'
                                 .format(self.directmatch_tb.Text))
                else:
                    self.wordsmatch_tb.Text = '- {}'.format(cur_res)
                    logger.debug('wordsmatch_tb.Text: {}'
                                 .format(self.wordsmatch_tb.Text))

            self._setup_response(response=cur_res)
            return True

        self._setup_response()
        return False

    def set_search_results(self, *args):
        """Set search results for returning."""
        self._result_index = 0
        self._search_results = []

        logger.debug('search input: {}'.format(self.search_input))
        logger.debug('search term: {}'.format(self.search_term))
        logger.debug('search term (main): {}'.format(self.search_term_main))
        logger.debug('search term (parts): {}'.format(self.search_input_parts))
        logger.debug('search term (args): {}'.format(self.search_term_args))
        logger.debug('search term (switches): {}'
                     .format(self.search_term_switches))

        for resultset in args:
            logger.debug('result set: {}'.format(resultset))
            self._search_results.extend(sorted(resultset))

        logger.debug('results: {}'.format(self._search_results))

    def find_direct_match(self, input_text):
        """Find direct text matches in search term."""
        results = []
        if input_text:
            for cmd_name in self._search_db:
                if cmd_name.lower().startswith(input_text):
                    results.append(cmd_name)

        return results

    def find_word_match(self, input_text):
        """Find direct word matches in search term."""
        results = []
        if input_text:
            cur_words = input_text.split(' ')
            for cmd_name in self._search_db:
                if all([x in cmd_name.lower() for x in cur_words]):
                    results.append(cmd_name)

        return results

    def search_txt_changed(self, sender, args):
        """Handle text changed event."""
        input_term = self.search_term_main
        dmresults = self.find_direct_match(input_term)
        wordresults = self.find_word_match(input_term)
        self.set_search_results(dmresults, wordresults)
        self.update_results_display()

    def handle_kb_key(self, sender, args):
        """Handle keyboard input event."""
        shiftdown = Input.Keyboard.IsKeyDown(Input.Key.LeftShift) \
            or Input.Keyboard.IsKeyDown(Input.Key.RightShift)
        # Escape: set response to none and close
        if args.Key == Input.Key.Escape:
            self._setup_response()
            self.Close()
        # Enter: close, returns matched response automatically
        elif args.Key == Input.Key.Enter:
            self.Close()
        # Shift+Tab, Tab: Cycle through matches
        elif args.Key == Input.Key.Tab and shiftdown:
            self._result_index -= 1
            self.update_results_display()
        elif args.Key == Input.Key.Tab:
            self._result_index += 1
            self.update_results_display()
        # Up, Down: Cycle through matches
        elif args.Key == Input.Key.Up:
            self._result_index -= 1
            self.update_results_display()
        elif args.Key == Input.Key.Down:
            self._result_index += 1
            self.update_results_display()
        # Right, End: Autocomplete with displayed match
        elif args.Key in [Input.Key.Right,
                          Input.Key.End]:
            self.update_results_display(fill_match=True)

    @classmethod
    def show(cls, search_db,
             width=DEFAULT_SEARCHWND_WIDTH,
             height=DEFAULT_SEARCHWND_HEIGHT, **kwargs):
        """Show search prompt."""
        dlg = cls(search_db, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class RevisionOption(TemplateListItem):
    def __init__(self, revision_element):
        super(RevisionOption, self).__init__(revision_element)

    @property
    def name(self):
        revnum = self.item.SequenceNumber
        if hasattr(self.item, 'RevisionNumber'):
            revnum = self.item.RevisionNumber
        return '{}-{}-{}'.format(revnum,
                                 self.item.Description,
                                 self.item.RevisionDate)


class SheetOption(TemplateListItem):
    def __init__(self, sheet_element):
        super(SheetOption, self).__init__(sheet_element)

    @property
    def name(self):
        return '{} - {}{}' \
            .format(self.item.SheetNumber,
                    self.item.Name,
                    ' (placeholder)' if self.item.IsPlaceholder else '')

    @property
    def number(self):
        return self.item.SheetNumber


class ViewOption(TemplateListItem):
    def __init__(self, view_element):
        super(ViewOption, self).__init__(view_element)

    @property
    def name(self):
        return '{} ({})'.format(self.item.ViewName, self.item.ViewType)


def select_revisions(title='Select Revision',
                     button_name='Select',
                     width=DEFAULT_INPUTWINDOW_WIDTH,
                     multiple=True,
                     filterfunc=None,
                     doc=None):
    revisions = sorted(revit.query.get_revisions(doc=doc),
                       key=lambda x: x.SequenceNumber)

    if filterfunc:
        revisions = filter(filterfunc, revisions)

    # ask user for revisions
    selected_revs = SelectFromList.show(
        [RevisionOption(x) for x in revisions],
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
        )

    if selected_revs:
        return [x.unwrap() for x in selected_revs]


def select_sheets(title='Select Sheets',
                  button_name='Select',
                  width=DEFAULT_INPUTWINDOW_WIDTH,
                  multiple=True,
                  filterfunc=None,
                  doc=None):
    doc = doc or HOST_APP.doc
    all_ops = dict()
    all_sheets = DB.FilteredElementCollector(doc) \
                   .OfClass(DB.ViewSheet) \
                   .WhereElementIsNotElementType() \
                   .ToElements()

    if filterfunc:
        all_sheets = filter(filterfunc, all_sheets)

    all_sheets_ops = sorted([SheetOption(x) for x in all_sheets],
                            key=lambda x: x.number)
    all_ops['All Sheets'] = all_sheets_ops

    sheetsets = revit.query.get_sheet_sets(doc)
    for sheetset in sheetsets:
        sheetset_sheets = sheetset.Views
        if filterfunc:
            sheetset_sheets = filter(filterfunc, sheetset_sheets)
        sheetset_ops = sorted([SheetOption(x) for x in sheetset_sheets],
                              key=lambda x: x.number)
        all_ops[sheetset.Name] = sheetset_ops

    # ask user for multiple sheets
    selected_sheets = SelectFromList.show(
        all_ops,
        title=title,
        group_selector_title='Sheet Sets:',
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
        )

    if selected_sheets:
        return [x.unwrap() for x in selected_sheets]


def select_views(title='Select Views',
                 button_name='Select',
                 width=DEFAULT_INPUTWINDOW_WIDTH,
                 multiple=True,
                 filterfunc=None,
                 doc=None):
    all_graphviews = revit.query.get_all_views(doc=doc)

    if filterfunc:
        all_graphviews = filter(filterfunc, all_graphviews)

    selected_views = SelectFromList.show(
        sorted([ViewOption(x) for x in all_graphviews],
               key=lambda x: x.name),
        title=title,
        button_name=button_name,
        width=width,
        multiselect=multiple,
        checked_only=True
        )

    if selected_views:
        return [x.unwrap() for x in selected_views]


def select_open_docs(title='Select Open Documents',
                     button_name='OK',
                     width=DEFAULT_INPUTWINDOW_WIDTH,
                     multiple=True,
                     filterfunc=None):
    # find open documents other than the active doc
    open_docs = [d for d in revit.docs if not d.IsLinked]
    open_docs.remove(revit.doc)

    if len(open_docs) < 1:
        alert('Only one active document is found. '
              'At least two documents must be open. '
              'Operation cancelled.')
        return

    return SelectFromList.show(
        open_docs,
        name_attr='Title',
        multiselect=multiple,
        title=title,
        button_name=button_name,
        filterfunc=filterfunc
        )


def select_titleblocks(title='Select Titleblock',
                       button_name='Select',
                       no_tb_option='No Title Block',
                       width=DEFAULT_INPUTWINDOW_WIDTH,
                       multiple=False,
                       filterfunc=None,
                       doc=None):
    doc = doc or HOST_APP.doc
    titleblocks = DB.FilteredElementCollector(doc)\
                    .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)\
                    .WhereElementIsElementType()\
                    .ToElements()

    tblock_dict = {'{}: {}'.format(tb.FamilyName,
                                   revit.ElementWrapper(tb).name): tb.Id
                   for tb in titleblocks}
    tblock_dict[no_tb_option] = DB.ElementId.InvalidElementId
    selected_titleblocks = SelectFromList.show(tblock_dict.keys(),
                                               title=title,
                                               button_name=button_name,
                                               width=width,
                                               multiselect=multiple,
                                               filterfunc=filterfunc)
    if selected_titleblocks:
        if multiple:
            return [tblock_dict[x] for x in selected_titleblocks]
        else:
            return tblock_dict[selected_titleblocks]


def alert(msg, title='pyRevit',
          cancel=False, yes=False, no=False, retry=False, exit=False):
    buttons = UI.TaskDialogCommonButtons.Ok

    if any([cancel, yes, no, retry]):
        buttons = UI.TaskDialogCommonButtons.None   # noqa

        if cancel:
            buttons |= UI.TaskDialogCommonButtons.Cancel
        if yes:
            buttons |= UI.TaskDialogCommonButtons.Yes
        if no:
            buttons |= UI.TaskDialogCommonButtons.No
        if retry:
            buttons |= UI.TaskDialogCommonButtons.Retry

    res = UI.TaskDialog.Show(title, msg, buttons)

    if not exit:
        if res == UI.TaskDialogResult.Ok \
                or res == UI.TaskDialogResult.Yes \
                or res == UI.TaskDialogResult.Retry:
            return True
        else:
            return False

    sys.exit()


def alert_ifnot(condition, msg, *args, **kwargs):
    if not condition:
        return alert(msg, *args, **kwargs)


def pick_folder():
    fb_dlg = Forms.FolderBrowserDialog()
    if fb_dlg.ShowDialog() == Forms.DialogResult.OK:
        return fb_dlg.SelectedPath


def pick_file(file_ext='', files_filter='', init_dir='',
              restore_dir=True, multi_file=False, unc_paths=False):
    of_dlg = Forms.OpenFileDialog()
    if files_filter:
        of_dlg.Filter = files_filter
    else:
        of_dlg.Filter = '|*.{}'.format(file_ext)
    of_dlg.RestoreDirectory = restore_dir
    of_dlg.Multiselect = multi_file
    if init_dir:
        of_dlg.InitialDirectory = init_dir
    if of_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(of_dlg.FileName)
        return of_dlg.FileName


def save_file(file_ext='', files_filter='', init_dir='', default_name='',
              restore_dir=True, unc_paths=False):
    sf_dlg = Forms.SaveFileDialog()
    if files_filter:
        sf_dlg.Filter = files_filter
    else:
        sf_dlg.Filter = '|*.{}'.format(file_ext)
    sf_dlg.RestoreDirectory = restore_dir
    if init_dir:
        sf_dlg.InitialDirectory = init_dir

    # setting default filename
    sf_dlg.FileName = default_name

    if sf_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(sf_dlg.FileName)
        return sf_dlg.FileName


def pick_excel_file(save=False):
    if save:
        return save_file(file_ext='xlsx')
    return pick_file(files_filter='All Files (*.*)|*.*|'
                     'Excel Workbook (*.xlsx)|*.xlsx|'
                     'Excel 97-2003 Workbook|*.xls')


def save_excel_file():
    return pick_excel_file(save=True)


def check_workshared(doc=None):
    doc = doc or HOST_APP.doc
    if not doc.IsWorkshared:
        alert('Model is not workshared.')
        return False
    return True


def check_selection(exit=False):
    if revit.get_selection().is_empty:
        alert('At least one element must be selected.', exit=exit)
        return False
    return True
