"""Exercise the shipped selection templates, search and two-way item state."""

import time


def descendants(root):
    """Walk the visual tree after WPF has instantiated the real templates."""
    yield root
    for index in range(Media.VisualTreeHelper.GetChildrenCount(root)):
        child = Media.VisualTreeHelper.GetChild(root, index)
        for descendant in descendants(child):
            yield descendant


dialog = forms.CommandSwitchWindow(
    ["First", "Second"], "Commands", 400, 300, switches={"Enabled": True}
)
try:
    dialog.search_tb.Text = "second"
    buttons = [
        item
        for item in dialog.button_list.Children
        if isinstance(item, Controls.Button)
    ]
    assert buttons[0].Visibility == Windows.Visibility.Collapsed
    assert buttons[1].Visibility == Windows.Visibility.Visible
    buttons[1].RaiseEvent(Windows.RoutedEventArgs(Controls.Button.ClickEvent))
    assert dialog.response == ("Second", {"Enabled": True})
finally:
    dialog.Close()

dialog = forms.SelectFromList(
    {"Group 2": ["Beta"], "Group 1": ["Alpha", "Other"]},
    "Selection",
    500,
    400,
    multiselect=True,
)
timer = Threading.DispatcherTimer()
timer.Interval = System.TimeSpan.FromMilliseconds(30)
observations = []


def interact(sender, args):
    """Read and click generated checkbox controls, then filter and accept."""
    timer.Stop()
    try:
        _backend.unwrap(dialog).UpdateLayout()
        checks = [
            item
            for item in descendants(_backend.unwrap(dialog))
            if isinstance(item, Controls.CheckBox)
        ]
        assert len(checks) >= 2
        labels = [
            item.Text
            for item in descendants(_backend.unwrap(dialog))
            if isinstance(item, Controls.TextBlock)
        ]
        assert "Alpha" in labels
        checks[0].IsChecked = True
        assert dialog._get_active_ctx()[0].checked
        dialog._get_active_ctx()[1].checked = True
        assert checks[1].IsChecked
        dialog.search_tb.Text = "Alpha"
        assert dialog.list_lb.Items.Count == 1
        dialog.button_select(None, None)
        observations.append(dialog.response)
    finally:
        dialog.Close()


timer.Tick += interact
timer.Start()
try:
    dialog.ShowDialog()
finally:
    timer.Stop()
    timer.Tick -= interact
assert observations == [["Alpha", "Other"]]
assert not theme_changed.handlers

started = time.perf_counter()
dialog = forms.SelectFromList(
    ["Item {}".format(index) for index in range(2000)],
    "Large list",
    500,
    400,
    multiselect=True,
)
try:
    assert dialog.list_lb.Items.Count == 2000
    dialog.search_tb.Text = "Item 1999"
    assert dialog.list_lb.Items.Count > 0
finally:
    dialog.Close()
selection_report = "Selection templates and 2000-item search passed in {:.3f}s".format(
    time.perf_counter() - started
)
