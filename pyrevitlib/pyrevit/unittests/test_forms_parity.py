"""Interactive form contracts exercised identically on IronPython and CPython.

These tests drive real WPF events with a bounded DispatcherTimer. They neither
write model data nor require a person to answer the modal dialogs.

IronPython is the reference: every test asserts the result IronPython's
``wpf.LoadComponent`` windows produce, and CPython must match it. Where the
engines are known to differ by design, the test asserts both sides explicitly.
"""

import datetime
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from collections import namedtuple

from pyrevit import forms, framework
from pyrevit.compat import IRONPY
from pyrevit.forms import _backend


FIXTURE = {}

_MODAL_WATCHDOG_SECONDS = 15

_NAMESPACES = (
    'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"'
)


def _modal(window_type, call, action):
    captured = {}
    failures = []
    original = window_type.__init__
    dispatcher = framework.Threading.Dispatcher.CurrentDispatcher
    timer = framework.Threading.DispatcherTimer()
    timer.Interval = framework.System.TimeSpan.FromMilliseconds(30)
    watchdog = framework.Threading.DispatcherTimer()
    watchdog.Interval = framework.System.TimeSpan.FromSeconds(_MODAL_WATCHDOG_SECONDS)

    def expire(sender, args):
        watchdog.Stop()
        failures.append(RuntimeError("modal dialog was still open after the watchdog"))
        if captured.get("dialog") is not None:
            captured["dialog"].Close()

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
    watchdog.Tick += expire
    dispatcher.UnhandledException += unhandled
    timer.Start()
    watchdog.Start()
    try:
        result = call()
    finally:
        timer.Stop()
        watchdog.Stop()
        timer.Tick -= tick
        watchdog.Tick -= expire
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


def _markup(body, attributes=""):
    return (
        "<Window "
        + _NAMESPACES
        + ' Width="360" Height="320" ShowActivated="False" '
        + attributes
        + ">"
        + body
        + "</Window>"
    )


def _native(window):
    return _backend.unwrap(window)


def _same(first, second):
    return framework.System.Runtime.CompilerServices.RuntimeHelpers.Equals(
        first, second
    )


def _of_type(root, clr_type):
    return [item for item in _visual_tree(root) if isinstance(item, clr_type)]


def _texts(root):
    return [item.Text for item in _of_type(root, framework.Controls.TextBlock)]


def _clr_items(values):
    items = framework.System.Collections.Generic.List[framework.System.Object]()
    for value in values:
        items.Add(value)
    return items


def _pump():
    """Run queued dispatcher work down to Background priority."""
    frame = framework.Threading.DispatcherFrame()

    def stop():
        frame.Continue = False

    framework.Threading.Dispatcher.CurrentDispatcher.BeginInvoke(
        framework.Threading.DispatcherPriority.Background, framework.System.Action(stop)
    )
    framework.Threading.Dispatcher.PushFrame(frame)


def _mouse(element, routed_event, button, clicks=1):
    """Raise a mouse-button event with an explicit click count."""
    args = framework.Input.MouseButtonEventArgs(
        framework.Input.Mouse.PrimaryDevice, 0, button
    )
    args.RoutedEvent = routed_event
    args.GetType().GetProperty("ClickCount").SetValue(args, clicks)
    element.RaiseEvent(args)


def _press(element, button, clicks=1):
    """Raise the tunnelling then bubbling mouse-down pair WPF raises for a press."""
    _mouse(element, framework.Input.Mouse.PreviewMouseDownEvent, button, clicks)
    _mouse(element, framework.Input.Mouse.MouseDownEvent, button, clicks)


def _key(element, routed_event, key):
    source = framework.Windows.PresentationSource.FromVisual(element)
    args = framework.Input.KeyEventArgs(
        framework.Input.Keyboard.PrimaryDevice, source, 0, key
    )
    args.RoutedEvent = routed_event
    element.RaiseEvent(args)
    return args


class _Shown(object):
    """Show a window for the block so templates, layout and input sources exist."""

    def __init__(self, window):
        self.window = window

    def __enter__(self):
        self.window.Show()
        native = _native(self.window)
        native.UpdateLayout()
        _pump()
        return native

    def __exit__(self, exception_type, exception, traceback):
        self.window.Close()


class _XamlWindow(forms.WPFWindow):
    """Load literal window markup; subclasses define the handlers it names."""

    def __init__(self, body, attributes=""):
        self.seen = []
        forms.WPFWindow.__init__(self, _markup(body, attributes), literal_string=True)


class _Plain(object):
    """Plain Python model: no Reactive base and no change notification."""

    def __init__(self, **values):
        self.__dict__.update(values)


class _Row(_Plain):
    def __init__(self, name, **values):
        _Plain.__init__(self, name=name, checked=False, **values)

    def __repr__(self):
        return "_Row({0!r})".format(self.name)


class _Message(forms.Reactive):
    def __init__(self, message):
        super(_Message, self).__init__()
        self._message = message

    @forms.reactive
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value


_Item = namedtuple("_Item", "name value")


class ModalFormsParityTests(unittest.TestCase):
    """Check values, actual control events and Python object identity."""

    def test_balloon_notification(self):
        """InfoCenter balloon notifications run through the active engine."""
        try:
            import Autodesk.Internal.InfoCenter
        except ImportError:
            self.skipTest("Revit InfoCenter is required")
        forms.show_balloon("CPython Forms", "Notification compatibility check")

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
        """A modal window bound to a Reactive view model updates in both directions.

        The view-model pattern of View Range and Print Sheets.
        """

        class ReactiveParityWindow(forms.WPFWindow):
            def __init__(self):
                forms.WPFWindow.__init__(
                    self,
                    _markup(
                        '<StackPanel><TextBlock x:Name="label" Text="{Binding message}"/>'
                        '<TextBox x:Name="editor" Text="{Binding message, Mode=TwoWay, '
                        'UpdateSourceTrigger=PropertyChanged}"/></StackPanel>'
                    ),
                    literal_string=True,
                )
                self.model = _Message("initial")
                self.DataContext = self.model

        def verify(window):
            label = window.label.GetBindingExpression(
                framework.Controls.TextBlock.TextProperty
            )
            label.UpdateTarget()
            self.assertEqual("initial", window.label.Text)
            window.model.message = "updated"
            label.UpdateTarget()
            self.assertEqual("updated", window.label.Text)
            window.editor.Text = "typed"
            window.editor.GetBindingExpression(
                framework.Controls.TextBox.TextProperty
            ).UpdateSource()
            self.assertEqual("typed", window.model.message)

        _modal(
            ReactiveParityWindow,
            lambda: ReactiveParityWindow().show_dialog(),
            verify,
        )

    def test_reactive_window_mixin_divergence(self):
        """Intended divergence: a window that is itself Reactive.

        IronPython resolves ``self.OnPropertyChanged`` against the CLR
        ``Window.OnPropertyChanged(DependencyPropertyChangedEventArgs)``, so a
        ``reactive`` setter raises TypeError (base order WPFWindow, Reactive);
        CPython windows are composed controllers and the setter works.
        """

        class ReactiveMixinWindow(forms.WPFWindow, forms.Reactive):
            def __init__(self):
                self._message = "initial"
                forms.WPFWindow.__init__(
                    self,
                    _markup("<Grid/>"),
                    literal_string=True,
                )

            @forms.reactive
            def message(self):
                return self._message

            @message.setter
            def message(self, value):
                self._message = value

        window = ReactiveMixinWindow()
        try:
            try:
                window.message = "updated"
                outcome = window.message
            except TypeError:
                outcome = "TypeError"
        finally:
            window.Close()
        self.assertEqual("TypeError" if IRONPY else "updated", outcome)

    def test_custom_window_programmatic_events(self):
        """Modal windows retain direct CLR event subscriptions made in __init__."""

        class EventParityWindow(forms.WPFWindow):
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

        _modal(EventParityWindow, lambda: EventParityWindow().ShowDialog(), verify)
        self.assertEqual(["click", "closed"], EventParityWindow.events)

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


class BindingParityTests(unittest.TestCase):
    """Plain Python lists and objects at the WPF binding boundary."""

    def test_list_items_source_identity(self):
        """A Python list is the ItemsSource it reads back, with original selections.

        Used by ReValue, Logs, Convert Line Styles and the Extensions window.
        """
        rows = [_Row("a"), _Row("b")]
        window = _XamlWindow(
            '<StackPanel><ListBox x:Name="list_lb" DisplayMemberPath="name"/>'
            '<ComboBox x:Name="combo_cb" DisplayMemberPath="name"/></StackPanel>'
        )
        try:
            for selector in (window.list_lb, window.combo_cb):
                selector.ItemsSource = rows
                selector.SelectedIndex = 1
                self.assertEqual(2, selector.Items.Count)
                self.assertIs(rows[1], selector.SelectedItem)
                self.assertIs(rows, selector.ItemsSource)
        finally:
            window.Close()

    def test_list_mutation_then_refresh(self):
        """Appending to the assigned list shows the new item after Items.Refresh().

        Used by ReValue, ColorSplasher and Manage Packages.
        """
        rows = [_Row("a")]
        window = _XamlWindow('<ListBox x:Name="list_lb" DisplayMemberPath="name"/>')
        try:
            window.list_lb.ItemsSource = rows
            added = _Row("b")
            rows.append(added)
            window.list_lb.Items.Refresh()
            self.assertEqual(2, window.list_lb.Items.Count)
            self.assertIs(added, window.list_lb.Items[1])
        finally:
            window.Close()

    def test_plain_object_property_bindings(self):
        """A plain object binds text, bool, brush, visibility, double, list and triggers.

        Used by Manage Tags (namedtuple Background), Print Sheets (DataTrigger)
        and the pyRevit Settings window (Brush).
        """
        window = _XamlWindow(
            '<StackPanel><TextBlock x:Name="text_tb" Text="{Binding text}"/>'
            '<CheckBox x:Name="flag_cb" IsChecked="{Binding flag}"/>'
            '<Border x:Name="swatch" Height="4" Background="{Binding color}"/>'
            '<TextBlock x:Name="hidden_tb" Text="h" Visibility="{Binding visibility}"/>'
            '<Slider x:Name="amount_sl" Maximum="10" Value="{Binding amount}"/>'
            '<ItemsControl x:Name="nested_ic" ItemsSource="{Binding nested}"/>'
            '<TextBlock x:Name="state_tb"><TextBlock.Style><Style TargetType="TextBlock">'
            '<Setter Property="Tag" Value="miss"/><Style.Triggers>'
            '<DataTrigger Binding="{Binding state}" Value="on">'
            '<Setter Property="Tag" Value="hit"/></DataTrigger>'
            "</Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel>"
        )
        window.DataContext = _Plain(
            text="hello",
            flag=True,
            color="#FF00FF00",
            visibility="Collapsed",
            amount=2.5,
            nested=["x", "y"],
            state="on",
        )
        with _Shown(window):
            observed = {
                "text": window.text_tb.Text,
                "flag": window.flag_cb.IsChecked,
                "color": str(window.swatch.Background),
                "visibility": str(window.hidden_tb.Visibility),
                "amount": window.amount_sl.Value,
                "nested": [str(item) for item in window.nested_ic.Items],
                "trigger": str(window.state_tb.Tag),
            }
        self.assertEqual(
            {
                "text": "hello",
                "flag": True,
                "color": "#FF00FF00",
                "visibility": "Collapsed",
                "amount": 2.5,
                "nested": ["x", "y"],
                "trigger": "hit",
            },
            observed,
        )

    def test_computed_property_binding(self):
        """A read-only @property on a plain object is bound like an attribute.

        Used by Print Sheets list items and Convert Line Styles.
        """

        class Person(object):
            def __init__(self):
                self.first = "Ada"
                self.last = "Lovelace"

            @property
            def full_name(self):
                return self.first + " " + self.last

        window = _XamlWindow('<TextBlock x:Name="name_tb" Text="{Binding full_name}"/>')
        window.DataContext = Person()
        with _Shown(window):
            self.assertEqual("Ada Lovelace", window.name_tb.Text)

    def test_namedtuple_items_in_template(self):
        """Fields of namedtuple items bind inside an item template.

        Used by Manage Tags (TagModifierDef) and Manage Packages (DocPkg).
        """
        items = [_Item("alpha", 1), _Item("beta", 2)]
        window = _XamlWindow(
            '<ListBox x:Name="list_lb"><ListBox.ItemTemplate><DataTemplate>'
            '<TextBlock Text="{Binding value}"/></DataTemplate>'
            "</ListBox.ItemTemplate></ListBox>"
        )
        window.list_lb.ItemsSource = items
        with _Shown(window) as native:
            self.assertEqual(["1", "2"], _texts(window.list_lb))
            window.list_lb.SelectedIndex = 1
            self.assertIs(items[1], window.list_lb.SelectedItem)

    def test_template_list_item_wrapping_namedtuple(self):
        """SelectFromList names a wrapped namedtuple by its field and returns the tuple.

        Used by Manage Tags and Print Sheets (PrintSettingListItem).
        """
        items = [_Item("alpha", 1), forms.TemplateListItem(_Item("beta", 2))]
        labels = []

        def accept(dialog):
            _native(dialog).UpdateLayout()
            labels.extend(_texts(dialog.list_lb))
            dialog.list_lb.SelectedIndex = 1
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList, lambda: forms.SelectFromList.show(items), accept
        )
        self.assertIn("alpha", labels)
        self.assertIn("beta", labels)
        self.assertIs(items[1].item, value)

    def test_nested_path_binding(self):
        """A dotted path walks plain Python attributes.

        Used by Print Sheets (revision.date) and Test XAML (nested.text).
        """
        window = _XamlWindow('<TextBlock x:Name="date_tb" Text="{Binding rev.date}"/>')
        window.DataContext = _Row("sheet", rev=_Plain(date="2026-10-28"))
        with _Shown(window):
            self.assertEqual("2026-10-28", window.date_tb.Text)

    def test_combobox_selected_value_path_two_way(self):
        """SelectedValuePath round-trips a Python int through a TwoWay SelectedValue.

        Used by View Range (level ComboBoxes) and Parameters Values To Parameter.
        """

        class RangeModel(forms.Reactive):
            def __init__(self):
                super(RangeModel, self).__init__()
                self._level = 2
                self.levels = [
                    _Plain(Name="L1", IdValue=1),
                    _Plain(Name="L2", IdValue=2),
                ]

            @forms.reactive
            def level(self):
                return self._level

            @level.setter
            def level(self, value):
                self._level = value

        model = RangeModel()
        window = _XamlWindow(
            '<ComboBox x:Name="level_cb" DisplayMemberPath="Name" '
            'SelectedValuePath="IdValue" ItemsSource="{Binding levels}" '
            'SelectedValue="{Binding level, Mode=TwoWay}"/>'
        )
        window.DataContext = model
        with _Shown(window):
            observed = [window.level_cb.SelectedIndex, window.level_cb.Text]
            window.level_cb.SelectedIndex = 0
            observed.extend([model.level, type(model.level).__name__])
        self.assertEqual([1, "L2", 1, "int"], observed)

    def test_hierarchical_template_two_way_expansion(self):
        """Nested Python children render and IsExpanded writes back to the node.

        Used by Keynotes (is_expanded, children) and Convert Line Styles.
        """
        leaf = _Plain(name="leaf", children=[], expanded=False)
        root = _Plain(name="root", children=[leaf], expanded=True)
        window = _XamlWindow(
            '<TreeView x:Name="tree_tv" ItemsSource="{Binding roots}">'
            '<TreeView.ItemContainerStyle><Style TargetType="TreeViewItem">'
            '<Setter Property="IsExpanded" Value="{Binding expanded, Mode=TwoWay}"/>'
            "</Style></TreeView.ItemContainerStyle><TreeView.ItemTemplate>"
            '<HierarchicalDataTemplate ItemsSource="{Binding children}">'
            '<TextBlock Text="{Binding name}"/></HierarchicalDataTemplate>'
            "</TreeView.ItemTemplate></TreeView>"
        )
        window.DataContext = _Plain(roots=[root])
        with _Shown(window) as native:
            container = window.tree_tv.ItemContainerGenerator.ContainerFromIndex(0)
            native.UpdateLayout()
            observed = [
                container is not None and container.IsExpanded,
                _texts(window.tree_tv),
            ]
            container.IsExpanded = False
            observed.append(root.expanded)
        self.assertEqual([True, ["root", "leaf"], False], observed)

    def test_collection_view_filter_receives_python_items(self):
        """An Items.Filter predicate receives and filters the original Python items.

        Used by ColorSplasher.
        """
        rows = [_Row("keep", keep=True), _Row("drop", keep=False)]
        seen = []

        def accept(item):
            seen.append(item)
            return item.keep

        window = _XamlWindow('<ListBox x:Name="list_lb" DisplayMemberPath="name"/>')
        try:
            window.list_lb.ItemsSource = rows
            window.list_lb.Items.Filter = framework.System.Predicate[
                framework.System.Object
            ](accept)
            self.assertEqual(1, window.list_lb.Items.Count)
            self.assertIs(rows[0], window.list_lb.Items[0])
            self.assertTrue(any(item is rows[1] for item in seen))
        finally:
            window.Close()

    def test_datagrid_sort_description_on_plain_items(self):
        """A SortDescription sorts plain Python rows by attribute name.

        No shipped tool sorts this way yet; DataGrid column-header sorting
        uses the same path.
        """
        rows = [_Row("b"), _Row("c"), _Row("a")]
        window = _XamlWindow(
            '<DataGrid x:Name="grid_dg" AutoGenerateColumns="False" '
            'CanUserAddRows="False" IsReadOnly="True"><DataGrid.Columns>'
            '<DataGridTextColumn Header="Name" Binding="{Binding name}"/>'
            "</DataGrid.Columns></DataGrid>"
        )
        description_type = framework.ComponentModel.SortDescription
        direction_type = (
            framework.System.Type.GetType(
                "System.ComponentModel.SortDescription, WindowsBase"
            )
            .GetProperty("Direction")
            .PropertyType
        )
        ascending = framework.System.Enum.ToObject(direction_type, 0)
        try:
            window.grid_dg.ItemsSource = rows
            window.grid_dg.Items.SortDescriptions.Add(
                description_type("name", ascending)
            )
            ordered = list(window.grid_dg.Items)
            self.assertEqual(["a", "b", "c"], [row.name for row in ordered])
            self.assertIs(rows[2], ordered[0])
        finally:
            window.Close()

    def test_window_data_context_self_with_plain_rows(self):
        """A non-Reactive window bound to itself lists plain rows with TwoWay checks.

        Used by the pyRevit Settings window.
        """

        class SelfBoundWindow(forms.WPFWindow):
            def __init__(self):
                self.rows = [_Row("one"), _Row("two")]
                forms.WPFWindow.__init__(
                    self,
                    _markup(
                        '<ItemsControl x:Name="rows_ic" ItemsSource="{Binding rows}">'
                        "<ItemsControl.ItemTemplate><DataTemplate>"
                        '<CheckBox Content="{Binding name}" '
                        'IsChecked="{Binding checked, Mode=TwoWay}"/>'
                        "</DataTemplate></ItemsControl.ItemTemplate></ItemsControl>"
                    ),
                    literal_string=True,
                )
                self.DataContext = self

        window = SelfBoundWindow()
        with _Shown(window) as native:
            checks = _of_type(native, framework.Controls.CheckBox)
            observed = [str(check.Content) for check in checks]
            if len(checks) == 2:
                checks[1].IsChecked = True
            observed.append(window.rows[1].checked)
        self.assertEqual(["one", "two", True], observed)

    def test_display_member_path_on_plain_objects(self):
        """DisplayMemberPath reads a plain attribute for each generated item.

        Used by the pyRevit Settings window and ColorSplasher.
        """
        window = _XamlWindow('<ListBox x:Name="list_lb" DisplayMemberPath="name"/>')
        window.list_lb.ItemsSource = [_Row("first"), _Row("second")]
        with _Shown(window):
            self.assertEqual(["first", "second"], _texts(window.list_lb))

    def test_unhashable_items(self):
        """Dicts and __eq__-only objects can be listed and selected.

        Dict rows appear in user tools that list parsed records.
        """

        class EqualByKey(object):
            __hash__ = None

            def __init__(self, key):
                self.key = key

            def __eq__(self, other):
                return isinstance(other, EqualByKey) and other.key == self.key

        items = [{"name": "dict"}, EqualByKey("eq")]
        window = _XamlWindow('<ListBox x:Name="list_lb"/>')
        window.list_lb.ItemsSource = items
        with _Shown(window):
            self.assertEqual(2, window.list_lb.Items.Count)
            window.list_lb.SelectedIndex = 1
            self.assertIs(items[1], window.list_lb.SelectedItem)
            window.list_lb.SelectedIndex = 0
            self.assertIs(items[0], window.list_lb.SelectedItem)

    def test_worker_thread_updates_reactive_model(self):
        """A Reactive change made on a worker thread is safe and reads back on the UI thread.

        IronPython reference: the worker assignment raises nothing and the
        bound control shows it once the binding is refreshed on the UI
        thread. The control does not refresh by itself in this host on
        either IronPython version, so automatic refresh is not asserted.
        Used by Test Modeless (Sensors) and Section Box Navigator.
        """
        model = _Message("initial")
        errors = []

        def work():
            try:
                model.message = "worker"
            except Exception as error:
                errors.append(error)

        window = _XamlWindow('<TextBlock x:Name="label" Text="{Binding message}"/>')
        window.DataContext = model
        with _Shown(window):
            worker = threading.Thread(target=work)
            worker.start()
            while worker.is_alive():
                _pump()
                worker.join(0.05)
            window.label.GetBindingExpression(
                framework.Controls.TextBlock.TextProperty
            ).UpdateTarget()
            observed = [model.message, window.label.Text]
        self.assertEqual([], errors)
        self.assertEqual(["worker", "worker"], observed)


class _MenuWindow(_XamlWindow):
    def menu_clicked(self, sender, args):
        self.seen.append(("menu", str(sender.Header)))


def _click_menu(item):
    item.RaiseEvent(
        framework.Windows.RoutedEventArgs(framework.Controls.MenuItem.ClickEvent)
    )


def _drag_args(target, routed_event, data):
    flags = framework.System.Reflection.BindingFlags
    drag_type = framework.System.Type.GetType(
        "System.Windows.DragEventArgs, PresentationCore"
    )
    constructor = drag_type.GetConstructors(flags.NonPublic | flags.Instance)[0]
    values = framework.System.Array[framework.System.Object](
        [
            data,
            getattr(framework.Windows.DragDropKeyStates, "None"),
            framework.Windows.DragDropEffects.Copy,
            target,
            framework.Windows.Point(1, 1),
        ]
    )
    args = constructor.Invoke(values)
    args.RoutedEvent = routed_event
    return args


class EventParityTests(unittest.TestCase):
    """XAML and programmatic event wiring, routing order and Handled semantics."""

    def test_context_menu_inside_data_template(self):
        """A MenuItem Click declared in a DataTemplate's ContextMenu reaches the window.

        Used by Keynotes (add_keynote on the tree item ContextMenu).
        """
        window = _MenuWindow(
            '<ItemsControl x:Name="rows_ic"><ItemsControl.ItemTemplate><DataTemplate>'
            '<TextBlock Text="{Binding}"><TextBlock.ContextMenu><ContextMenu>'
            '<MenuItem Header="Do" Click="menu_clicked"/></ContextMenu>'
            "</TextBlock.ContextMenu></TextBlock></DataTemplate>"
            "</ItemsControl.ItemTemplate></ItemsControl>"
        )
        window.rows_ic.ItemsSource = _clr_items(["row"])
        with _Shown(window) as native:
            menus = [
                item.ContextMenu
                for item in _of_type(native, framework.Controls.TextBlock)
                if item.ContextMenu is not None
            ]
            self.assertEqual(1, len(menus))
            _click_menu(menus[0].Items[0])
        self.assertEqual([("menu", "Do")], window.seen)

    def test_keyed_context_menu_from_item_container_style(self):
        """A named MenuItem in a keyed ContextMenu resource resolves and clicks.

        Used by the pyRevit Settings window, Manage Tags and Print Sheets.
        """
        window = _MenuWindow(
            '<ListBox x:Name="rows_lb"><ListBox.Resources><ContextMenu x:Key="row_menu">'
            '<MenuItem x:Name="delete_item" Header="Delete" Click="menu_clicked"/>'
            "</ContextMenu></ListBox.Resources><ListBox.ItemContainerStyle>"
            '<Style TargetType="ListBoxItem"><Setter Property="ContextMenu" '
            'Value="{StaticResource row_menu}"/></Style></ListBox.ItemContainerStyle>'
            "</ListBox>"
        )
        window.rows_lb.ItemsSource = _clr_items(["row"])
        with _Shown(window):
            named = getattr(window, "delete_item", None)
            container = window.rows_lb.ItemContainerGenerator.ContainerFromIndex(0)
            applied = container.ContextMenu.Items[0]
            self.assertTrue(_same(named, applied))
            _click_menu(applied)
        self.assertEqual([("menu", "Delete")], window.seen)

    def test_named_context_menu_property_element(self):
        """A named MenuItem inside Button.ContextMenu resolves and clicks.

        Used by Keynotes (caseMenu) and Print Sheets (TextBlock.ContextMenu).
        """
        window = _MenuWindow(
            '<Button x:Name="case_b" Content="Case"><Button.ContextMenu>'
            '<ContextMenu><MenuItem x:Name="upper_item" Header="Upper" '
            'Click="menu_clicked"/></ContextMenu></Button.ContextMenu></Button>'
        )
        with _Shown(window):
            self.assertTrue(
                _same(window.case_b.ContextMenu.Items[0], window.upper_item)
            )
            _click_menu(window.upper_item)
        self.assertEqual([("menu", "Upper")], window.seen)

    def test_select_from_list_double_click_accepts(self):
        """A double click on list_lb runs its named MouseDoubleClick handler.

        Used by every SelectFromList-based selector.
        """

        def accept(dialog):
            dialog.list_lb.SelectedIndex = 1
            _press(dialog.list_lb, framework.Input.MouseButton.Left, clicks=2)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show(["first", "second"]),
            accept,
        )
        self.assertEqual("second", value)

    def test_template_mouse_double_click(self):
        """A template MouseDoubleClick ignores single clicks and fires once per double.

        Used by the pyRevit Settings window (list template double click).
        """

        class DoubleClickWindow(_XamlWindow):
            def row_double(self, sender, args):
                self.seen.append(str(args.ChangedButton))

        window = DoubleClickWindow(
            '<ItemsControl x:Name="rows_ic"><ItemsControl.ItemTemplate><DataTemplate>'
            '<ContentControl Content="{Binding}" MouseDoubleClick="row_double"/>'
            "</DataTemplate></ItemsControl.ItemTemplate></ItemsControl>"
        )
        window.rows_ic.ItemsSource = _clr_items(["row"])
        with _Shown(window) as native:
            row = [
                item
                for item in _of_type(native, framework.Controls.ContentControl)
                if str(item.Content) == "row"
                and not isinstance(item, framework.Windows.Window)
            ][0]
            _press(row, framework.Input.MouseButton.Left, clicks=1)
            _press(row, framework.Input.MouseButton.Left, clicks=2)
            _press(row, framework.Input.MouseButton.Right, clicks=2)
        self.assertEqual(["Left", "Right"], window.seen)

    def test_template_preview_key_down_handled_stops_tunnel(self):
        """Tunnelling PreviewKeyDown in a template runs outer first and stops when handled.

        Root-level PreviewKeyDown is used by Keynotes; template use is for parity.
        """

        class KeyWindow(_XamlWindow):
            handle_outer = True

            def outer_key(self, sender, args):
                self.seen.append("outer")
                args.Handled = self.handle_outer

            def inner_key(self, sender, args):
                self.seen.append("inner")

        window = KeyWindow(
            '<ItemsControl x:Name="rows_ic"><ItemsControl.ItemTemplate><DataTemplate>'
            '<Border PreviewKeyDown="outer_key"><TextBox Text="{Binding Mode=OneWay}" '
            'PreviewKeyDown="inner_key"/></Border></DataTemplate>'
            "</ItemsControl.ItemTemplate></ItemsControl>"
        )
        window.rows_ic.ItemsSource = _clr_items(["row"])
        with _Shown(window) as native:
            editor = _of_type(native, framework.Controls.TextBox)[0]
            _key(
                editor,
                framework.Input.Keyboard.PreviewKeyDownEvent,
                framework.Input.Key.F5,
            )
            window.handle_outer = False
            _key(
                editor,
                framework.Input.Keyboard.PreviewKeyDownEvent,
                framework.Input.Key.F5,
            )
        self.assertEqual(["outer", "outer", "inner"], window.seen)

    def test_template_drop_handled_hides_outer_drop(self):
        """A template Drop that sets Handled keeps the outer ItemsControl Drop silent.

        Used by Keynotes (tree_item_drop) and Edit Naming Formats.
        """

        class DropWindow(_XamlWindow):
            def row_drop(self, sender, args):
                self.seen.append(("row", str(args.Data.GetData("Text"))))
                args.Handled = True

            def outer_drop(self, sender, args):
                self.seen.append(("outer", None))

        window = DropWindow(
            '<ItemsControl x:Name="rows_ic" AllowDrop="True" Drop="outer_drop">'
            "<ItemsControl.ItemTemplate><DataTemplate>"
            '<Border Width="20" Height="20" Background="Red" AllowDrop="True" '
            'Drop="row_drop"/></DataTemplate></ItemsControl.ItemTemplate></ItemsControl>'
        )
        window.rows_ic.ItemsSource = _clr_items(["row"])
        with _Shown(window) as native:
            border = [
                item
                for item in _of_type(native, framework.Controls.Border)
                if str(item.Background) == "#FFFF0000"
            ][0]
            data = framework.Windows.DataObject("Text", "payload")
            args = _drag_args(border, framework.Windows.DragDrop.PreviewDropEvent, data)
            border.RaiseEvent(args)
            args.RoutedEvent = framework.Windows.DragDrop.DropEvent
            border.RaiseEvent(args)
        self.assertEqual([("row", "payload")], window.seen)

    def test_preview_text_input_truthy_handled(self):
        """``args.Handled`` accepts a re.match result or None, by truthiness.

        Used by Print Sheets (validate_index_start).
        """

        class DigitsWindow(_XamlWindow):
            def digits_only(self, sender, args):
                args.Handled = re.match(r"[^0-9]+", args.Text)

        window = DigitsWindow(
            '<TextBox x:Name="digits_tb" PreviewTextInput="digits_only"/>'
        )
        observed = []
        with _Shown(window):
            for text in ("a", "5"):
                composition = framework.Input.TextComposition(
                    framework.Input.InputManager.Current, window.digits_tb, text
                )
                args = framework.Input.TextCompositionEventArgs(
                    framework.Input.Keyboard.PrimaryDevice, composition
                )
                args.RoutedEvent = (
                    framework.Input.TextCompositionManager.PreviewTextInputEvent
                )
                window.digits_tb.RaiseEvent(args)
                observed.append((text, args.Handled))
        self.assertEqual([("a", True), ("5", False)], observed)

    def test_root_closing_cancels_once(self):
        """A root Closing handler that cancels keeps the window open until it allows.

        Used by Keynotes and Manage Packages.
        """

        class ClosingWindow(_XamlWindow):
            def closing(self, sender, args):
                self.seen.append("closing")
                args.Cancel = len(self.seen) == 1

        window = ClosingWindow("<Grid/>", 'Closing="closing"')
        window.Show()
        native = _native(window)
        window.Close()
        observed = [native.IsVisible]
        window.Close()
        observed.append(native.IsVisible)
        self.assertEqual([True, False], observed)
        self.assertEqual(["closing", "closing"], window.seen)

    def test_handler_exception_policy(self):
        """A failing XAML handler surfaces as IronPython surfaces it.

        IronPython raises the error out of RaiseEvent to the code that raised
        the event and leaves the window open. Every XAML-based tool depends on
        where its handler errors appear.
        """

        class FailingWindow(_XamlWindow):
            def __init__(self):
                _XamlWindow.__init__(self, '<Button x:Name="boom_b" Click="boom"/>')

            def boom(self, sender, args):
                raise ValueError("handler failed")

        observed = {}

        def action(dialog):
            try:
                _click(dialog.boom_b)
                observed["click"] = None
            except ValueError:
                observed["click"] = "ValueError"
            _pump()
            observed["open_after_click"] = _native(dialog).IsVisible

        try:
            _modal(FailingWindow, lambda: FailingWindow().ShowDialog(), action)
            observed["show_dialog"] = None
        except ValueError:
            observed["show_dialog"] = "ValueError"
        self.assertEqual(
            {"click": "ValueError", "open_after_click": True, "show_dialog": None},
            observed,
        )

    def test_programmatic_handler_on_code_built_control(self):
        """``+=`` and ``-=`` on a control built in code attach and detach a handler.

        Used by CommandSwitchWindow and settings_window dynamic controls.
        """
        window = _XamlWindow('<StackPanel x:Name="panel"/>')
        button = framework.Controls.Button()
        window.panel.Children.Add(button)
        seen = []

        def clicked(sender, args):
            seen.append(_same(sender, button))

        try:
            button.Click += clicked
            _click(button)
            button.Click -= clicked
            _click(button)
        finally:
            window.Close()
        self.assertEqual([True], seen)

    def test_root_and_child_routing_order(self):
        """Bubbling MouseDown and KeyDown reach the child before the root window.

        Used by About (root KeyDown/MouseDown) and Test Modeless (Sensors).
        """

        class RoutingWindow(_XamlWindow):
            def root_down(self, sender, args):
                self.seen.append("root")

            def child_down(self, sender, args):
                self.seen.append("child")

            def root_key(self, sender, args):
                self.seen.append("root_key")

            def child_key(self, sender, args):
                self.seen.append("child_key")

        window = RoutingWindow(
            '<Border x:Name="child" Background="Red" MouseDown="child_down">'
            '<TextBox x:Name="child_tb" KeyDown="child_key"/></Border>',
            'MouseDown="root_down" KeyDown="root_key"',
        )
        with _Shown(window):
            _mouse(
                window.child,
                framework.Input.Mouse.MouseDownEvent,
                framework.Input.MouseButton.Left,
            )
            _key(
                window.child_tb,
                framework.Input.Keyboard.KeyDownEvent,
                framework.Input.Key.F5,
            )
        self.assertEqual(["child", "root", "child_key", "root_key"], window.seen)

    def test_named_preview_left_button_filters_right(self):
        """PreviewMouseLeftButtonDown/Up on a named element ignore the right button.

        Used by the Extensions window and Keynotes.
        """

        class PadWindow(_XamlWindow):
            def left_down(self, sender, args):
                self.seen.append("down")

            def left_up(self, sender, args):
                self.seen.append("up")

        window = PadWindow(
            '<Border x:Name="pad" Background="Red" PreviewMouseLeftButtonDown="left_down" '
            'PreviewMouseLeftButtonUp="left_up"/>'
        )
        mouse = framework.Input.Mouse
        buttons = framework.Input.MouseButton
        with _Shown(window):
            _mouse(window.pad, mouse.PreviewMouseDownEvent, buttons.Right)
            _mouse(window.pad, mouse.PreviewMouseDownEvent, buttons.Left)
            _mouse(window.pad, mouse.PreviewMouseUpEvent, buttons.Right)
            _mouse(window.pad, mouse.PreviewMouseUpEvent, buttons.Left)
        self.assertEqual(["down", "up"], window.seen)

    def test_unnamed_hyperlink_handlers(self):
        """Unnamed Hyperlinks reach handle_url_click and a window Click handler.

        Used by the pyRevit Settings and Extensions windows and SamplePanel.
        """

        class LinkWindow(_XamlWindow):
            def link_clicked(self, sender, args):
                self.seen.append("click")

        opened = []
        base = sys.modules["pyrevit.forms.base"]
        browser = base.webbrowser
        base.webbrowser = _Plain(open_new_tab=opened.append)
        window = LinkWindow(
            '<TextBlock x:Name="links_tb"><Hyperlink NavigateUri="https://pyrevitlabs.io/" '
            'RequestNavigate="handle_url_click">site</Hyperlink>'
            '<Hyperlink Click="link_clicked">click</Hyperlink></TextBlock>'
        )
        try:
            with _Shown(window):
                links = [
                    inline
                    for inline in window.links_tb.Inlines
                    if isinstance(inline, framework.Documents.Hyperlink)
                ]
                navigate = framework.Windows.Navigation.RequestNavigateEventArgs(
                    links[0].NavigateUri, ""
                )
                navigate.RoutedEvent = (
                    framework.Documents.Hyperlink.RequestNavigateEvent
                )
                links[0].RaiseEvent(navigate)
                links[1].RaiseEvent(
                    framework.Windows.RoutedEventArgs(
                        framework.Documents.Hyperlink.ClickEvent
                    )
                )
        finally:
            base.webbrowser = browser
        self.assertEqual(["https://pyrevitlabs.io/"], opened)
        self.assertEqual(["click"], window.seen)

    def test_named_grid_columns(self):
        """x:Name on DataGridTextColumn and GridViewColumn becomes an attribute.

        Used by Print Sheets (pfilename) and the clipboard pane (categoryColumn).
        """
        window = _XamlWindow(
            '<StackPanel><DataGrid x:Name="grid_dg"><DataGrid.Columns>'
            '<DataGridTextColumn x:Name="name_col" Header="Name"/></DataGrid.Columns>'
            '</DataGrid><ListView x:Name="list_lv"><ListView.View><GridView>'
            '<GridViewColumn x:Name="group_col" Header="Group"/></GridView>'
            "</ListView.View></ListView></StackPanel>"
        )
        try:
            self.assertEqual("Name", str(window.name_col.Header))
            self.assertEqual("Group", str(window.group_col.Header))
        finally:
            window.Close()

    def test_initial_selection_and_check_replay_order(self):
        """Load-time SelectionChanged and Checked fire exactly where LoadComponent fires them.

        Reference check for the CPython replay rule. Used by Edit Naming
        Formats (SelectionChanged with SelectedIndex="0").
        """

        class ReplayWindow(_XamlWindow):
            def changed(self, sender, args):
                self.seen.append((str(sender.Name), sender.SelectedIndex))

            def checked(self, sender, args):
                self.seen.append((str(sender.Name), "checked"))

        items = '<ComboBoxItem Content="a"/><ComboBoxItem Content="b"/>'
        window = ReplayWindow(
            "<StackPanel>"
            '<ComboBox x:Name="event_first" SelectionChanged="changed" SelectedIndex="1">'
            + items
            + "</ComboBox>"
            '<ComboBox x:Name="state_first" SelectedIndex="1" SelectionChanged="changed">'
            + items
            + "</ComboBox>"
            '<ListBox x:Name="item_selected" SelectionChanged="changed">'
            '<ListBoxItem Content="x"/><ListBoxItem Content="y" IsSelected="True"/></ListBox>'
            '<CheckBox x:Name="check_event_first" Checked="checked" IsChecked="True"/>'
            '<CheckBox x:Name="check_state_first" IsChecked="True" Checked="checked"/>'
            "</StackPanel>"
        )
        window.Close()
        self.assertEqual(
            [
                ("event_first", 1),
                ("state_first", 1),
                ("item_selected", 1),
                ("check_event_first", "checked"),
            ],
            window.seen,
        )

    def test_initial_selection_waits_for_items(self):
        """A selection set before its items exist fires once the items arrive.

        Child items and property elements apply after every attribute, an
        ``ItemsSource`` attribute applies at its own position, and a binding
        to a static source resolves immediately. Reference check for the
        CPython replay rule.
        """

        class SelectorWindow(_XamlWindow):
            def changed(self, sender, args):
                self.seen.append(str(sender.Name))

        def selector(tag, name, attributes, body=""):
            return '<{0} x:Name="{1}" {2}>{3}</{0}>'.format(
                tag, name, " ".join(attributes), body
            )

        items = '<ComboBoxItem Content="a"/><ComboBoxItem Content="b"/>'
        index = 'SelectedIndex="1"'
        source = 'ItemsSource="{StaticResource letters}"'
        bound = 'ItemsSource="{Binding Source={StaticResource letters}}"'
        event = 'SelectionChanged="changed"'
        window = SelectorWindow(
            "<StackPanel><StackPanel.Resources>"
            '<x:Array x:Key="letters" Type="{x:Type sys:String}">'
            "<sys:String>a</sys:String><sys:String>b</sys:String></x:Array>"
            "</StackPanel.Resources>"
            + selector(
                "ListBox",
                "list_children",
                [index, event],
                '<ListBoxItem Content="x"/><ListBoxItem Content="y"/>',
            )
            + selector(
                "TabControl",
                "tab_children",
                [index, event],
                '<TabItem Header="x"/><TabItem Header="y"/>',
            )
            + selector(
                "TabControl",
                "tab_unselected",
                [event],
                '<TabItem Header="x"/><TabItem Header="y"/>',
            )
            + selector(
                "ComboBox",
                "items_element",
                [index, event],
                "<ComboBox.Items>" + items + "</ComboBox.Items>",
            )
            + selector(
                "ComboBox",
                "value_children",
                ['SelectedValue="b"', 'SelectedValuePath="Content"', event],
                items,
            )
            + selector(
                "ComboBox",
                "index_element",
                [event],
                items + "<ComboBox.SelectedIndex>1</ComboBox.SelectedIndex>",
            )
            + selector("ComboBox", "source_state_event", [source, index, event])
            + selector("ComboBox", "state_source_event", [index, source, event])
            + selector("ComboBox", "state_event_source", [index, event, source])
            + selector("ComboBox", "state_event_binding", [index, event, bound])
            + selector("ComboBox", "state_binding_event", [index, bound, event])
            + selector(
                "ComboBox", "item_source_event", ['SelectedItem="b"', source, event]
            )
            + "</StackPanel>",
            'xmlns:sys="clr-namespace:System;assembly=mscorlib"',
        )
        window.Close()
        self.assertEqual(
            [
                "list_children",
                "tab_children",
                "items_element",
                "value_children",
                "index_element",
                "state_event_source",
                "state_event_binding",
            ],
            window.seen,
        )


def _define_converter(namespace):
    """Define a fresh Python IValueConverter, as a re-run command script does."""
    body = {
        "Convert": lambda self, value, target, parameter, culture: str(value).upper(),
        "ConvertBack": lambda self, value, target, parameter, culture: str(
            value
        ).lower(),
    }
    if namespace:
        body["__namespace__"] = namespace
    return type("UpperConverter", (framework.Windows.Data.IValueConverter,), body)


def _converted(converter_type):
    text = framework.Controls.TextBlock()
    text.DataContext = "abc"
    binding = framework.Windows.Data.Binding()
    binding.Converter = converter_type()
    text.SetBinding(framework.Controls.TextBlock.TextProperty, binding)
    return text.Text


class InteropParityTests(unittest.TestCase):
    """Python objects crossing into CLR APIs: converters, owners, Tag, reload."""

    def test_value_converter_with_namespace_redefined(self):
        """A Python IValueConverter with __namespace__ works when defined twice.

        No shipped tool defines one yet; user tools re-run their script on each
        click, defining the converter class again.
        """
        observed = [
            _converted(_define_converter("PyRevitFormsParity")) for _ in range(2)
        ]
        self.assertEqual(["ABC", "ABC"], observed)

    def test_value_converter_without_namespace(self):
        """A Python IValueConverter without __namespace__ works when defined twice.

        IronPython needs no namespace; CPython needs one to derive a CLR type.
        """
        observed = [_converted(_define_converter(None)) for _ in range(2)]
        self.assertEqual(["ABC", "ABC"], observed)

    def test_owner_is_a_controller(self):
        """``child.Owner = parent`` accepts another pyRevit window.

        Used by Keynotes (EditRecordWindow, PastePreviewWindow).
        """
        parent = _XamlWindow("<Grid/>")
        child = _XamlWindow("<Grid/>")
        parent.Show()
        try:
            child.Owner = parent
            self.assertTrue(_same(_native(child).Owner, _native(parent)))
            self.assertEqual(1, _native(parent).OwnedWindows.Count)
        finally:
            child.Close()
            parent.Close()

    def test_window_typed_parameter_accepts_controller(self):
        """A pyRevit window is accepted where .NET expects a ``Window`` argument.

        Uses ``WindowInteropHelper(Window)`` so no native modal opens. Keynotes
        passes its window to ``Windows.MessageBox.Show(self, ...)``, which
        resolves the same Window-typed overload.
        """
        parent = _XamlWindow("<Grid/>")
        parent.Show()
        try:
            helper = framework.Interop.WindowInteropHelper(parent)
            native_helper = framework.Interop.WindowInteropHelper(_native(parent))
            observed = [
                helper.Handle != framework.System.IntPtr.Zero,
                helper.Handle == native_helper.Handle,
            ]
        finally:
            parent.Close()
        self.assertEqual([True, True], observed)

    def test_reserved_attribute_names(self):
        """Subclass attributes named _events, _closed and _window keep Show/Close working.

        Used by Keynotes (self._closed) and Rocket Mode Scope Test (self._events).
        """

        class ReservedWindow(forms.WPFWindow):
            def __init__(self):
                forms.WPFWindow.__init__(self, _markup("<Grid/>"), literal_string=True)
                self.root = _backend.unwrap(self)
                self._events = ["user"]
                self._closed = "user"
                self._window = "user"

        window = ReservedWindow()
        observed = []
        try:
            window.Show()
            observed.append(window.root.IsVisible)
            window.Close()
            observed.append(window.root.IsVisible)
        finally:
            window.root.Close()
        observed.extend([window._events, window._closed, window._window])
        self.assertEqual([True, False, ["user"], "user", "user"], observed)

    def test_attributes_set_before_load_xaml(self):
        """``script.load_ui`` windows may set attributes before their XAML loads.

        XAML attributes win for CLR properties, as LoadComponent applies them
        last. Used by Test XAML, Test Modeless (Sensors) and Test Persistent
        Engine.
        """

        class LoadUiWindow(forms.WPFWindow):
            def __init__(self):
                self.Title = "pre"
                self.counter = 1
                self.load_xaml(_markup("<Grid/>", 'Title="xaml"'), literal_string=True)

        window = LoadUiWindow()
        try:
            observed = [window.Title, _native(window).Title, window.counter]
        finally:
            window.Close()
        self.assertEqual(["xaml", "xaml", 1], observed)

    def test_tag_and_data_object_round_trip(self):
        """Python values stored in Tag and DataObject come back as the same objects.

        Used by Section Box Navigator (dict Tag), the custom properties pane
        (tuple Tag), FamSlide (row Tag), Keynotes and Print Sheets (DataObject).
        """
        point = namedtuple("Point", "x y")
        values = {
            "dict": {"a": 1},
            "tuple": (1, "b"),
            "namedtuple": point(1, 2),
            "row": _Row("r"),
        }
        border = framework.Controls.Border()
        observed = {}
        for key, value in values.items():
            border.Tag = value
            data = framework.Windows.DataObject()
            data.SetData("pyrevit", value)
            observed[key] = (border.Tag is value, data.GetData("pyrevit") is value)
        self.assertEqual(
            {
                "dict": (True, True),
                "tuple": (True, True),
                "namedtuple": (True, True),
                "row": (True, True),
            },
            observed,
        )

    def test_load_xaml_twice(self):
        """A second load_xaml exposes the new names and wires the new handlers.

        Used by dockable panels and WPFWindow.__init__ when a subclass reloads.
        """

        class ReloadWindow(_XamlWindow):
            def on_first(self, sender, args):
                self.seen.append("first")

            def on_second(self, sender, args):
                self.seen.append("second")

        window = ReloadWindow('<Button x:Name="first" Click="on_first"/>')
        try:
            old = window.first
            window.load_xaml(
                _markup('<Button x:Name="second" Click="on_second"/>'),
                literal_string=True,
            )
            _click(old)
            _click(window.second)
            observed = {
                "seen": list(window.seen),
                "content_is_second": _same(_native(window).Content, window.second),
            }
        finally:
            window.Close()
        self.assertEqual(
            {"seen": ["first", "second"], "content_is_second": True}, observed
        )


def _switch_buttons(dialog):
    toggles = []
    options = []
    for child in dialog.button_list.Children:
        if isinstance(child, framework.Controls.Primitives.ToggleButton):
            toggles.append(child)
        elif isinstance(child, framework.Controls.Button):
            options.append(child)
    return toggles, options


def _write_png(path):
    bitmap = framework.Imaging.WriteableBitmap(
        2, 2, 96, 96, framework.Media.PixelFormats.Bgra32, None
    )
    encoder = framework.Imaging.PngBitmapEncoder()
    encoder.Frames.Add(framework.Imaging.BitmapFrame.Create(bitmap))
    stream = framework.System.IO.File.Create(path)
    try:
        encoder.Save(stream)
    finally:
        stream.Close()


class BuiltinFormsParityTests(unittest.TestCase):
    """Shipped dialogs driven through options that the modal tests do not cover."""

    def test_command_switch_list_switches(self):
        """Switches given as a list start unchecked and return their toggled state.

        Used by Overkill and Test pyRevit Button.
        """
        initial = []

        def accept(dialog):
            toggles, options = _switch_buttons(dialog)
            initial.extend(toggle.IsChecked for toggle in toggles)
            [toggle for toggle in toggles if str(toggle.Content) == "s2"][
                0
            ].IsChecked = True
            _click(options[0])

        value = _modal(
            forms.CommandSwitchWindow,
            lambda: forms.CommandSwitchWindow.show(["A", "B"], switches=["s1", "s2"]),
            accept,
        )
        self.assertEqual([False, False], initial)
        self.assertEqual(("A", {"s1": False, "s2": True}), value)

    def test_command_switch_dict_config_access_key_and_enter(self):
        """Dict switches, a background config, access keys and Enter acceptance.

        Used by Override VG (background config), Test pyRevit Button
        (recognize_access_key) and Select Element Types.
        """
        observed = {}

        def accept(dialog):
            toggles, options = _switch_buttons(dialog)
            observed["switches"] = dict(
                (str(toggle.Content), toggle.IsChecked) for toggle in toggles
            )
            observed["background"] = str(options[0].Background)
            observed["access_key"] = dialog.Resources["pyRevitRecognizesAccessKey"]
            dialog.search_tb.Text = "alp"
            _key(
                _native(dialog),
                framework.Input.Keyboard.PreviewKeyDownEvent,
                framework.Input.Key.Enter,
            )

        value = _modal(
            forms.CommandSwitchWindow,
            lambda: forms.CommandSwitchWindow.show(
                ["Alpha", "Beta"],
                switches={"on": True, "off": False},
                config={"Alpha": {"background": "0xFF55FF"}},
                recognize_access_key=True,
            ),
            accept,
        )
        self.assertEqual(
            {
                "switches": {"on": True, "off": False},
                "background": "#FFFF55FF",
                "access_key": True,
            },
            observed,
        )
        self.assertEqual(("Alpha", {"on": True, "off": False}), value)

    def test_command_switch_cancel(self):
        """Cancelling returns None, or (None, switches) when switches are shown.

        Used by every CommandSwitchWindow caller that checks for cancellation.
        """
        plain = _modal(
            forms.CommandSwitchWindow,
            lambda: forms.CommandSwitchWindow.show(["A"]),
            lambda dialog: dialog.Close(),
        )
        switched = _modal(
            forms.CommandSwitchWindow,
            lambda: forms.CommandSwitchWindow.show(["A"], switches=["s"]),
            lambda dialog: dialog.Close(),
        )
        self.assertIsNone(plain)
        self.assertEqual((None, {"s": False}), switched)

    def test_select_from_list_info_panel_and_regex_toggle(self):
        """The info panel shows the selected item's description; regex swaps the icon.

        Used by Preflight Checks (info_panel=True).
        """
        items = [_Row("alpha", description="first"), _Row("beta", description="second")]
        observed = {}

        def accept(dialog):
            dialog.list_lb.SelectedIndex = 1
            observed["info"] = dialog.infoData.Text
            observed["panel"] = str(dialog.infoPanel.Visibility)
            dialog.regexToggle_b.IsChecked = True
            _click(dialog.regexToggle_b)
            observed["regex_icon"] = _same(
                dialog.regexToggle_b.Content, dialog.Resources["regexIcon"]
            )
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show(items, info_panel=True),
            accept,
        )
        self.assertEqual(
            {"info": "second", "panel": "Visible", "regex_icon": True}, observed
        )
        self.assertIs(items[1], value)

    def test_select_from_list_toggle_all(self):
        """Toggle All flips every check box and the result follows the new states.

        Used by every multiselect SelectFromList caller.
        """
        items = [
            forms.TemplateListItem("a"),
            forms.TemplateListItem("b", checked=True),
            forms.TemplateListItem("c"),
        ]
        states = []

        def accept(dialog):
            _click(dialog.toggleall_b)
            _native(dialog).UpdateLayout()
            states.extend(
                check.IsChecked
                for check in _of_type(dialog.list_lb, framework.Controls.CheckBox)
            )
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show(items, multiselect=True),
            accept,
        )
        self.assertEqual([True, False, True], states)
        self.assertEqual(["a", "c"], value)

    def test_select_from_list_external_item_template(self):
        """An item_template from another window's Resources triggers on a wrapped attribute.

        Used by Manage Tags, Manage Packages and XLS Export (item_template).
        """
        resources = _XamlWindow(
            '<Window.Resources><ControlTemplate x:Key="flag_template">'
            '<TextBlock Text="{Binding name}"><TextBlock.Style><Style TargetType="TextBlock">'
            '<Setter Property="Tag" Value="plain"/><Style.Triggers>'
            '<DataTrigger Binding="{Binding flag}" Value="yes">'
            '<Setter Property="Tag" Value="flagged"/></DataTrigger></Style.Triggers>'
            "</Style></TextBlock.Style></TextBlock></ControlTemplate></Window.Resources>"
            "<Grid/>"
        )
        template = resources.Resources["flag_template"]
        items = [_Row("a", flag="yes"), _Row("b", flag="no")]
        tags = {}

        def accept(dialog):
            _native(dialog).UpdateLayout()
            for text in _of_type(dialog.list_lb, framework.Controls.TextBlock):
                if text.Text in ("a", "b"):
                    tags[text.Text] = str(text.Tag)
            _select_first(dialog)

        try:
            value = _modal(
                forms.SelectFromList,
                lambda: forms.SelectFromList.show(items, item_template=template),
                accept,
            )
        finally:
            resources.Close()
        self.assertEqual({"a": "flagged", "b": "plain"}, tags)
        self.assertIs(items[0], value)

    def test_select_from_list_group_selector_and_default_group(self):
        """group_selector_title labels the selector and default_group picks the list.

        Used by Test IronPython/CPython Forms Manual (group_selector_title).
        """
        observed = {}

        def accept(dialog):
            observed["title"] = dialog.ctx_groups_title_tb.Text
            observed["group"] = str(dialog.ctx_groups_selector_cb.SelectedItem)
            observed["count"] = dialog.list_lb.Items.Count
            dialog.list_lb.SelectedIndex = 1
            _click(dialog.select_b)

        value = _modal(
            forms.SelectFromList,
            lambda: forms.SelectFromList.show(
                {"A": ["a1"], "B": ["b1", "b2"]},
                group_selector_title="Sets",
                default_group="B",
            ),
            accept,
        )
        self.assertEqual({"title": "Sets", "group": "B", "count": 2}, observed)
        self.assertEqual("b2", value)

    def test_progress_bar_indeterminate_and_step(self):
        """Indeterminate bars report it; a step only repaints on its multiples.

        Used by Test Progressbar (step=10).
        """
        with forms.ProgressBar(indeterminate=True) as progress:
            indeterminate = [progress.pbar.IsIndeterminate, progress.indeterminate]
        values = []
        with forms.ProgressBar(step=5) as progress:
            progress.update_progress(3, 10)
            values.append(progress.pbar.Value)
            progress.update_progress(5, 10)
            values.append(progress.pbar.Value)
        self.assertEqual([True, True], indeterminate)
        self.assertEqual([0.0, 5.0], values)

    def test_template_prompt_bar(self):
        """A bare TemplatePromptBar shows with the requested height and closes on exit.

        Base of WarningBar and ProgressBar.
        """
        with forms.TemplatePromptBar(height=40) as bar:
            observed = [_native(bar).IsVisible, bar.Height, bar.Width > 0]
        observed.append(_native(bar).IsVisible)
        self.assertEqual([True, 40.0, True, False], observed)

    def test_select_image_returns_the_given_path(self):
        """select_image returns the very path object that was passed in.

        Used by Test IronPython/CPython Forms Manual.
        """
        folder = tempfile.mkdtemp()
        paths = [os.path.join(folder, "a.png"), os.path.join(folder, "b.png")]
        for path in paths:
            _write_png(path)
        try:
            value = _modal(
                forms.SelectFromList, lambda: forms.select_image(paths), _select_first
            )
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        self.assertIs(paths[0], value)


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
        target_index = []

        def select_fixture_doc(dialog):
            options = dialog._get_active_ctx()
            target_index.extend(
                index
                for index, option in enumerate(options)
                if option.item.Equals(self.doc)
            )
            dialog.list_lb.SelectedIndex = target_index[0]
            _click(dialog.select_b)

        selected = self._select(
            lambda: forms.select_open_docs(multiple=False, check_more_than_one=False),
            select_fixture_doc,
        )
        self.assertEqual(1, len(target_index))
        self.assertTrue(selected.Equals(self.doc))

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
