# coding: utf-8
"""Palette, contrast and title-bar theming for pyRevit WPF forms.

Shared by both Python engines; ``base`` re-exports the public names and the
form mixin delegates here.

Note:
    This module must stay importable by IronPython 2.7.
"""

from pyrevit import HOST_APP
from pyrevit import framework, revit
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import Interop, Media, Controls, Documents
from pyrevit.labs import Common
from . import _backend

mlogger = get_logger(__name__)


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


def setup_resources(wpf_ctrl, set_root_colors, resolve_theme, recognize_access_key):
    """Write the pyRevit palette brushes into a control's resources.

    See ``_WPFMixin.setup_resources`` for the argument contract;
    ``recognize_access_key`` becomes the ``pyRevitRecognizesAccessKey``
    resource.
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

    res["pyRevitRecognizesAccessKey"] = recognize_access_key

    if set_root_colors:
        wpf_ctrl.Background = res["pyRevitWindowBackgroundBrush"]
        wpf_ctrl.Foreground = res["pyRevitWindowForegroundBrush"]


def apply_contrast_foregrounds(form):
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
    res = form.Resources
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

    previous_managed = getattr(form, "_contrast_managed", {})
    managed = {}
    form._contrast_managed = managed

    for element in _walk_logical_tree(form):
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


def apply_title_bar_theme(window):
    """Re-skin a window's native title bar to match the active theme.

    Keeps the OS chrome (icon, drag, resize, snap, min/max/close) intact;
    only recolors it, instead of replacing it with custom-drawn chrome.
    DWMWA_USE_IMMERSIVE_DARK_MODE picks light vs dark glyphs/contrast on
    any supported Windows version; the exact caption/text colors (so the
    title bar matches pyRevit's own palette rather than the OS default
    dark gray) additionally require Windows 11 22000+ and are a no-op
    elsewhere. Failures are ignored.
    """
    try:
        wih = Interop.WindowInteropHelper(_backend.unwrap(window))
        hwnd = wih.EnsureHandle()
        is_dark = is_dark_theme()
        Common.DwmApi.SetImmersiveDarkMode(hwnd, is_dark)
        palette = _PALETTE_DARK if is_dark else _PALETTE_LIGHT
        caption_color = _colorref(palette["ChromeBackground"])
        text_color = _colorref(palette["WindowForeground"])
        Common.DwmApi.SetTitleBarColors(hwnd, caption_color, text_color)
    except Exception:
        pass
