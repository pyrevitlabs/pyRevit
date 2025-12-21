using System;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Utility for detecting Revit's UI theme
    /// </summary>
    public class RevitThemeDetector
    {
        private readonly LoggingHelper _logger;

        public RevitThemeDetector(object pythonLogger)
        {
            _logger = new LoggingHelper(pythonLogger ?? throw new ArgumentNullException(nameof(pythonLogger)));
        }

        /// <summary>
        /// Detects the current Revit UI theme
        /// </summary>
        /// <returns>True if the current theme is dark, false if light or cannot be determined</returns>
        public bool IsDarkTheme()
        {
            try
            {
#if (REVIT2019 || REVIT2020 || REVIT2021 || REVIT2022 || REVIT2023)
                // UIThemeManager not available before Revit 2024
                _logger.Debug("UIThemeManager not available in this Revit version, falling back to light theme");
                return false;
#else
                // Use Revit 2024+ UIThemeManager API directly
                var currentTheme = Autodesk.Revit.UI.UIThemeManager.CurrentTheme;
                var isDark = currentTheme == Autodesk.Revit.UI.UITheme.Dark;
                _logger.Debug($"Revit theme detected: {currentTheme} -> isDark: {isDark}");
                return isDark;
#endif
            }
            catch (Exception ex)
            {
                _logger.Error($"Error detecting Revit theme: {ex.Message}");
                // Default to light theme if detection fails
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
    }
}