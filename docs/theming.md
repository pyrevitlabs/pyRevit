# Theming and dark mode

Revit 2024 introduced a light/dark UI theme. pyRevit follows it: ribbon icons, panel backgrounds,
and WPF forms all switch with the host, and a theme change applies without reloading the session.

On Revit 2021–2023 there is no theme API. Everything below degrades to the light theme, and no
bundle key or form attribute needs removing to build for those versions.

## How the theme is detected

`RevitThemeDetector` reads Revit's active `UITheme` through reflection rather than a compile-time
reference, so the same detector logic supports every supported Revit version. The loader uses
the `net48` assembly for Revit 2021–2024 and the `net8.0` assembly for Revit 2025 and later.
When the API is missing the detector reports light.

Two consumers sit on top of it:

- `RevitThemeChangeMonitor` subscribes to Revit's `ThemeChanged` event and drives live refreshes.
- `RibbonThemeRegistry` holds the refresh actions for ribbon icons and panel backgrounds, so a theme
  switch repaints them in place.

From Python, `pyrevit.forms.is_dark_theme()` returns the current state, and always returns `False`
on Revit versions without the theme API.

## Ribbon icons

A bundle ships a dark variant by placing `icon.dark.png` next to `icon.png`. The pattern is exact
and case-insensitive — no other suffix is recognised:

```text
MyButton.pushbutton/
  bundle.yaml
  script.py
  icon.png            # used in light theme, and on Revit 2021-2023
  icon.dark.png       # used in dark theme
```

A bundle with no `icon.dark.png` keeps using `icon.png` in both themes. That is usually fine for
full-colour icons and usually wrong for monochrome line-art, which disappears against a dark ribbon.

## Panel backgrounds

`*.panel` bundles declare `background_dark` alongside `background`. Both accept a single colour or a
map of `panel` / `title` / `slideout`, and each area falls back to its light colour when the dark
form leaves it unset.

See [Panel background colors](extensions.md#panel-background-colors) for the full key reference.

## WPF forms

### The palette

`pyrevitlib/pyrevit/forms/Theme.xaml` is a central resource dictionary that re-templates the
standard WPF controls — `Button`, `TextBox`, `ComboBox`, `ListBox`/`ListView`, `CheckBox`,
`RadioButton`, `Expander`, `GroupBox`, `TabItem`, `ScrollBar`, `ContextMenu`, `MenuItem`, `ToolTip`,
`Separator`, `Label`, `DataGrid` — against named brushes instead of literal colours.

Every pyRevit WPF control gets a semantic palette injected into its resources at construction. Each
entry exists as both `pyRevit<Name>Color` and `pyRevit<Name>Brush`:

| Group | Names |
|---|---|
| Surfaces | `WindowBackground`, `ChromeBackground`, `ControlBackground`, `ButtonBackground`, `ContrastBackground` |
| Text | `WindowForeground`, `ContrastForeground`, `SubtleForeground`, `DisabledForeground` |
| Interaction | `ControlBorder`, `ControlHover`, `ControlPressed`, `ControlOverlayHover`, `ControlOverlayPressed` |
| Selection | `SelectionBackground`, `SelectionForeground` |
| Status | `DangerForeground`, `DangerBackground`, `WarningForeground`, `WarningBackground`, `SuccessBackground` |
| Other | `Icon`, `ScrollBarThumb`, `ScrollBarThumbHover` |

`pyRevitIsDarkTheme` is also set as a resource, for XAML that needs to branch on the theme directly.

Reference them with `DynamicResource` so they track live theme changes:

```xml
<TextBlock Text="Ready"
           Background="{DynamicResource pyRevitWindowBackgroundBrush}"
           Foreground="{DynamicResource pyRevitSubtleForegroundBrush}" />
```

A separate brand palette (`pyRevitDark`, `pyRevitDarkerDark`, `pyRevitAccent`) is constant across
themes and is what the HUD-style overlays use.

### Opting a window in

Theme resolution is **opt-in**. A `WPFWindow` defaults to the light palette, so existing third-party
forms keep rendering exactly as before. Set the class attribute to follow Revit:

```python
from pyrevit import forms


class MyWindow(forms.WPFWindow):
    resolve_theme = True

    def __init__(self, xaml_file):
        forms.WPFWindow.__init__(self, xaml_file)
```

`resolve_theme` is read at class level, so it can be set on a subclass without touching
`__init__` — which keeps a form working on older pyRevit versions that do not know the attribute.

pyRevit's own dialogs (`SelectFromList`, `GetValueWindow`, the settings window, ...) already opt in.

### Title bar

`WPFWindow` recolours the native OS title bar to match, via a `DwmApi` wrapper that toggles
`DWMWA_USE_IMMERSIVE_DARK_MODE`. On Windows 11 build 22000+ it additionally sets the exact caption
and caption-text colours. Both calls are no-ops on older Windows, where the title bar stays in the
system colour.

## Writing theme-aware forms

- Never hardcode `White`, `Black`, `DimGray` or similar in XAML. Bind to a palette brush instead.
- Use `DynamicResource`, not `StaticResource`, or the control will not follow a live theme switch.
- Check contrast in both themes. `ContrastBackground`/`ContrastForeground` exist for the cases where
  a surface must stay readable regardless of theme.
- A window that declares its own literal `Background` — a transparent overlay, for instance — keeps
  it. Root colours are only forced before the window's own XAML is parsed.

## Version support

| Revit | Theme API | Behaviour |
|---|---|---|
| 2024+ | `UITheme` available | Full: icons, panel backgrounds, forms, title bar, live switching |
| 2021–2023 | none | Light theme everywhere; `is_dark_theme()` returns `False`, `icon.dark.png` and `background_dark` are ignored |
