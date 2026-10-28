# coding: utf-8
"""Shared WPF window resources, theming and lifecycle across Python engines."""

import os
import os.path as op
import threading
import webbrowser

from pyrevit import HOST_APP, EXEC_PARAMS, BIN_DIR
from pyrevit import coreutils, framework, revit, versionmgr
from pyrevit.api import AdWindows
from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import System, Threading, Interop, Input
from pyrevit.framework import Uri, UriKind, ResourceDictionary
from pyrevit.userconfig import user_config
from . import _backend
from . import _theme
from . import utils
from ._theme import (  # noqa: F401
    _BRAND_ACCENT,
    _BRAND_DARK,
    _BRAND_DARKER_DARK,
    _PALETTE_DARK,
    _PALETTE_LIGHT,
    _argb,
    _background_property,
    _colorref,
    _contrast_ratio,
    _foreground_property,
    _is_authored_value,
    _relative_luminance,
    _srgb_component,
    _walk_logical_tree,
    is_dark_theme,
)

mlogger = get_logger(__name__)

DEFAULT_CMDSWITCHWND_WIDTH = 600
DEFAULT_SEARCHWND_WIDTH = 600
DEFAULT_SEARCHWND_HEIGHT = 100
DEFAULT_INPUTWINDOW_WIDTH = 500
DEFAULT_INPUTWINDOW_HEIGHT = 600
DEFAULT_RECOGNIZE_ACCESS_KEY = False

WPF_HIDDEN = framework.Windows.Visibility.Hidden
WPF_COLLAPSED = framework.Windows.Visibility.Collapsed
WPF_VISIBLE = framework.Windows.Visibility.Visible


XAML_FILES_DIR = op.dirname(__file__)
THEME_XAML_FILE = op.join(XAML_FILES_DIR, "Theme.xaml")


class WindowToggler(object):
    """Context manager to toggle window visibility."""

    def __init__(self, window):
        self._window = window

    def __enter__(self):
        self._window.hide()

    def __exit__(self, exception, exception_value, traceback):
        self._window.show_dialog()


def set_data_context(control, model):
    """Set a control's ``DataContext`` so both engines can bind to ``model``.

    Forms adapt their own ``DataContext`` automatically. Under CPython a Python
    model assigned straight to a child control's ``DataContext`` reaches WPF as
    a plain object: bindings read it once and TwoWay edits are lost. Use this
    helper for child controls instead.

    Args:
        control (object): A WPF element, or a pyRevit form.
        model (object): A ``forms.Reactive`` model or any bindable value.

    Warning:
        Under CPython a child control does not keep ``model`` alive; hold a
        reference to it, for example on the form, while it is bound. A form
        keeps its own ``DataContext`` model alive.
    """
    _backend.set_data_context(control, model)


def activate_open_window(envvar):
    """Bring a modeless window left open by an earlier run to the front.

    Single-instance guard for modeless tools: the tool stores its window
    under ``envvar`` with ``script.set_envvar`` when it opens it, and calls
    this on every run before creating a new one. A minimized window is
    restored before activation; a hidden one is left hidden.

    Openness is judged by the window's native handle, which WPF releases on
    close, not by ``IsLoaded``, which stays True after ``Close()``. Callers
    therefore need not clear ``envvar`` in their ``Closed`` handler. Under
    CPython the stored controller is unwrapped by attribute rather than by
    class, so a window created before ``pyrevit.forms`` was re-imported
    still counts.

    Args:
        envvar (str): pyRevit environment variable holding the window.

    Returns:
        (bool): True when a window already exists, meaning the caller must
            not open another. It does not promise the window is now in front:
            Windows may refuse the foreground request, and a hidden window
            stays hidden. False otherwise; a stale (closed) reference is
            cleared.

    Examples:
        ```python
        from pyrevit import forms, script

        if not forms.activate_open_window("MYTOOL_WINDOW"):
            window = MyToolWindow("MyTool.xaml")
            script.set_envvar("MYTOOL_WINDOW", window)
            window.show()
        ```
    """
    window = envvars.get_pyrevit_env_var(envvar)
    if window is None:
        return False
    native = getattr(window, "_window", window)
    try:
        is_open = Interop.WindowInteropHelper(native).Handle != System.IntPtr.Zero
    except Exception:
        is_open = False
    if not is_open:
        envvars.set_pyrevit_env_var(envvar, None)
        return False
    if native.IsVisible:
        if native.WindowState == framework.Windows.WindowState.Minimized:
            native.WindowState = framework.Windows.WindowState.Normal
        native.Activate()
    return True


class _WPFMixin(object):
    """Shared behaviour for WPFWindow and WPFPanel.

    Not intended for direct use — inherit via WPFWindow or WPFPanel.

    Attributes:
        _live_refresh_root_colors (bool): whether a live theme-change refresh
            re-applies Background/Foreground directly.

    Important:
        _live_refresh_root_colors stays False for WPFWindow: a HUD-style
        overlay (CommandSwitchWindow, SearchPrompt, ...) declares its own
        literal transparent Background in XAML and must not have it clobbered
        while already open. WPFPanel overrides it to True — dockable panes
        never use that transparent-HUD pattern, and unlike transient dialogs
        they stay open for the whole Revit session, so they need to pick up a
        live theme change.
    """

    _live_refresh_root_colors = False
    _binding_exclude = True

    def add_PropertyChanged(self, value):
        """Expose reactive event accessors before the CLR window in the MRO.

        IronPython's generated interface dispatch must find these accessors on
        the window side when a subclass also inherits the Reactive mixin.
        """
        self.PropertyChanged += value

    def remove_PropertyChanged(self, value):
        """Detach a reactive listener through the same CLR-visible accessor."""
        self.PropertyChanged -= value

    # ------------------------------------------------------------------ resources

    @staticmethod
    def setup_resources(wpf_ctrl, set_root_colors=True, resolve_theme=False):
        """Set pyRevit colour resources on any WPF control.

        Injects the brand palette (constant, used by HUD-style overlays)
        and the semantic light/dark palette as DynamicResource-able brushes.
        Theme resolution is opt-in so forms default to the light palette.

        Args:
            wpf_ctrl: any WPF FrameworkElement with a Resources dict.
            set_root_colors (bool): also force wpf_ctrl.Background/Foreground
                directly. Only safe before the control's own XAML is parsed:
                a window that declares its own literal Background (e.g. the
                transparent HUD-style overlays) must be able to override this
                afterwards. Live theme-change refreshes pass False so an
                already-open HUD window is not forced opaque.
            resolve_theme (bool): resolve the palette from Revit's active UI
                theme. Defaults to False.

        Note:
            The root colours are assigned directly rather than left to the
            implicit Window/Page style. The root element already exists before
            its Resources are populated, and its own implicit-style lookup does
            not reliably re-run once the brushes and Theme.xaml are merged
            afterwards, even though descendants created later during XAML
            parsing do pick the styles up.
        """
        _theme.setup_resources(
            wpf_ctrl, set_root_colors, resolve_theme, DEFAULT_RECOGNIZE_ACCESS_KEY
        )

    @staticmethod
    def apply_theme(wpf_ctrl):
        """Re-resolve and re-apply theme resources on an already-loaded control.

        Because window/control chrome binds to these resources with
        DynamicResource, overwriting the values here is enough to repaint
        an open window without reloading its XAML. Does not touch the root
        Background/Foreground directly — see _live_refresh_root_colors.

        Args:
            wpf_ctrl: any WPF FrameworkElement with a Resources dict.
        """
        _WPFMixin.setup_resources(wpf_ctrl, set_root_colors=False, resolve_theme=True)

    def apply_contrast_foregrounds(self):
        """Give every custom-background element a readable text color.

        Walks the logical tree and, for each element painting a background
        that is not one of the theme's own brushes, assigns whichever of the
        theme window foreground/background colors contrasts better with it.
        This keeps hardcoded accent colors in user XAML -- a pale red "danger"
        button, a pale green "confirm" button -- legible under a dark UI
        theme, where the inherited near-white text would otherwise vanish
        into them.

        Elements that declare their own Foreground are left untouched, and so
        are theme-brush backgrounds, which already pair with the theme
        foreground. Translucent backgrounds are left untouched because their
        effective color depends on the surface below them. Contrast is supplied
        by a style setter so disabled-state triggers remain authoritative,
        including when IsEnabled changes after the window opens. Safe to call
        again after a theme change; unchanged brushes reuse the managed style.
        Previously managed elements that stop qualifying regain their original
        style, unless a local Foreground has been authored. Detached elements
        are dropped from tracking on the next pass, and a failed element does
        not prevent the remaining controls from updating.
        """
        _theme.apply_contrast_foregrounds(self)

    def _apply_dark_titlebar(self):
        """No-op by default; overridden by WPFWindow (Page has no title bar)."""

    def _refresh_icon(self):
        """No-op by default; overridden by WPFWindow (Page has no icon)."""

    def _on_theme_refresh(self):
        """Re-theme resources and, for windows, the native title bar."""
        _WPFMixin.setup_resources(
            self,
            set_root_colors=self._live_refresh_root_colors,
            resolve_theme=True,
        )
        self.apply_contrast_foregrounds()
        self._apply_dark_titlebar()
        self._refresh_icon()

    def _subscribe_theme_changed(self):
        """Subscribe this control to Revit's ThemeChanged event, if available.

        Silently no-ops on Revit versions without a UITheme concept, and when
        already subscribed. The subscription ends when the form releases its
        callbacks (see ``_backend.on_release``); dockable pages under
        IronPython keep it for the session.
        """
        if getattr(self, "_on_theme_changed", None) is not None:
            return
        try:
            if not HOST_APP.is_newer_than(2024, True):
                return
            self._on_theme_changed = lambda sender, args: self._on_theme_refresh()
            HOST_APP.uiapp.ThemeChanged += self._on_theme_changed
        except Exception:
            self._on_theme_changed = None
            return
        _backend.on_release(self, self._unsubscribe_theme_changed)

    def _unsubscribe_theme_changed(self, sender=None, args=None):  # pylint: disable=unused-argument
        """Detach the ThemeChanged subscription set up by _subscribe_theme_changed."""
        handler = getattr(self, "_on_theme_changed", None)
        if handler is None:
            return
        try:
            HOST_APP.uiapp.ThemeChanged -= handler
        except Exception:
            pass
        self._on_theme_changed = None

    def merge_resource_dict(self, xaml_source):
        """Merge a ResourceDictionary xaml file into this control's resources.

        Under CPython, a dictionary merged before the XAML loads is queued and
        merged into the loaded markup instead, so it is parsed only once.

        Args:
            xaml_source (str): absolute path to a ResourceDictionary xaml file.
        """
        if _backend.queue_resource(self, xaml_source):
            return
        lang_dictionary = ResourceDictionary()
        lang_dictionary.Source = Uri(xaml_source, UriKind.Absolute)
        self.Resources.MergedDictionaries.Add(lang_dictionary)

    def get_locale_string(self, string_name, default=None):
        """Return a localised string from the merged ResourceDictionary.

        Missing keys are treated as recoverable UI state: they are logged and a
        safe fallback is returned so the form can keep working without surfacing a
        blocking WPF exception dialog.

        Args:
            string_name (str): resource key.
            default (any): fallback value when the resource is missing.

        Returns:
            str: localised string value or the provided fallback.
        """
        value = self.TryFindResource(string_name)
        if value is not None:
            return value

        fallback = default if default is not None else string_name
        mlogger.warning(
            "Missing WPF resource key '%s' on %s; using fallback '%s'.",
            string_name,
            self.__class__.__name__,
            fallback,
        )
        return fallback

    def _load_root(self, xaml_source, literal_string):
        """Load XAML into this form's root with pyRevit resources merged first.

        Resolves the locale fallback chain for paths (see
        ``_resolve_xaml_source``), applies contrast foregrounds and records
        the UI thread. Theme subscription and window chrome stay with the
        caller.
        """
        _backend.initialize(self)
        _WPFMixin.setup_resources(self, resolve_theme=self.resolve_theme)
        self.merge_resource_dict(THEME_XAML_FILE)
        if literal_string:
            _backend.load_component(self, framework.StringReader(xaml_source))
        else:
            xaml_path, pending_resource_merge = _resolve_xaml_source(xaml_source)
            # merge before LoadComponent so resources are available during parse
            if pending_resource_merge:
                self.merge_resource_dict(pending_resource_merge)
            _backend.load_component(self, xaml_path)
        self.apply_contrast_foregrounds()
        self.thread_id = framework.get_current_thread_id()

    # ------------------------------------------------------------------ images

    @staticmethod
    def set_image_source_file(wpf_element, image_file):
        """Set the source of a WPF Image element from a file path.

        Args:
            wpf_element (System.Windows.Controls.Image): target image element.
            image_file (str): absolute or command-relative image path.
        """
        if not op.exists(image_file):
            wpf_element.Source = utils.bitmap_from_file(
                os.path.join(EXEC_PARAMS.command_path, image_file)
            )
        else:
            wpf_element.Source = utils.bitmap_from_file(image_file)

    def set_image_source(self, wpf_element, image_file):
        """Set the source of a WPF Image element from a file path.

        Args:
            wpf_element (System.Windows.Controls.Image): target image element.
            image_file (str): absolute or command-relative image path.
        """
        _WPFMixin.set_image_source_file(wpf_element, image_file)

    # ------------------------------------------------------------------ visibility

    @staticmethod
    def hide_element(*wpf_elements):
        """Collapse one or more WPF elements (removes from layout).

        Args:
            *wpf_elements (list[UIElement]): elements to collapse.
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = WPF_COLLAPSED

    @staticmethod
    def show_element(*wpf_elements):
        """Make one or more collapsed WPF elements visible.

        Args:
            *wpf_elements (list[UIElement]): elements to show.
        """
        for wpfel in wpf_elements:
            wpfel.Visibility = WPF_VISIBLE

    @staticmethod
    def toggle_element(*wpf_elements):
        """Toggle visibility of one or more WPF elements.

        Args:
            *wpf_elements (list[UIElement]): elements to toggle.
        """
        for wpfel in wpf_elements:
            if wpfel.Visibility == WPF_VISIBLE:
                _WPFMixin.hide_element(wpfel)
            elif wpfel.Visibility == WPF_COLLAPSED:
                _WPFMixin.show_element(wpfel)

    # ------------------------------------------------------------------ enabled

    @staticmethod
    def disable_element(*wpf_elements):
        """Disable one or more WPF elements.

        Args:
            *wpf_elements (list[UIElement]): elements to disable.
        """
        for wpfel in wpf_elements:
            wpfel.IsEnabled = False

    @staticmethod
    def enable_element(*wpf_elements):
        """Enable one or more WPF elements.

        Args:
            *wpf_elements (list[UIElement]): elements to enable.
        """
        for wpfel in wpf_elements:
            wpfel.IsEnabled = True

    # ------------------------------------------------------------------ threading

    def dispatch(self, func, *args, **kwargs):
        """Run a function on the opposite thread.

        When called from the UI thread, spawns a background thread.
        When called from a background thread, marshals execution back
        onto the UI thread via the Dispatcher.  This makes the pattern
        for background work + UI updates symmetrical:

            # on UI thread — starts background work
            self.dispatch(self._do_work)

            def _do_work(self):
                ...heavy work...
                # on background thread — posts UI update
                self.dispatch(self._update_label, "done")

        Args:
            func (Callable): function to run.
            *args: positional arguments forwarded to func.
            **kwargs: keyword arguments forwarded to func.
        """
        if framework.get_current_thread_id() == self.thread_id:
            t = threading.Thread(target=func, args=args, kwargs=kwargs)
            t.start()
        else:
            self.Dispatcher.Invoke(
                System.Action(lambda: func(*args, **kwargs)),
                Threading.DispatcherPriority.Background,
            )

    # ------------------------------------------------------------------ misc

    @property
    def pyrevit_version(self):
        """Active pyRevit formatted version string, e.g. '4.9-beta'."""
        return "pyRevit {}".format(versionmgr.get_pyrevit_version().get_formatted())

    def handle_url_click(self, sender, args):  # pylint: disable=unused-argument
        """XAML event handler: open a Hyperlink URL in the default browser.

        Wire up in XAML with:  RequestNavigate="handle_url_click"
        """
        return webbrowser.open_new_tab(sender.NavigateUri.AbsoluteUri)


def _resolve_xaml_source(xaml_source):
    """Resolve a XAML path with full locale-fallback logic.

    Resolution order:
      1. <name>.<locale>.xaml                      full localised replacement
      2. <name>.en_us.xaml                         English replacement
      3. <name>.xaml  +  ResourceDictionary merge  localised strings
      4. <name>.xaml  +  ResourceDictionary merge  English strings
      5. <name>.xaml                               bare, no merge

    Args:
        xaml_source (str): xaml filename or absolute path.

    Returns:
        tuple(str, str|None): (resolved xaml path, resource-dict path or None)
    """
    xaml_file = xaml_source
    if not op.exists(xaml_file):
        xaml_file = os.path.join(EXEC_PARAMS.command_path, xaml_source)

    localized_xaml = xaml_file.replace(
        ".xaml", ".{}.xaml".format(user_config.user_locale)
    )
    english_xaml = xaml_file.replace(".xaml", ".en_us.xaml")
    localized_res = xaml_file.replace(
        ".xaml", ".ResourceDictionary.{}.xaml".format(user_config.user_locale)
    )
    english_res = xaml_file.replace(".xaml", ".ResourceDictionary.en_us.xaml")

    if os.path.isfile(localized_xaml):
        return localized_xaml, None
    if os.path.isfile(english_xaml):
        return english_xaml, None
    if os.path.isfile(localized_res):
        return xaml_file, localized_res
    if os.path.isfile(english_res):
        return xaml_file, english_res
    return xaml_file, None


class WPFWindow(_WPFMixin, _backend.Window):
    r"""WPF Window base class for all pyRevit forms.

    Args:
        xaml_source (str): xaml source filepath or xaml content
        literal_string (bool): xaml_source contains xaml content, not filepath
        handle_esc (bool): handle Escape button and close the window
        set_owner (bool): set the owner of window to host app window

    Optional class attributes:
        resolve_theme (bool):
            resolve the palette from Revit's active UI theme. Defaults to False.

    Examples:
        ```python
        from pyrevit import forms
        layout = '<Window ' \
                 'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" ' \
                 'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" ' \
                 'ShowInTaskbar="False" ResizeMode="NoResize" ' \
                 'WindowStartupLocation="CenterScreen" ' \
                 'HorizontalContentAlignment="Center">' \
                 '</Window>'
        w = forms.WPFWindow(layout, literal_string=True)
        w.show()
        ```
    """

    resolve_theme = False
    _binding_exclude = True

    def __init__(
        self,
        xaml_source,
        literal_string=False,
        handle_esc=True,
        set_owner=True,
    ):
        """Initialize WPF window and resources."""
        with _backend.disposing(self):
            self.load_xaml(
                xaml_source,
                literal_string=literal_string,
                handle_esc=handle_esc,
                set_owner=set_owner,
            )

    def load_xaml(
        self,
        xaml_source,
        literal_string=False,
        handle_esc=True,
        set_owner=True,
    ):
        """Load the window XAML file.

        Args:
            xaml_source (str): The XAML content or file path to load.
            literal_string (bool, optional): True if `xaml_source` is content,
                False if it is a path. Defaults to False.
            handle_esc (bool, optional): Whether the ESC key should be handled.
                Defaults to True.
            set_owner (bool, optional): Whether to set the window owner.
                Defaults to True.

        Note:
            Safe to call on an instance whose ``__init__`` did not call
            ``WPFWindow.__init__``, as ``script.load_ui`` allows.
        """
        # create new id for this window
        self.window_id = coreutils.new_uuid()
        self._load_root(xaml_source, literal_string)
        if set_owner:
            self.setup_owner()
        self.setup_icon()
        if handle_esc:
            self.setup_default_handlers()
        if self.resolve_theme:
            self._apply_dark_titlebar()
            self._subscribe_theme_changed()

    def setup_owner(self):
        """Set the window owner."""
        wih = Interop.WindowInteropHelper(_backend.unwrap(self))
        wih.Owner = AdWindows.ComponentManager.ApplicationWindow

    def setup_default_handlers(self):
        """Set the default handlers."""
        _backend.bind_event(self, "PreviewKeyDown", self.handle_input_key)

    def handle_input_key(self, sender, args):  # pylint: disable=W0613
        """Handle keyboard input and close the window on Escape."""
        if args.Key == Input.Key.Escape:
            self.Close()

    def _apply_dark_titlebar(self):
        """Re-skin this window's native title bar to match the active theme.

        Keeps the OS chrome (icon, drag, resize, snap, min/max/close) intact;
        only recolors it, instead of replacing it with custom-drawn chrome.
        DWMWA_USE_IMMERSIVE_DARK_MODE picks light vs dark glyphs/contrast on
        any supported Windows version; the exact caption/text colors (so the
        title bar matches pyRevit's own palette rather than the OS default
        dark gray) additionally require Windows 11 22000+ and are a no-op
        elsewhere.
        """
        _theme.apply_title_bar_theme(self)

    def set_icon(self, icon_path):
        """Set window icon to given icon path."""
        self.Icon = utils.bitmap_from_file(icon_path)

    def _refresh_icon(self):
        """Repaint the default window icon for the active theme."""
        self.setup_icon()

    def setup_icon(self):
        """Setup default window icon, following the bundle icon convention.

        If required, picks up pyrevit_settings.dark.png under a dark UI theme,
        the same <name>.dark.png lookup that extension bundle icons use.
        """
        if self.resolve_theme:
            icon_file = revit.ui.resolve_icon_file(BIN_DIR, "pyrevit_settings.png")
        else:
            icon_file = op.join(BIN_DIR, "pyrevit_settings.png")
            if not op.exists(icon_file):
                icon_file = None
        if icon_file:
            self.set_icon(icon_file)

    def hide(self):
        """Hide window."""
        self.Hide()

    def show(self, modal=False):
        """Show window."""
        if modal:
            return self.ShowDialog()
        # else open non-modal
        self.Show()

    def show_dialog(self):
        """Show modal window."""
        return self.ShowDialog()

    def conceal(self):
        """Conceal window."""
        return WindowToggler(self)
