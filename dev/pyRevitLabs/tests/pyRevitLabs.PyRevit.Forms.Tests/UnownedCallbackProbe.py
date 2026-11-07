"""Queue input that reaches CPython form callbacks with no Python code below them.

FormsBackendTests runs this script, pumps the dispatcher from C# once the
script has returned, then calls ``check_unowned_callbacks``. That is how
Revit delivers input to a modeless window or a dockable page after its
command has finished: the callback error must be logged, never left to the
WPF dispatcher.
"""

unowned_errors = []
logger.error = lambda *args: unowned_errors.append(args)


class UnownedWindow(forms.WPFWindow):
    """Modeless window whose Click handler fails."""

    def __init__(self):
        forms.WPFWindow.__init__(
            self,
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" ShowActivated="False">'
            '<Button x:Name="fail_b" Click="fail"/></Window>',
            literal_string=True,
        )

    def fail(self, sender, args):
        """Raise from a callback that no Python code is waiting on."""
        raise ValueError("unowned callback failure")


unowned = UnownedWindow()
unowned.Show()
native_raise = System.Delegate.CreateDelegate(
    System.Action[Windows.RoutedEventArgs],
    unowned.fail_b,
    clr.GetClrType(Windows.UIElement).GetMethod("RaiseEvent"),
)
for attempt in range(2):
    Threading.Dispatcher.CurrentDispatcher.BeginInvoke(
        native_raise, Windows.RoutedEventArgs(Controls.Button.ClickEvent)
    )


def check_unowned_callbacks():
    """Each failure was logged once and the window kept working."""
    try:
        assert len(unowned_errors) == 2, unowned_errors
        assert all("unowned callback failure" in args[1] for args in unowned_errors)
        assert unowned.IsVisible
        assert not unowned._pyrevit_backend.events.is_released
    finally:
        unowned.Close()
    assert unowned._pyrevit_backend.events.is_released
