"""Exercise the real contrast pass with a small WPF precedence model.

These portable tests cover style composition and state changes. Actual WPF
value sources and rendering still require the Windows probe window.
"""

import ast
import io
import os
import unittest


class _Namespace(object):
    def __init__(self, **values):
        self.__dict__.update(values)


class _Setters(list):
    def Add(self, setter):
        self.append(setter)


class _Setter(object):
    def __init__(self, prop, value):
        self.Property = prop
        self.Value = value


class _Style(object):
    def __init__(self, target_type, based_on=None):
        self.TargetType = target_type
        self.BasedOn = based_on
        self.Setters = _Setters()


class _Brush(object):
    def __init__(self, red, green, blue, alpha=255):
        self.Color = _Namespace(A=alpha, R=red, G=green, B=blue)


class _Resources(dict):
    @property
    def Keys(self):
        return list(self.keys())


_UNSET = object()


class _Element(object):
    def __init__(self, background, style=None):
        self.local = {"Background": background}
        self.Style = style
        self.IsEnabled = True
        self.disabled_brush = None

    def GetType(self):
        return type(self)

    def ReadLocalValue(self, prop):
        return self.local.get(prop, _UNSET)

    def SetValue(self, prop, value):
        self.local[prop] = value

    def GetValue(self, prop):
        if prop in self.local:
            return self.local[prop]
        if prop == "Foreground" and not self.IsEnabled:
            return self.disabled_brush
        style = self.Style
        while style is not None:
            for setter in reversed(style.Setters):
                if setter.Property == prop:
                    return setter.Value
            style = style.BasedOn
        return None


def _load_contrast_pass(test):
    """Compile production definitions without importing Revit or WPF."""
    source_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "pyrevitlib",
            "pyrevit",
            "forms",
            "_theme.py",
        )
    )
    with io.open(source_path, encoding="utf-8") as source:
        tree = ast.parse(source.read())
    names = {
        "_argb",
        "_srgb_component",
        "_relative_luminance",
        "_contrast_ratio",
        "apply_contrast_foregrounds",
    }
    selected = [node for node in tree.body if getattr(node, "name", None) in names]
    if "apply_contrast_foregrounds" not in {node.name for node in selected}:
        test.fail("Production apply_contrast_foregrounds function was not found")
    tree.body = selected
    scope = {
        "framework": _Namespace(
            Windows=_Namespace(
                DependencyProperty=_Namespace(UnsetValue=_UNSET),
                Style=_Style,
                Setter=_Setter,
            )
        ),
        "Media": _Namespace(SolidColorBrush=_Brush),
        "_walk_logical_tree": lambda window: window.elements,
        "_foreground_property": lambda element: "Foreground",
        "_background_property": lambda element: "Background",
        "_is_authored_value": lambda element, prop: prop in element.local,
        "mlogger": _Namespace(debug=lambda *args: test.debug_messages.append(args)),
    }
    exec(compile(tree, source_path, "exec"), scope)
    return scope["apply_contrast_foregrounds"]


class FormsContrastTests(unittest.TestCase):
    """Keep contrast below triggers without losing user styles or local values."""

    def setUp(self):
        """Prepare contrasting colors and a window for the production pass."""
        self.debug_messages = []
        self.apply = _load_contrast_pass(self)
        self.black = _Brush(0, 0, 0)
        self.white = _Brush(255, 255, 255)
        self.disabled = _Brush(160, 160, 160)
        self.window = _Namespace(
            Resources=_Resources(
                pyRevitWindowForegroundBrush=self.black,
                pyRevitWindowBackgroundBrush=self.white,
                pyRevitWindowForegroundColor=self.black.Color,
                pyRevitWindowBackgroundColor=self.white.Color,
            ),
            elements=[],
        )

    def element(self, style=None):
        """Add a pale colored control with a disabled-state template trigger."""
        element = _Element(_Brush(255, 200, 200), style)
        element.disabled_brush = self.disabled
        self.window.elements.append(element)
        return element

    def test_enabled_and_disabled_foregrounds(self):
        """Contrast wins when enabled; the disabled trigger wins otherwise."""
        enabled = self.element()
        disabled = self.element()
        disabled.IsEnabled = False
        self.apply(self.window)
        self.assertIs(enabled.GetValue("Foreground"), self.black)
        self.assertIs(disabled.GetValue("Foreground"), self.disabled)
        for element in (enabled, disabled):
            self.assertIs(element.ReadLocalValue("Foreground"), _UNSET)

    def test_runtime_enabled_changes(self):
        """Both initial states can toggle repeatedly without another pass."""
        for initially_enabled in (True, False):
            element = self.element()
            element.IsEnabled = initially_enabled
            self.apply(self.window)
            for enabled in (False, True, False, True):
                element.IsEnabled = enabled
                self.assertIs(
                    element.GetValue("Foreground"),
                    self.black if enabled else self.disabled,
                )
                self.assertIs(element.ReadLocalValue("Foreground"), _UNSET)

    def test_existing_style_and_setters_are_preserved(self):
        """The contrast style derives from the exact existing user style."""
        original = _Style(_Element)
        original.Setters.Add(_Setter("Padding", 12))
        original.Setters.Add(_Setter("Foreground", self.white))
        element = self.element(original)
        self.apply(self.window)
        self.assertIs(element.Style.BasedOn, original)
        self.assertIs(element.Style.TargetType, _Element)
        self.assertEqual(element.GetValue("Padding"), 12)
        self.assertIs(element.GetValue("Foreground"), self.black)
        self.assertEqual(len(original.Setters), 2)
        self.assertIs(original.Setters[1].Value, self.white)

    def test_implicit_style_is_preserved_as_basedon(self):
        """An implicitly styled control keeps its theme below the contrast style."""
        implicit = _Style(_Element)
        implicit.Setters.Add(_Setter("Background", _Brush(255, 200, 200)))
        element = self.element(implicit)
        self.apply(self.window)
        self.assertIs(element.Style.BasedOn, implicit)
        self.assertIsNot(element.Style, implicit)
        self.assertEqual(len(implicit.Setters), 1)

    def test_unchanged_brush_reuses_managed_style(self):
        """Repeated passes do not replace a style with the same contrast brush."""
        element = self.element()
        self.apply(self.window)
        original = element.Style
        self.apply(self.window)
        self.assertIs(element.Style, original)
        self.assertIs(self.window._contrast_managed[element], original)

    def test_detached_elements_are_removed_from_tracking(self):
        """A refresh retains only elements still in the logical tree."""
        detached = self.element()
        attached = self.element()
        self.apply(self.window)
        attached_style = attached.Style
        self.window.elements.remove(detached)
        self.apply(self.window)
        self.assertNotIn(detached, self.window._contrast_managed)
        self.assertIs(self.window._contrast_managed[attached], attached_style)

    def test_failed_element_does_not_abort_remaining_elements(self):
        """An inaccessible background is logged without aborting form loading."""
        broken = self.element()

        def fail_get_value(prop):
            raise ValueError("unavailable background")

        broken.GetValue = fail_get_value
        healthy = self.element()
        self.apply(self.window)
        self.assertIsNone(broken.Style)
        self.assertIs(healthy.GetValue("Foreground"), self.black)
        self.assertEqual(len(self.debug_messages), 1)
        self.assertIn("unavailable background", str(self.debug_messages[0][1]))

    def test_refresh_replaces_only_managed_style(self):
        """Theme refresh updates contrast without building a style chain."""
        original = _Style(_Element)
        element = self.element(original)
        self.apply(self.window)
        first_style = element.Style
        element.local["Background"] = _Brush(20, 20, 20)
        self.apply(self.window)
        self.assertIsNot(element.Style, first_style)
        self.assertIs(element.Style.BasedOn, original)
        self.assertIs(element.GetValue("Foreground"), self.white)
        replacement = _Style(_Element)
        element.Style = replacement
        self.apply(self.window)
        self.assertIs(element.Style.BasedOn, replacement)

    def test_explicit_foreground_is_untouched(self):
        """Authored local foregrounds, including later edits, stay authoritative."""
        element = self.element()
        element.local["Foreground"] = self.white
        self.apply(self.window)
        self.assertIsNone(element.Style)
        self.assertIs(element.GetValue("Foreground"), self.white)
        del element.local["Foreground"]
        self.apply(self.window)
        contrast_style = element.Style
        element.local["Foreground"] = self.disabled
        self.apply(self.window)
        self.assertIs(element.Style, contrast_style)
        self.assertIs(element.GetValue("Foreground"), self.disabled)

    def test_dequalified_background_restores_original_style(self):
        """Every excluded background restores the exact pre-contrast style."""
        backgrounds = (
            ("unset", _UNSET),
            ("non-solid", object()),
            ("translucent", _Brush(255, 200, 200, alpha=128)),
            ("theme-colored", _Brush(255, 255, 255)),
        )
        for name, background in backgrounds:
            for original in (None, _Style(_Element)):
                with self.subTest(background=name, original=original):
                    element = self.element(original)
                    self.apply(self.window)
                    self.assertIsNot(element.Style, original)
                    if background is _UNSET:
                        del element.local["Background"]
                    else:
                        element.local["Background"] = background
                    self.apply(self.window)
                    self.assertIs(element.Style, original)
                    self.assertNotIn(element, self.window._contrast_managed)

    def test_local_foreground_keeps_style_when_background_stops_qualifying(self):
        """Authored foregrounds prevent changes even when contrast is no longer needed."""
        backgrounds = (
            ("unset", _UNSET),
            ("non-solid", object()),
            ("translucent", _Brush(255, 200, 200, alpha=128)),
            ("theme-colored", self.white),
        )
        for name, background in backgrounds:
            with self.subTest(background=name):
                element = self.element()
                self.apply(self.window)
                contrast_style = element.Style
                element.local["Foreground"] = self.disabled
                if background is _UNSET:
                    del element.local["Background"]
                else:
                    element.local["Background"] = background
                self.apply(self.window)
                self.assertIs(element.Style, contrast_style)
                self.assertIs(element.GetValue("Foreground"), self.disabled)
                self.assertIs(self.window._contrast_managed[element], contrast_style)
                del element.local["Foreground"]
                self.apply(self.window)
                self.assertIsNone(element.Style)
                self.assertNotIn(element, self.window._contrast_managed)

    def test_dequalification_preserves_replacement_style(self):
        """Removing tracking must not overwrite an externally replaced style."""
        element = self.element()
        self.apply(self.window)
        replacement = _Style(_Element)
        element.Style = replacement
        element.local["Background"] = self.white
        self.apply(self.window)
        self.assertIs(element.Style, replacement)
        self.assertNotIn(element, self.window._contrast_managed)

    def test_theme_and_translucent_backgrounds_are_untouched(self):
        """Existing exclusions do not create unnecessary contrast styles."""
        for background in (self.white, _Brush(255, 200, 200, alpha=128)):
            element = self.element()
            element.local["Background"] = background
        self.apply(self.window)
        for element in self.window.elements:
            self.assertIsNone(element.Style)


if __name__ == "__main__":
    unittest.main()
