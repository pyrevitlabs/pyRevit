#nullable enable
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Panels
{
    /// <summary>
    /// Panel background colors that apply to one Revit UI theme.
    /// </summary>
    /// <remarks>
    /// A null member means the area keeps the stock Revit background.
    /// </remarks>
    public sealed class PanelBackgroundColors
    {
        /// <summary>
        /// Color painted on the panel body, its title bar and its slideout.
        /// </summary>
        public string? Panel { get; set; }

        /// <summary>
        /// Color painted on the panel title bar, overriding <see cref="Panel"/>.
        /// </summary>
        public string? Title { get; set; }

        /// <summary>
        /// Color painted on the panel slideout, overriding <see cref="Panel"/>.
        /// </summary>
        public string? Slideout { get; set; }

        /// <summary>
        /// Whether any area carries a color.
        /// </summary>
        public bool IsEmpty =>
            string.IsNullOrEmpty(Panel)
            && string.IsNullOrEmpty(Title)
            && string.IsNullOrEmpty(Slideout);
    }

    /// <summary>
    /// Maps the <c>background</c> and <c>background_dark</c> bundle sections onto the active theme.
    /// </summary>
    public static class PanelBackgroundResolver
    {
        /// <summary>
        /// Whether the component declares a background color for either theme.
        /// </summary>
        public static bool HasBackgroundColors(ParsedComponent? component)
        {
            if (component == null)
                return false;

            return !string.IsNullOrEmpty(component.PanelBackground)
                || !string.IsNullOrEmpty(component.TitleBackground)
                || !string.IsNullOrEmpty(component.SlideoutBackground)
                || !string.IsNullOrEmpty(component.DarkPanelBackground)
                || !string.IsNullOrEmpty(component.DarkTitleBackground)
                || !string.IsNullOrEmpty(component.DarkSlideoutBackground);
        }

        /// <summary>
        /// Resolves the colors a panel is painted with under the supplied theme.
        /// </summary>
        /// <remarks>
        /// Each area falls back to its <c>background</c> color when <c>background_dark</c> leaves that
        /// area unset, so a bundle can override a single area for dark theme. A bundle that declares
        /// colors for dark theme only paints nothing in light theme.
        /// </remarks>
        /// <param name="component">The panel component carrying the parsed colors.</param>
        /// <param name="isDarkTheme">True when the Revit UI theme is dark.</param>
        public static PanelBackgroundColors Resolve(ParsedComponent? component, bool isDarkTheme)
        {
            if (component == null)
                return new PanelBackgroundColors();

            return new PanelBackgroundColors
            {
                Panel = SelectThemeColor(component.PanelBackground, component.DarkPanelBackground, isDarkTheme),
                Title = SelectThemeColor(component.TitleBackground, component.DarkTitleBackground, isDarkTheme),
                Slideout = SelectThemeColor(component.SlideoutBackground, component.DarkSlideoutBackground, isDarkTheme),
            };
        }

        private static string? SelectThemeColor(string? lightColor, string? darkColor, bool isDarkTheme)
        {
            if (isDarkTheme && !string.IsNullOrEmpty(darkColor))
                return darkColor;

            return lightColor;
        }
    }
}
