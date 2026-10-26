"""Interactive form contracts exercised identically on IronPython and CPython.

These tests drive real WPF events with a bounded DispatcherTimer. They neither
write model data nor require a person to answer the modal dialogs.
"""

import datetime
import unittest

from pyrevit import forms, framework


FIXTURE = {}


def _modal(window_type, call, action):
    captured = {}
    failures = []
    original = window_type.__init__
    dispatcher = framework.Threading.Dispatcher.CurrentDispatcher
    timer = framework.Threading.DispatcherTimer()
    timer.Interval = framework.System.TimeSpan.FromMilliseconds(30)

    def initialize(self, *args, **kwargs):
        original(self, *args, **kwargs)
        captured["dialog"] = self

    def tick(sender, args):
        dialog = captured.get("dialog")
        if dialog is None:
            return
        timer.Stop()
        try:
            action(dialog)
        except Exception as error:
            failures.append(error)
        finally:
            dialog.Close()

    def unhandled(sender, args):
        failures.append(RuntimeError(str(args.Exception)))
        args.Handled = True
        timer.Stop()
        if captured.get("dialog") is not None:
            captured["dialog"].Close()

    window_type.__init__ = initialize
    timer.Tick += tick
    dispatcher.UnhandledException += unhandled
    timer.Start()
    try:
        result = call()
    finally:
        timer.Stop()
        timer.Tick -= tick
        dispatcher.UnhandledException -= unhandled
        window_type.__init__ = original
        if captured.get("dialog") is not None:
            captured["dialog"].Close()
    if failures:
        raise failures[0]
    return result


def _click(button):
    button.RaiseEvent(
        framework.Windows.RoutedEventArgs(framework.Controls.Button.ClickEvent)
    )


def _select_first(dialog):
    dialog.list_lb.SelectedIndex = 0
    _click(dialog.select_b)


def _visual_tree(root):
    yield root
    for index in range(framework.Media.VisualTreeHelper.GetChildrenCount(root)):
        for child in _visual_tree(
            framework.Media.VisualTreeHelper.GetChild(root, index)
        ):
            yield child


class ModalFormsParityTests(unittest.TestCase):
    """Check values, actual control events and Python object identity."""

    def test_string_accept_and_cancel(self):
        """Public string input accepts edited text and cancellation returns None."""

        def accept(dialog):
            dialog.stringValue_tb.Text = "edited"
            _click(dialog.okayButton)

        value = _modal(
            forms.GetValueWindow,
            lambda: forms.ask_for_string(default="initial"),
            accept,
        )
        self.assertEqual("edited", value)
        value = _modal(
            forms.GetValueWindow,
            lambda: forms.ask_for_string(),
            lambda dialog: dialog.Close(),
        )
        self.assertIsNone(value)

    def test_unique_string_validation(self):
        """Reserved input disables OK until the user enters a free name."""

        def accept(dialog):
            self.assertFalse(dialog.okayButton.IsEnabled)
            dialog.stringValue_tb.Text = "free"
            self.assertTrue(dialog.okayButton.IsEnabled)
            _click(dialog.okayButton)

        value = _modal(
            forms.GetValueWindow,
            lambda: forms.ask_for_unique_string(["taken"], default="taken"),
            accept,
        )
        self.assertEqual("free", value)

    def test_dropdown_date_and_slider(self):
        """Public input wrappers preserve their existing Python return types."""

        def dropdown(dialog):
            dialog.dropdown_cb.SelectedIndex = 1
            _click(dialog.okayButton)

        value = _modal(
            forms.GetValueWindow,
            lambda: forms.ask_for_one_item(["First", "Second"]),
            dropdown,
        )
        self.assertEqual("Second", value)
        value = _modal(
            forms.GetValueWindow,
            lambda: forms.ask_for_date(default=datetime.datetime(2026, 10, 26)),
            lambda dialog: _click(dialog.okayButton),
        )
        self.assertEqual(datetime.datetime(2026, 10, 26), value)
        value = _modal(
            forms.GetValueWindow,
            lambda: forms.ask_for_number_slider(default=25, min=0, max=100, interval=5),
            lambda dialog: _click(dialog.okayButton),
        )
        self.assertEqual(25.0, value)

    def test_command_switch_filter_and_response(self):
        """Filtering and generated button events return the selected command and switches."""

        def accept(dialog):
            dialog.search_tb.Text = "Second"
            buttons = [
                item
                for item in dialog.button_list.Children
                if isinstance(item, framework.Controls.Button)
            ]
            self.assertEqual(
                framework.Windows.Visibility.Collapsed, buttons[0].Visibility
            )
            _click(buttons[1])

        value = _modal(
            forms.CommandSwitchWindow,
            lambda: forms.CommandSwitchWindow.show(
                ["First", "Second"], switches={"Enabled": True}
            ),
            accept,
        )
        self.assertEqual(("Second", {"Enabled": True}), value)

    def test_single_selection_preserves_item_identity(self):
        """A list returns the original Python object rather than a binding adapter."""
        first = object()
        second = object()

        def accept(dialog):
            dialog.list_lb.SelectedIndex = 1
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show([first, second]),
            accept,
        )
        self.assertIs(second, value)

    def test_grouped_multiselect_and_filter(self):
        """Checked values survive filtering and selection in another group."""

        def accept(dialog):
            dialog.check_all(None, None)
            dialog.search_tb.Text = "Alpha"
            self.assertEqual(1, dialog.list_lb.Items.Count)
            dialog.ctx_groups_selector_cb.SelectedIndex = 1
            dialog.search_tb.Text = ""
            dialog.check_all(None, None)
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show(
                {"A": ["Alpha", "Other"], "B": ["Beta"]}, multiselect=True
            ),
            accept,
        )
        self.assertEqual(["Alpha", "Other", "Beta"], value)

    def test_return_all_preserves_wrappers_and_reset(self):
        """Return-all and reset callbacks expose original TemplateListItem instances."""
        items = [
            forms.TemplateListItem("First"),
            forms.TemplateListItem("Second", checked=True),
        ]
        observed = []

        def reset(values):
            observed.extend(values)
            for value in values:
                value.checked = False

        def accept(dialog):
            _click(dialog.reset_b)
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show(
                items, multiselect=True, return_all=True, resetfunc=reset
            ),
            accept,
        )
        self.assertEqual(items, observed)
        self.assertEqual(items, value)
        self.assertFalse(any(bool(item) for item in value))

    def test_prompt_and_progress_overlays(self):
        """Command-scoped overlays update and cancellation is received before cleanup."""
        with forms.WarningBar(title="Forms parity warning") as warning:
            self.assertEqual("Forms parity warning", warning.message_tb.Text)
        with forms.ProgressBar(
            title="{value}/{max_value}", cancellable=True
        ) as progress:
            progress.update_progress(3, 10)
            self.assertEqual(3.0, progress.pbar.Value)
            self.assertEqual("3/10", progress.pbar_text.Text)
            _click(progress.cancel_b)
            self.assertTrue(progress.cancelled)

    def test_search_prompt_keyboard_accept(self):
        """Search text and the shipped keyboard handler accept a matching command."""
        from pyrevit.forms import _backend

        def accept(dialog):
            dialog.search_tb.Text = "be"
            native = _backend.unwrap(dialog)
            source = framework.Windows.PresentationSource.FromVisual(native)
            event = framework.Input.KeyEventArgs(
                framework.Input.Keyboard.PrimaryDevice,
                source,
                0,
                framework.Input.Key.Enter,
            )
            event.RoutedEvent = framework.Input.Keyboard.PreviewKeyUpEvent
            native.RaiseEvent(event)

        value = _modal(
            forms.SearchPrompt,
            lambda: forms.SearchPrompt.show(["Alpha", "Beta"]),
            accept,
        )
        self.assertEqual("Beta", value[0])

    def test_color_swatch_template(self):
        """The actual color template binds forwarded RGB properties and returns the RGB."""
        from pyrevit.coreutils import colors
        from pyrevit.forms import _backend

        expected = next(iter(colors.COLORS.values()))

        def accept(dialog):
            native = _backend.unwrap(dialog)
            native.UpdateLayout()
            brushes = [
                item.Background
                for item in _visual_tree(native)
                if isinstance(item, framework.Controls.Border)
                and item.Background is not None
            ]
            self.assertTrue(
                any(str(brush) == "#FF" + expected.hex_color[1:] for brush in brushes)
            )
            _select_first(dialog)

        value = _modal(forms.SelectFromList, lambda: forms.select_swatch(), accept)
        self.assertIs(expected, value)

    def test_custom_reactive_window(self):
        """Custom modal controls receive notifications and write edits back to Python."""

        class Window(forms.WPFWindow, forms.Reactive):
            def __init__(self):
                self._message = "initial"
                forms.WPFWindow.__init__(
                    self,
                    '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><StackPanel><TextBlock x:Name="label" Text="{Binding message}"/><TextBox x:Name="editor" Text="{Binding message, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"/></StackPanel></Window>',
                    literal_string=True,
                )
                self.DataContext = self

            @forms.reactive
            def message(self):
                return self._message

            @message.setter
            def message(self, value):
                self._message = value

        def verify(window):
            window.label.GetBindingExpression(
                framework.Controls.TextBlock.TextProperty
            ).UpdateTarget()
            self.assertEqual("initial", window.label.Text)
            window.message = "updated"
            window.label.GetBindingExpression(
                framework.Controls.TextBlock.TextProperty
            ).UpdateTarget()
            self.assertEqual("updated", window.label.Text)
            window.editor.Text = "typed"
            window.editor.GetBindingExpression(
                framework.Controls.TextBox.TextProperty
            ).UpdateSource()
            self.assertEqual("typed", window.message)

        _modal(Window, lambda: Window().show_dialog(), verify)

    def test_custom_window_programmatic_events(self):
        """Custom modal windows retain direct CLR event subscriptions."""

        class Window(forms.WPFWindow):
            events = []

            def __init__(self):
                forms.WPFWindow.__init__(
                    self,
                    '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
                    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
                    '<StackPanel><Button x:Name="accept"/></StackPanel></Window>',
                    literal_string=True,
                )
                self.clicks = 0
                self.closes = 0
                self.accept.Click += self.accept_clicked
                self.Closed += self.closed

            def accept_clicked(self, sender, args):
                self.clicks += 1
                self.events.append("click")
                self.Close()

            def closed(self, sender, args):
                self.closes += 1
                self.events.append("closed")

        def verify(window):
            _click(window.accept)
            self.assertEqual(1, window.clicks)

        _modal(Window, lambda: Window().ShowDialog(), verify)
        self.assertEqual(["click", "closed"], Window.events)


class DocumentFormsParityTests(unittest.TestCase):
    """Drive the public Revit selectors against an explicit disposable fixture."""

    def setUp(self):
        """Require the fixture created inside the acceptance run's rollback scope."""
        if not FIXTURE:
            self.skipTest("Run with the Revit acceptance fixture")
        self.doc = FIXTURE["doc"]

    def _select(self, call, select_action=_select_first):
        return _modal(forms.SelectFromList, call, select_action)

    def test_views(self):
        """View grouping preserves the original Revit element."""
        expected = FIXTURE["view"]
        selected = self._select(
            lambda: forms.select_views(
                multiple=False,
                doc=self.doc,
                filterfunc=lambda item: item.Id == expected.Id,
            )
        )
        self.assertEqual(expected.Id, selected.Id)

    def test_sheets(self):
        """Sheet wrappers return the original ViewSheet."""
        expected = FIXTURE["sheet"]
        selected = self._select(
            lambda: forms.select_sheets(
                multiple=False,
                doc=self.doc,
                filterfunc=lambda item: item.Id == expected.Id,
            )
        )
        self.assertEqual(expected.Id, selected.Id)

    def test_revisions(self):
        """Revision labels and their element identity agree across engines."""
        expected = FIXTURE["revision"]
        selected = self._select(
            lambda: forms.select_revisions(
                multiple=False,
                doc=self.doc,
                filterfunc=lambda item: item.Id == expected.Id,
            )
        )
        self.assertEqual(expected.Id, selected.Id)

    def test_schedules(self):
        """Schedule selectors return the original schedule."""
        expected = FIXTURE["schedule"]
        selected = self._select(
            lambda: forms.select_schedules(
                multiple=False,
                doc=self.doc,
                filterfunc=lambda item: item.Id == expected.Id,
            )
        )
        self.assertEqual(expected.Id, selected.Id)

    def test_viewtemplates(self):
        """View-template labels and selection work with live Revit objects."""
        expected = FIXTURE["template"]
        selected = self._select(
            lambda: forms.select_viewtemplates(
                multiple=False,
                doc=self.doc,
                filterfunc=lambda item: item.Id == expected.Id,
            )
        )
        self.assertEqual(expected.Id, selected.Id)

    def test_levels(self):
        """Level ordering and wrappers preserve the selected element."""
        expected = FIXTURE["level"]
        selected = self._select(
            lambda: forms.select_levels(
                multiple=False,
                doc=self.doc,
                filterfunc=lambda item: item.Id == expected.Id,
            )
        )
        self.assertEqual(expected.Id, selected.Id)

    def test_open_documents(self):
        """The active document can be selected when the two-document guard is disabled."""
        selected = self._select(
            lambda: forms.select_open_docs(multiple=False, check_more_than_one=False)
        )
        self.assertEqual(self.doc.PathName, selected.PathName)

    def test_titleblocks(self):
        """The explicit no-titleblock option retains its invalid ElementId result."""
        from pyrevit import DB
        from pyrevit.compat import get_elementid_value_func

        no_titleblock = "No Title Block"

        def select_no_titleblock(dialog):
            options = dialog._get_active_ctx()
            selected_index = next(
                index
                for index, option in enumerate(options)
                if option.item == no_titleblock
            )
            dialog.list_lb.SelectedIndex = selected_index
            _click(dialog.select_b)

        selected = self._select(
            lambda: forms.select_titleblocks(doc=self.doc, no_tb_option=no_titleblock),
            select_no_titleblock,
        )
        get_elementid_value = get_elementid_value_func()
        self.assertEqual(
            get_elementid_value(DB.ElementId.InvalidElementId),
            get_elementid_value(selected),
        )

    def test_parameters(self):
        """Parameter selection returns a populated ParamDef rather than a native adapter."""
        selected = self._select(
            lambda: forms.select_parameters(
                FIXTURE["view"],
                multiple=False,
                include_type=False,
                exclude_readonly=False,
            )
        )
        self.assertIsInstance(selected, forms.ParamDef)
        self.assertTrue(selected.name)

    def test_settings_window(self):
        """Dynamic settings controls validate and return values without writing config files."""
        from pyrevit import script
        from pyrevit.forms import settings_window

        class Config(object):
            def __init__(self):
                self.values = {}

            def get_option(self, name, default=None):
                return self.values.get(name, default)

            def set_option(self, name, value):
                self.values[name] = value

        config = Config()
        saved = []
        get_config = script.get_config
        save_config = script.save_config
        script.get_config = lambda section=None: config
        script.save_config = lambda: saved.append(True)
        schema = [
            {
                "name": "message",
                "type": "string",
                "label": "Message",
                "default": "initial",
            },
            {
                "name": "choice",
                "type": "choice",
                "label": "Choice",
                "options": ["First", "Second"],
                "default": "First",
            },
            {"name": "enabled", "type": "bool", "label": "Enabled", "default": False},
            {
                "name": "amount",
                "type": "slider",
                "label": "Amount",
                "default": 25,
                "min": 0,
                "max": 100,
            },
        ]

        def accept(dialog):
            dialog.message.Text = "edited"
            dialog.choice.SelectedIndex = 1
            dialog.enabled.IsChecked = True
            dialog.amount.Value = 30
            _click(dialog.save_button)

        try:
            result = _modal(
                settings_window.SettingsWindow,
                lambda: settings_window.show_settings(schema),
                accept,
            )
            self.assertTrue(result)
            self.assertEqual(
                {
                    "message": "edited",
                    "choice": "Second",
                    "enabled": True,
                    "amount": 30.0,
                },
                config.values,
            )
            self.assertEqual([True], saved)
        finally:
            script.get_config = get_config
            script.save_config = save_config
