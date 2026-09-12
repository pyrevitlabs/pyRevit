using System;
using System.Reflection;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Single source of truth for the UI theme that ribbon icons and smart buttons render against.
    /// </summary>
    /// <remarks>
    /// Invariant: the theme is resolved reflectively, never through a compile-time Revit API
    /// reference or a <c>#if REVIT20xx</c> switch. pyRevitAssemblyBuilder is version-agnostic - one
    /// net48 build serves Revit 2021-2024, one net8.0 build serves Revit 2025+ - so a compile-time
    /// switch resolves against each target framework's baseline version instead of the running host.
    /// That is how Revit 2024 came to report Light unconditionally despite supporting dark theme
    /// (#3628).
    /// <para>
    /// Important: the resolved theme is cached for the lifetime of the process, not per instance,
    /// so every instance observes the same value until <see cref="ClearCache"/> runs.
    /// </para>
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
        /// Resolves the running host's UI theme, treating a host with no theme API and a failed
        /// lookup alike as light rather than propagating either.
        /// </summary>
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
        /// Names the theme the way Revit's own <c>UITheme</c> does, as "Dark" or "Light", so the
        /// value round-trips against theme strings coming off the Revit API.
        /// </summary>
        public string GetThemeName()
        {
            return IsDarkTheme() ? DarkThemeName : LightThemeName;
        }

        /// <summary>
        /// Drops the cached theme so the next lookup re-queries the host.
        /// </summary>
        /// <remarks>
        /// Invariant: must run on every session load. Revit changes theme without restarting the
        /// process, and a cache left stale across a reload repaints the whole ribbon with the
        /// previous theme's icons.
        /// </remarks>
        public static void ClearCache()
        {
            _cachedTheme = null;
            _themeDetected = false;
        }

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
