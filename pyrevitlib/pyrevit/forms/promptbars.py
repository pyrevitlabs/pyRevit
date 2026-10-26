"""Command-scoped warning and progress overlays owned by the Revit UI thread."""

from .base import WPFWindow
from .base import XAML_FILES_DIR
from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit import revit
from pyrevit.framework import System
from pyrevit.framework import Threading
import os.path as op
import string
from . import _backend


class TemplatePromptBar(WPFWindow):
    """Template context-manager class for creating prompt bars.

    Prompt bars are show at the top of the active Revit window and are
    designed for better prompt visibility.

    Args:
        height (int): window height
        **kwargs (Any): other arguments to be passed to :func:`_setup`
    """

    xaml_source = "TemplatePromptBar.xaml"

    def __init__(self, height=32, **kwargs):
        """Initialize user prompt window."""
        WPFWindow.__init__(self, op.join(XAML_FILES_DIR, self.xaml_source))

        self.user_height = height
        self.update_window()
        self._setup(**kwargs)

    def update_window(self):
        """Update the prompt bar to match Revit window."""
        screen_area = HOST_APP.proc_screen_workarea
        scale_factor = 1.0 / HOST_APP.proc_screen_scalefactor
        top = left = width = height = 0

        window_rect = revit.ui.get_window_rectangle()

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

    def _prepare(self):
        pass

    def _cleanup(self):
        pass

    def __enter__(self):
        self._prepare()
        _backend.show_prompt(self)
        return self

    def __exit__(self, exception, exception_value, traceback):
        self._cleanup()
        self.Close()


class WarningBar(TemplatePromptBar):
    """Show warning bar at the top of Revit window.

    Keyword Args:
        title (string): warning bar text
        background (SolidColorBrush): background brush
        foreground (SolidColorBrush): text brush

    Examples:
        ```python
        with WarningBar(title='my warning'):
           # do stuff
        ```
    """

    xaml_source = "WarningBar.xaml"

    def _setup(self, **kwargs):
        self.message_tb.Text = kwargs.get("title", "")

        bg = kwargs.get("background", None)
        if bg:
            self.Resources["pyRevitAccentBrush"] = bg

        fg = kwargs.get("foreground", None)
        if fg:
            self.Resources[System.Windows.SystemColors.WindowBrushKey] = fg


class ProgressBar(TemplatePromptBar):
    """Show progress bar at the top of Revit window.

    Keyword Args:
        title (string): progress bar text, defaults to 0/100 progress format
        indeterminate (bool): create indeterminate progress bar
        cancellable (bool): add cancel button to progress bar
        step (int): update progress intervals

    Examples:
        ```python
        from pyrevit import forms
        count = 1
        with forms.ProgressBar(title='my command progress message') as pb:
           # do stuff
           pb.update_progress(count, 100)
           count += 1
        ```

        Progress bar title could also be customized to show the current and
        total progress values. In example below, the progress bar message
        will be in format "0 of 100"

        ```python
        with forms.ProgressBar(title='{value} of {max_value}') as pb:
        ```

        By default progress bar updates the progress every time the
        .update_progress method is called. For operations with a large number
        of max steps, the gui update process time will have a significate
        effect on the overall execution time of the command. In these cases,
        set the value of step argument to something larger than 1. In example
        below, the progress bar updates once per every 10 units of progress.

        ```python
        with forms.ProgressBar(title='message', steps=10):
        ```

        Progress bar could also be set to indeterminate for operations of
        unknown length. In this case, the progress bar will show an infinitely
        running ribbon:

        ```python
        with forms.ProgressBar(title='message', indeterminate=True):
        ```

        if cancellable is set on the object, a cancel button will show on the
        progress bar and .cancelled attribute will be set on the ProgressBar
        instance if users clicks on cancel button:

        ```python
        with forms.ProgressBar(title='message',
                               cancellable=True) as pb:
           # do stuff
           if pb.cancelled:
               # wrap up and cancel operation
        ```
    """

    xaml_source = "ProgressBar.xaml"

    def _setup(self, **kwargs):
        self.max_value = 1
        self.new_value = 0
        self.step = kwargs.get("step", 0)

        self.cancelled = False
        has_cancel = kwargs.get("cancellable", False)
        if has_cancel:
            self.show_element(self.cancel_b)

        self.pbar.IsIndeterminate = kwargs.get("indeterminate", False)
        self._title = kwargs.get("title", "{value}/{max_value}")
        self._hostwnd = None
        self._host_task_pbar = None

        self._update_pbar()

    def _prepare(self):
        self._hostwnd = revit.ui.get_mainwindow()
        if self._hostwnd:
            self._host_task_pbar = System.Windows.Shell.TaskbarItemInfo()
            self._hostwnd.TaskbarItemInfo = self._host_task_pbar

    def _cleanup(self):
        if self._hostwnd:
            self._hostwnd.TaskbarItemInfo = None

    def _update_task_pbar(self):
        if self._host_task_pbar is not None:
            if self.indeterminate:
                self._host_task_pbar.ProgressState = (
                    System.Windows.Shell.TaskbarItemProgressState.Indeterminate
                )
            else:
                self._host_task_pbar.ProgressState = (
                    System.Windows.Shell.TaskbarItemProgressState.Normal
                )
                self._host_task_pbar.ProgressValue = self.new_value / float(
                    self.max_value
                )

    def _update_pbar(self):
        self.update_window()
        self.pbar.Maximum = self.max_value
        self.pbar.Value = self.new_value

        # updating title
        title_text = string.Formatter().vformat(
            self._title,
            (),
            coreutils.SafeDict({"value": self.new_value, "max_value": self.max_value}),
        )

        self.pbar_text.Text = title_text

    def _donothing(self):
        pass

    def _dispatch_updater(self):
        # ask WPF dispatcher for gui update
        self.pbar.Dispatcher.Invoke(
            System.Action(self._update_pbar), Threading.DispatcherPriority.Background
        )
        # ask WPF dispatcher for gui update
        self.pbar.Dispatcher.Invoke(
            System.Action(self._update_task_pbar),
            Threading.DispatcherPriority.Background,
        )
        # give it a little free time to update ui
        self.pbar.Dispatcher.Invoke(
            System.Action(self._donothing), Threading.DispatcherPriority.Background
        )

    @property
    def title(self):
        """Progress bar title."""
        return self._title

    @title.setter
    def title(self, value):
        if isinstance(value, str):
            self._title = value  # pylint: disable=W0201

    @property
    def indeterminate(self):
        """Progress bar indeterminate state."""
        return self.pbar.IsIndeterminate

    @indeterminate.setter
    def indeterminate(self, value):
        self.pbar.IsIndeterminate = value

    def clicked_cancel(self, sender, args):  # pylint: disable=W0613
        """Handler for cancel button clicked event."""
        self.cancel_b.Content = "Cancelling..."
        self.cancelled = True  # pylint: disable=W0201

    def reset(self):
        """Reset progress value to 0."""
        self.update_progress(0, 1)

    def update_progress(self, new_value, max_value=1):
        """Update progress bar state with given min, max values.

        Args:
            new_value (float): current progress value
            max_value (float): total progress value
        """
        self.max_value = max_value  # pylint: disable=W0201
        self.new_value = new_value  # pylint: disable=W0201
        if self.new_value == 0:
            self._dispatch_updater()
        elif self.step > 0:
            if self.new_value % self.step == 0:
                self._dispatch_updater()
        else:
            self._dispatch_updater()
