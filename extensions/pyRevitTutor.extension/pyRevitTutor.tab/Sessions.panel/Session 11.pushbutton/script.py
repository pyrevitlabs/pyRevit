"""Reactive data binding with pyrevit.forms.

The window's DataContext is a forms.Reactive view model. The TextBox writes
into ``name`` through a two-way binding, the TextBlock re-reads it whenever
the view model raises PropertyChanged, and the button changes the view model
from code to show the UI following along.
"""

from pyrevit import forms


class GreetingViewModel(forms.Reactive):
    """View model whose ``name`` changes are pushed to bound controls."""

    def __init__(self):
        self._name = "World"

    @forms.reactive
    def name(self):
        """Raises PropertyChanged when set to a different value."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value


class ReactiveWindow(forms.WPFWindow):
    """Window bound to a GreetingViewModel through its DataContext."""

    def __init__(self):
        forms.WPFWindow.__init__(self, "reactive_ui.xaml")
        self.view_model = GreetingViewModel()
        self.DataContext = self.view_model

    def reset_name(self, sender, args):
        """Update the view model only; bindings refresh the TextBox and TextBlock."""
        self.view_model.name = "World"


ReactiveWindow().show(modal=True)
