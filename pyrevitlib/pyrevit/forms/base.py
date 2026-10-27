# coding: utf-8
"""Shared WPF window resources, theming and lifecycle across Python engines."""

import os
import os.path as op
import threading
import webbrowser

from pyrevit import HOST_APP, EXEC_PARAMS, BIN_DIR
from pyrevit import coreutils, framework, revit, versionmgr
from pyrevit.api import AdWindows
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import (
    System,
    Threading,
    Interop,
    Input,
    Media,
    Controls,
    Documents,
)
from pyrevit.framework import Uri, UriKind, ResourceDictionary
from pyrevit.labs import Common
from pyrevit.userconfig import user_config
from . import _backend
from . import utils

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


_BRAND_DARK = (0xFF, 0x2C, 0x3E, 0x50)  # dark blue-gray
_BRAND_DARKER_DARK = (0xFF, 0x23, 0x30, 0x3D)  # darker blue-gray
_BRAND_ACCENT = (0xFF, 0xF3, 0x9C, 0x12)  # amber

_PALETTE_LIGHT = {
    "WindowBackground": (0xFF, 0xF3, 0xF4, 0xF6),  # off white
    "WindowForeground": (0xFF, 0x00, 0x00, 0x00),  # black
    "ChromeBackground": (0xFF, 0xE8, 0xE8, 0xE8),  # light gray
    "ControlBackground": (0xFF, 0xFF, 0xFF, 0xFF),  # white
    "ButtonBackground": (0xFF, 0xF0, 0xF0, 0xF0),  # whitesmoke
    "ContrastBackground": (0xFF, 0x2C, 0x3E, 0x50),  # dark blue-gray
    "ContrastForeground": (0xFF, 0xFF, 0xFF, 0xFF),  # white
    "ControlBorder": (0xFF, 0xCC, 0xCC, 0xCC),  # light gray
    "ControlHover": (0xFF, 0xE5, 0xE5, 0xE5),  # light gray
    "ControlPressed": (0xFF, 0xD9, 0xD9, 0xD9),  # light gray
    "ControlOverlayHover": (0x0C, 0x00, 0x00, 0x00),  # translucent black
    "ControlOverlayPressed": (0x18, 0x00, 0x00, 0x00),  # translucent black
    "DisabledForeground": (0xFF, 0xA0, 0xA0, 0xA0),  # gray
    "SubtleForeground": (0xFF, 0x69, 0x69, 0x69),  # dim gray
    "DangerForeground": (0xFF, 0xB4, 0x23, 0x18),  # brick red
    "DangerBackground": (0xFF, 0xFB, 0xD5, 0xD5),  # misty rose
    "WarningForeground": (0xFF, 0x9A, 0x63, 0x00),  # dark amber
    "WarningBackground": (0xFF, 0xFD, 0xF0, 0xD5),  # pale amber
    "SuccessBackground": (0xFF, 0xD4, 0xEF, 0xD8),  # pale green
    "Icon": (0xFF, 0x00, 0x00, 0x00),  # black
    "SelectionBackground": (0xFF, 0xCC, 0xE4, 0xF7),  # pale blue
    "SelectionForeground": (0xFF, 0x00, 0x00, 0x00),  # black
    "ScrollBarThumb": (0xFF, 0xCC, 0xCC, 0xCC),  # light gray
    "ScrollBarThumbHover": (0xFF, 0xAA, 0xAA, 0xAA),  # dark gray
}

_PALETTE_DARK = {
    "WindowBackground": (0xFF, 0x2E, 0x34, 0x40),  # charcoal blue
    "WindowForeground": (0xFF, 0xEC, 0xF0, 0xF1),  # light gray
    "ChromeBackground": (0xFF, 0x39, 0x42, 0x4F),  # dark slate
    "ControlBackground": (0xFF, 0x22, 0x29, 0x33),  # charcoal
    "ButtonBackground": (0xFF, 0x22, 0x29, 0x33),  # charcoal
    "ContrastBackground": (0xFF, 0xEC, 0xF0, 0xF1),  # light gray
    "ContrastForeground": (0xFF, 0x2C, 0x3E, 0x50),  # dark blue-gray
    "ControlBorder": (0xFF, 0x45, 0x4F, 0x61),  # slate blue
    "ControlHover": (0xFF, 0x45, 0x4F, 0x61),  # slate blue
    "ControlPressed": (0xFF, 0x52, 0x5E, 0x73),  # steel blue
    "ControlOverlayHover": (0x28, 0xFF, 0xFF, 0xFF),  # translucent white
    "ControlOverlayPressed": (0x37, 0xFF, 0xFF, 0xFF),  # translucent white
    "DisabledForeground": (0xFF, 0x7F, 0x8C, 0x8D),  # gray
    "SubtleForeground": (0xFF, 0x95, 0xA5, 0xA6),  # muted blue-gray
    "DangerForeground": (0xFF, 0xFF, 0x6B, 0x61),  # coral
    "DangerBackground": (0xFF, 0x5C, 0x2E, 0x2E),  # dark red
    "WarningForeground": (0xFF, 0xF0, 0xAD, 0x4E),  # amber
    "WarningBackground": (0xFF, 0x5C, 0x48, 0x2E),  # dark amber
    "SuccessBackground": (0xFF, 0x2C, 0x4C, 0x33),  # dark green
    "Icon": (0xFF, 0xEC, 0xF0, 0xF1),  # light gray
    "SelectionBackground": (0xFF, 0x33, 0x50, 0x6E),  # dark blue
    "SelectionForeground": (0xFF, 0xEC, 0xF0, 0xF1),  # light gray
    "ScrollBarThumb": (0xFF, 0x45, 0x4F, 0x61),  # slate blue
    "ScrollBarThumbHover": (0xFF, 0x52, 0x5E, 0x73),  # steel blue
}


def _colorref(argb):
    """Convert an (a, r, g, b) byte tuple to a Win32 COLORREF (0x00BBGGRR)."""
    _, r, g, b = argb
    return r | (g << 8) | (b << 16)


def _argb(color):
    """Convert a Media.Color to a hashable (a, r, g, b) byte tuple."""
    return (color.A, color.R, color.G, color.B)


def _srgb_component(byte_value):
    """Linearize a single 0-255 sRGB channel for luminance math."""
    channel = byte_value / 255.0
    if channel <= 0.03928:
        return channel / 12.92
    return pow((channel + 0.055) / 1.055, 2.4)


def _relative_luminance(color):
    """Return the WCAG relative luminance of a Media.Color."""
    return (
        0.2126 * _srgb_component(color.R)
        + 0.7152 * _srgb_component(color.G)
        + 0.0722 * _srgb_component(color.B)
    )


def _contrast_ratio(first_color, second_color):
    """Return the WCAG contrast ratio between two Media.Color values."""
    first = _relative_luminance(first_color)
    second = _relative_luminance(second_color)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def _background_property(wpf_element):
    """Return the DependencyProperty painting an element's own background.

    Returns:
        DependencyProperty or None: None for elements that paint no background.
    """
    if isinstance(wpf_element, Controls.Control):
        return Controls.Control.BackgroundProperty
    if isinstance(wpf_element, Controls.TextBlock):
        return Controls.TextBlock.BackgroundProperty
    if isinstance(wpf_element, Controls.Panel):
        return Controls.Panel.BackgroundProperty
    if isinstance(wpf_element, Controls.Border):
        return Controls.Border.BackgroundProperty
    return None


def _is_authored_value(wpf_element, dependency_property):
    """Return True if a property value was authored rather than defaulted.

    WPF hands out opaque metadata defaults for properties nobody set -- a bare
    CheckBox reports a white Background its template never paints. Those must
    not be mistaken for a real background, or the element gets a foreground
    picked to contrast against a color that is never drawn.
    """
    try:
        source = framework.Windows.DependencyPropertyHelper.GetValueSource(
            wpf_element, dependency_property
        ).BaseValueSource
    except Exception:
        return False
    return source not in (
        framework.Windows.BaseValueSource.Default,
        framework.Windows.BaseValueSource.DefaultStyle,
        framework.Windows.BaseValueSource.DefaultStyleTrigger,
        framework.Windows.BaseValueSource.Inherited,
        framework.Windows.BaseValueSource.Unknown,
    )


def _foreground_property(wpf_element):
    """Return the DependencyProperty carrying text color for an element.

    Controls and TextBlocks own a Foreground; Panels and Borders do not, so
    the inherited TextElement.Foreground attached property is used to color
    whatever text they contain.

    Returns:
        DependencyProperty or None: None for elements that paint no text.
    """
    if isinstance(wpf_element, Controls.Control):
        return Controls.Control.ForegroundProperty
    if isinstance(wpf_element, Controls.TextBlock):
        return Controls.TextBlock.ForegroundProperty
    if isinstance(wpf_element, (Controls.Panel, Controls.Border)):
        return Documents.TextElement.ForegroundProperty
    return None


def _walk_logical_tree(root):
    """Yield root and every logical descendant of a WPF element.

    The logical tree deliberately excludes control-template internals, so
    only elements authored in the window/panel XAML are visited.
    """
    pending = [_backend.unwrap(root)]
    while pending:
        current = pending.pop()
        yield current
        try:
            children = framework.Windows.LogicalTreeHelper.GetChildren(current)
        except Exception:
            continue
        for child in children:
            if isinstance(child, framework.Windows.DependencyObject):
                pending.append(child)


def is_dark_theme():
    """Return True if Revit's active UI theme is Dark.

    Always False on Revit <2024, which has no UITheme concept.
    """
    try:
        if HOST_APP.is_newer_than(2024, True):
            from Autodesk.Revit.UI import UITheme

            return revit.ui.get_current_theme() == UITheme.Dark
    except Exception:
        pass
    return False


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
    """
    _backend.unwrap(control).DataContext = _backend.binding_source(model)


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
        res = wpf_ctrl.Resources

        def _set_color(key, argb):
            res[key + "Color"] = Media.Color.FromArgb(*argb)
            res[key + "Brush"] = Media.SolidColorBrush(res[key + "Color"])

        _set_color("pyRevitDark", _BRAND_DARK)
        _set_color("pyRevitDarkerDark", _BRAND_DARKER_DARK)
        _set_color("pyRevitAccent", _BRAND_ACCENT)
        res["pyRevitButtonColor"] = Media.Color.FromArgb(0xFF, 0xFF, 0xFF, 0xFF)
        res["pyRevitButtonForgroundBrush"] = Media.SolidColorBrush(
            res["pyRevitButtonColor"]
        )

        is_dark = resolve_theme and is_dark_theme()
        palette = _PALETTE_DARK if is_dark else _PALETTE_LIGHT
        for name, argb in palette.items():
            _set_color("pyRevit" + name, argb)
        res["pyRevitIsDarkTheme"] = is_dark

        res["pyRevitRecognizesAccessKey"] = DEFAULT_RECOGNIZE_ACCESS_KEY

        if set_root_colors:
            wpf_ctrl.Background = res["pyRevitWindowBackgroundBrush"]
            wpf_ctrl.Foreground = res["pyRevitWindowForegroundBrush"]

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
        res = self.Resources
        try:
            candidates = [
                b
                for b in [
                    res["pyRevitWindowForegroundBrush"],
                    res["pyRevitWindowBackgroundBrush"],
                ]
                if b is not None and b.Color is not None
            ]
            theme_argbs = set(
                _argb(res[key]) for key in list(res.Keys) if str(key).endswith("Color")
            )
        except Exception:
            return

        if not candidates:
            return

        previous_managed = getattr(self, "_contrast_managed", {})
        managed = {}
        self._contrast_managed = managed

        for element in _walk_logical_tree(self):
            try:
                if element in previous_managed:
                    managed[element] = previous_managed[element]
                fore_prop = _foreground_property(element)
                back_prop = _background_property(element)
                if fore_prop is None or back_prop is None:
                    continue
                if (
                    element.ReadLocalValue(fore_prop)
                    != framework.Windows.DependencyProperty.UnsetValue
                ):
                    continue
                brush = (
                    element.GetValue(back_prop)
                    if _is_authored_value(element, back_prop)
                    else None
                )
                if (
                    not isinstance(brush, Media.SolidColorBrush)
                    or brush.Color.A != 0xFF
                    or _argb(brush.Color) in theme_argbs
                ):
                    contrast_style = managed.get(element)
                    if contrast_style is not None:
                        if element.Style is contrast_style:
                            element.Style = contrast_style.BasedOn
                        del managed[element]
                    continue
                background = brush.Color
                best = max(
                    candidates,
                    key=lambda candidate: _contrast_ratio(background, candidate.Color),
                )
                base_style = element.Style
                if element in managed and base_style is managed[element]:
                    if base_style.Setters[0].Value is best:
                        continue
                    base_style = base_style.BasedOn
                contrast_style = framework.Windows.Style(element.GetType(), base_style)
                contrast_style.Setters.Add(framework.Windows.Setter(fore_prop, best))
                element.Style = contrast_style
                managed[element] = contrast_style
            except Exception as contrast_error:
                mlogger.debug("Could not apply contrast foreground: %s", contrast_error)
                continue

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

        Silently no-ops on Revit versions without a UITheme concept.
        """
        try:
            if not HOST_APP.is_newer_than(2024, True):
                return
            self._on_theme_changed = lambda sender, args: self._on_theme_refresh()
            HOST_APP.uiapp.ThemeChanged += self._on_theme_changed
        except Exception:
            self._on_theme_changed = None

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

        Args:
            xaml_source (str): absolute path to a ResourceDictionary xaml file.
        """
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

    def __init__(
        self,
        xaml_source,
        literal_string=False,
        handle_esc=True,
        set_owner=True,
    ):
        """Initialize WPF window and resources."""
        _backend.initialize(self)
        try:
            self.load_xaml(
                xaml_source,
                literal_string=literal_string,
                handle_esc=handle_esc,
                set_owner=set_owner,
            )
        except Exception:
            _backend.dispose(self)
            raise

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
        """
        # create new id for this window
        self.window_id = coreutils.new_uuid()

        _WPFMixin.setup_resources(self, resolve_theme=self.resolve_theme)
        self.merge_resource_dict(THEME_XAML_FILE)
        if not literal_string:
            xaml_path, pending_resource_merge = _resolve_xaml_source(xaml_source)
            # merge before LoadComponent so resources are available during parse
            if pending_resource_merge:
                self.merge_resource_dict(pending_resource_merge)
            _backend.load_component(self, xaml_path)
        else:
            _backend.load_component(self, framework.StringReader(xaml_source))

        # set properties
        self.apply_contrast_foregrounds()
        self.thread_id = framework.get_current_thread_id()
        if set_owner:
            self.setup_owner()
        self.setup_icon()
        if handle_esc:
            self.setup_default_handlers()
        if self.resolve_theme:
            self._apply_dark_titlebar()
            self._subscribe_theme_changed()
        _backend.bind_event(self, "Closed", self._unsubscribe_theme_changed)

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
        try:
            wih = Interop.WindowInteropHelper(_backend.unwrap(self))
            hwnd = wih.EnsureHandle()
            is_dark = is_dark_theme()
            Common.DwmApi.SetImmersiveDarkMode(hwnd, is_dark)
            palette = _PALETTE_DARK if is_dark else _PALETTE_LIGHT
            caption_color = _colorref(palette["ChromeBackground"])
            text_color = _colorref(palette["WindowForeground"])
            Common.DwmApi.SetTitleBarColors(hwnd, caption_color, text_color)
        except Exception:
            pass

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
