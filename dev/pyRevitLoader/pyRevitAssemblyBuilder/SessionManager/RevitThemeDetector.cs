using System;
using System.Reflection;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Utility for detecting Revit's UI theme.
    /// </summary>
    /// <remarks>
    /// The theme is read reflectively from the loaded RevitAPIUI assembly instead of through a
    /// compile-time reference, because pyRevitAssemblyBuilder is version-agnostic: a single net48
    /// build serves Revit 2021-2024 and a single net8.0 build serves Revit 2025+. A compile-time
    /// switch on the baseline Revit version of each target framework reported Light unconditionally
    /// on Revit 2024, which does support the dark theme (issue #3628).
    /// </remarks>
    public class RevitThemeDetector
    {
        private const string ThemeManagerTypeName = "Autodesk.Revit.UI.UIThemeManager";
        private const string CurrentThemePropertyName = "CurrentTheme";
        private const string DarkThemeName = "Dark";
        private const string LightThemeName = "Light";

        private readonly ILogger _logger;
        private readonly Func<string> _themeNameReader;
        private static bool? _cachedTheme;
        private static bool _themeDetected;

        public RevitThemeDetector(ILogger logger)
            : this(logger, ReadCurrentThemeName)
        {
        }

        internal RevitThemeDetector(ILogger logger, Func<string> themeNameReader)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _themeNameReader = themeNameReader ?? throw new ArgumentNullException(nameof(themeNameReader));
        }

        /// <summary>
        /// Detects the current Revit UI theme (cached after first call).
        /// </summary>
        /// <returns>True if the current theme is dark, false if light or cannot be determined</returns>
        public bool IsDarkTheme()
        {
            if (_themeDetected)
                return _cachedTheme ?? false;

            try
            {
                var themeName = _themeNameReader();
                var isDark = string.Equals(themeName, DarkThemeName, StringComparison.OrdinalIgnoreCase);
                _logger.Debug($"Revit theme detected: {themeName ?? "Unknown"} -> isDark: {isDark}");
                return Cache(isDark);
            }
            catch (Exception ex)
            {
                _logger.Error($"Error detecting Revit theme: {ex.Message}");
                return Cache(false);
            }
        }

        /// <summary>
        /// Gets a string representation of the current theme
        /// </summary>
        public string GetThemeName()
        {
            return IsDarkTheme() ? DarkThemeName : LightThemeName;
        }

        /// <summary>
        /// Clears the cached theme (call if user changes theme mid-session).
        /// </summary>
        public static void ClearCache()
        {
            _cachedTheme = null;
            _themeDetected = false;
        }

        /// <summary>
        /// Reads <c>UIThemeManager.CurrentTheme</c> from the RevitAPIUI assembly backing
        /// <paramref name="revitUiApplicationType"/>.
        /// </summary>
        /// <returns>The theme name, or null on a Revit version without UI theme support.</returns>
        internal static string ReadCurrentThemeName(Type revitUiApplicationType)
        {
            var themeManagerType = revitUiApplicationType?.Assembly.GetType(ThemeManagerTypeName);
            var currentThemeProperty = themeManagerType?.GetProperty(
                CurrentThemePropertyName,
                BindingFlags.Public | BindingFlags.Static);
            return currentThemeProperty?.GetValue(null)?.ToString();
        }

        private static string ReadCurrentThemeName()
        {
            return ReadCurrentThemeName(typeof(Autodesk.Revit.UI.UIApplication));
        }

        private static bool Cache(bool isDarkTheme)
        {
            _cachedTheme = isDarkTheme;
            _themeDetected = true;
            return isDarkTheme;
        }
    }
}
