"""Exercise ExternalEvent callback scope with and without Rocket Mode.

Run Rocket Mode Cache Warmup before this modeless test. Its buttons reproduce
the direct callback pattern reported in issue #3538 against a cached engine.
"""

from pyrevit import DB, UI, forms, script
from Autodesk.Revit.DB import FilteredElementCollector


SCOPE_SENTINEL = "rocket-mode-scope-test"


class DirectEventHandler(UI.IExternalEventHandler):
    """Run a stored callback when Revit services the external event."""

    def __init__(self, owner, label, callback):
        self.owner = owner
        self.label = label
        self.callback = callback

    def Execute(self, uiapp):
        """Invoke the selected callback and retain any scope failure."""
        try:
            self.callback()
        except Exception as error:
            self.owner.record_failure(self.label, error)

    def GetName(self):
        """Return a stable name for Revit's external-event diagnostics."""
        return "pyRevit Rocket Mode Scope Test"


class ScopeTestWindow(forms.WPFWindow):
    """Provide independent probes for script globals and imported symbols."""

    resolve_theme = True

    def __init__(self):
        layout = """
        <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                Title="Rocket Mode Scope Test"
                Width="500" Height="410"
                WindowStartupLocation="CenterScreen"
                ShowInTaskbar="False"
                ResizeMode="CanMinimize">
            <StackPanel Margin="18">
                <TextBlock TextWrapping="Wrap" Margin="0,0,0,10"
                    Text="Run Rocket Mode Cache Warmup first. Each Direct button invokes a custom IExternalEventHandler. Results are written to the pyRevit output window." />
                <Button Height="30" Margin="0,3" Content="Direct: imported CLR type" Click="direct_imported_type" />
                <Button Height="30" Margin="0,3" Content="Direct: pyRevit module" Click="direct_module" />
                <Button Height="30" Margin="0,3" Content="Direct: script global" Click="direct_global" />
                <TextBlock Name="result" TextWrapping="Wrap" Margin="0,12,0,0"
                    Text="Waiting for a probe." />
            </StackPanel>
        </Window>
        """
        forms.WPFWindow.__init__(self, layout, literal_string=True)
        self.output = script.get_output()
        self.output.set_title("Rocket Mode Scope Test")
        self._reused_cached_engine = __cachedengine__
        self._events = []
        self.Closed += self._dispose_events
        self._register_event("Direct imported CLR type", self._probe_imported_type)
        self._register_event("Direct pyRevit module", self._probe_module)
        self._register_event("Direct script global", self._probe_global)
        self.output.print_md("# Rocket Mode Scope Test")
        self.output.print_md(
            "Cached engine reused: {}".format(self._reused_cached_engine)
        )
        if not self._reused_cached_engine:
            self.result.Text = "Run Rocket Mode Cache Warmup, then reopen this test."

    def _register_event(self, label, callback):
        handler = DirectEventHandler(self, label, callback)
        self._events.append((label, UI.ExternalEvent.Create(handler)))

    def _raise_event(self, label):
        if not self._reused_cached_engine:
            self.result.Text = "Run Rocket Mode Cache Warmup, then reopen this test."
            return
        for event_label, external_event in self._events:
            if event_label == label:
                response = external_event.Raise()
                self.result.Text = "{} raised: {}".format(label, response)
                return

    def _dispose_events(self, sender, args):
        try:
            for _, external_event in self._events:
                external_event.Dispose()
        finally:
            self._events = []

    def _probe_imported_type(self):
        self.record_success(
            "Direct imported CLR type", FilteredElementCollector.__name__
        )

    def _probe_module(self):
        self.record_success("Direct pyRevit module", DB.__name__)

    def _probe_global(self):
        self.record_success("Direct script global", SCOPE_SENTINEL)

    def record_success(self, label, value):
        """Record a probe result that completed without a scope error."""
        message = "PASS | {} | {}".format(label, value)
        self.result.Text = message
        self.output.print_md("- **{}**".format(message))

    def record_failure(self, label, error):
        """Record a probe result that raised while Revit ran the event."""
        message = "FAIL | {} | {}: {}".format(label, type(error).__name__, error)
        self.result.Text = message
        self.output.print_md("- **{}**".format(message))

    def direct_imported_type(self, sender, args):
        """Run the direct imported-type probe."""
        self._raise_event("Direct imported CLR type")

    def direct_module(self, sender, args):
        """Run the direct module probe."""
        self._raise_event("Direct pyRevit module")

    def direct_global(self, sender, args):
        """Run the direct global probe."""
        self._raise_event("Direct script global")


if __name__ == "__main__":
    window = ScopeTestWindow()
    window.show(modal=False)
