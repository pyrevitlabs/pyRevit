"""Keyboard-filterable command and switch selection dialogs."""

from .base import DEFAULT_CMDSWITCHWND_WIDTH
from .base import DEFAULT_RECOGNIZE_ACCESS_KEY
from .base import WPF_COLLAPSED
from .base import WPF_VISIBLE
from .dialogs import TemplateUserInputWindow
from pyrevit import framework
from pyrevit.framework import Input
from pyrevit.framework import Media
from . import _backend


class CommandSwitchWindow(TemplateUserInputWindow):
    """Standard form to select from a list of command options.

    Keyword Args:
        context (list[str]): list of command options to choose from
        switches (list[str]): list of on/off switches
        message (str): window title message
        config (dict): dictionary of config dicts for options or switches
        recognize_access_key (bool): recognize '_' as mark of access key

    Returns:
        (str | tuple[str, dict]): name of selected option.
            if ``switches`` option is used, returns a tuple
            of selection option name and dict of switches

    Examples:
        This is an example with series of command options:

        ```python
        from pyrevit import forms
        ops = ['option1', 'option2', 'option3', 'option4']
        forms.CommandSwitchWindow.show(ops, message='Select Option')
        'option2'
        ```

        A more advanced example of combining command options, on/off switches,
        and option or switch configuration options:

        ```python
        from pyrevit import forms
        ops = ['option1', 'option2', 'option3', 'option4']
        switches = ['switch1', 'switch2']
        cfgs = {'option1': { 'background': '0xFF55FF'}}
        rops, rswitches = forms.CommandSwitchWindow.show(
            ops,
            switches=switches,
            message='Select Option',
            config=cfgs,
            recognize_access_key=False
            )
        rops
        'option2'
        rswitches
        {'switch1': False, 'switch2': True}
        ```
    """

    xaml_source = "CommandSwitchWindow.xaml"
    _binding_exclude = True

    def _setup(self, **kwargs):
        self.selected_switch = ""
        self.Width = DEFAULT_CMDSWITCHWND_WIDTH
        self.Title = "Command Options"

        message = kwargs.get("message", None)
        self._switches = kwargs.get("switches", [])
        if not isinstance(self._switches, dict):
            self._switches = dict.fromkeys(self._switches)

        configs = kwargs.get("config", None)

        self.message_label.Content = message if message else "Pick a command option:"

        self.Resources["pyRevitRecognizesAccessKey"] = kwargs.get(
            "recognize_access_key", DEFAULT_RECOGNIZE_ACCESS_KEY
        )

        # creates the switches first
        for switch, state in self._switches.items():
            my_togglebutton = framework.Controls.Primitives.ToggleButton()
            my_togglebutton.Content = switch
            my_togglebutton.IsChecked = state if state else False
            if configs and switch in configs:
                self._set_config(my_togglebutton, configs[switch])
            self.button_list.Children.Add(my_togglebutton)

        for option in self._context:
            my_button = framework.Controls.Button()
            my_button.Content = option
            _backend.bind_control_event(self, my_button, "Click", self.process_option)
            if configs and option in configs:
                self._set_config(my_button, configs[option])
            self.button_list.Children.Add(my_button)

        self._setup_response()
        self.search_tb.Focus()
        self._filter_options()

    @staticmethod
    def _set_config(item, config_dict):
        bg = config_dict.get("background", None)
        if bg:
            bg = bg.replace("0x", "#")
            item.Background = Media.BrushConverter().ConvertFrom(bg)

    def _setup_response(self, response=None):
        if self._switches:
            switches = [x for x in self.button_list.Children if hasattr(x, "IsChecked")]
            self.response = response, {x.Content: x.IsChecked for x in switches}
        else:
            self.response = response

    def _filter_options(self, option_filter=None):
        if option_filter:
            self.search_tb.Tag = ""
            option_filter = option_filter.lower()
            for button in self.button_list.Children:
                if option_filter not in button.Content.lower():
                    button.Visibility = WPF_COLLAPSED
                else:
                    button.Visibility = WPF_VISIBLE
        else:
            self.search_tb.Tag = (
                "Type to Filter / Tab to Select / Enter or Click to Run"
            )
            for button in self.button_list.Children:
                button.Visibility = WPF_VISIBLE

    def _get_active_button(self):
        buttons = []
        for button in self.button_list.Children:
            if button.Visibility == WPF_VISIBLE:
                buttons.append(button)
        if len(buttons) == 1:
            return buttons[0]
        else:
            for x in buttons:
                if x.IsFocused:
                    return x

    def handle_click(self, sender, args):  # pylint: disable=W0613
        """Handle mouse click."""
        self.Close()

    def handle_input_key(self, sender, args):
        """Handle keyboard inputs."""
        if args.Key == Input.Key.Escape:
            if self.search_tb.Text:
                self.search_tb.Text = ""
            else:
                self.Close()
        elif args.Key == Input.Key.Enter:
            active_button = self._get_active_button()
            if active_button:
                if isinstance(
                    active_button, framework.Controls.Primitives.ToggleButton
                ):
                    return
                self.process_option(active_button, None)
                args.Handled = True
        elif (
            args.Key != Input.Key.Tab
            and args.Key != Input.Key.Space
            and args.Key != Input.Key.LeftShift
            and args.Key != Input.Key.RightShift
        ):
            self.search_tb.Focus()

    def search_txt_changed(self, sender, args):  # pylint: disable=W0613
        """Handle text change in search box."""
        self._filter_options(option_filter=self.search_tb.Text)

    def process_option(self, sender, args):  # pylint: disable=W0613
        """Handle click on command option button."""
        if sender:
            self._setup_response(response=sender.Content)
        self.Close()
