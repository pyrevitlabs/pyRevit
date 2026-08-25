using System;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Utility for detecting Revit's UI theme.
    /// </summary>
    public class RevitThemeDetector
    {
        private readonly ILogger _logger;
        private static bool? _cachedTheme;
        private static bool _themeDetected;

        public RevitThemeDetector(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// Detects the current Revit UI theme (cached after first call).
        /// </summary>
        /// <returns>True if the current theme is dark, false if light or cannot be determined</returns>
        public bool IsDarkTheme()
        {
            // Return cached result if available
            if (_themeDetected)
                return _cachedTheme ?? false;
                
            try
            {
#if (REVIT2019 || REVIT2020 || REVIT2021 || REVIT2022 || REVIT2023)
                // UIThemeManager not available before Revit 2024
                _cachedTheme = false;
                _themeDetected = true;
                return false;
#else
                // Use Revit 2024+ UIThemeManager API directly
                var currentTheme = Autodesk.Revit.UI.UIThemeManager.CurrentTheme;
                var isDark = currentTheme == Autodesk.Revit.UI.UITheme.Dark;
                _cachedTheme = isDark;
                _themeDetected = true;
                _logger.Debug($"Revit theme detected: {currentTheme} -> isDark: {isDark}");
                return isDark;
#endif
            }
            catch (Exception ex)
            {
                _logger.Error($"Error detecting Revit theme: {ex.Message}");
                _cachedTheme = false;
                _themeDetected = true;
                return false;
            }
        }
        
        /// <summary>
        /// Gets a string representation of the current theme
        /// </summary>
        public string GetThemeName()
        {
            return IsDarkTheme() ? "Dark" : "Light";
        }
        
        /// <summary>
        /// Clears the cached theme (call if user changes theme mid-session).
        /// </summary>
        public static void ClearCache()
        {
            _cachedTheme = null;
            _themeDetected = false;
        }
    }
}