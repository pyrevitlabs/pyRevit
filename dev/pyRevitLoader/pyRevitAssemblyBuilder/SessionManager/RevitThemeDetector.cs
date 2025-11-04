using System;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Utility for detecting Revit's UI theme
    /// </summary>
    public static class RevitThemeDetector
    {
        /// <summary>
        /// Detects the current Revit UI theme
        /// </summary>
        /// <returns>True if the current theme is dark, false if light or cannot be determined</returns>
        public static bool IsDarkTheme()
        {
            try
            {
                // Try to use Revit 2024+ UIThemeManager API
                var uiThemeManagerType = Type.GetType("Autodesk.Revit.UI.UIThemeManager, RevitAPIUI");
                if (uiThemeManagerType != null)
                {
                    var currentThemeProperty = uiThemeManagerType.GetProperty("CurrentTheme", 
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                    
                    if (currentThemeProperty != null)
                    {
                        var currentTheme = currentThemeProperty.GetValue(null);
                        
                        // Get the UITheme enum type to compare against
                        var uiThemeType = Type.GetType("Autodesk.Revit.UI.UITheme, RevitAPIUI");
                        if (uiThemeType != null)
                        {
                            // Get the Dark enum value
                            var darkThemeValue = Enum.Parse(uiThemeType, "Dark");
                            
                            // Compare the current theme with Dark theme
                            var isDark = currentTheme.Equals(darkThemeValue);
                            
                            Console.WriteLine($"Revit theme detected: {currentTheme} -> isDark: {isDark}");
                            return isDark;
                        }
                        else
                        {
                            // Fallback: try string comparison if we can't get the enum type
                            var themeString = currentTheme.ToString();
                            var isDark = themeString.Contains("Dark");
                            Console.WriteLine($"Revit theme detected via string: {themeString} -> isDark: {isDark}");
                            return isDark;
                        }
                    }
                }
                
                // Fallback: Try to detect theme through system settings or other methods
                Console.WriteLine("UIThemeManager not available, falling back to light theme");
                return false;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error detecting Revit theme: {ex.Message}");
                // Default to light theme if detection fails
                return false;
            }
        }
        
        /// <summary>
        /// Gets a string representation of the current theme
        /// </summary>
        public static string GetThemeName()
        {
            return IsDarkTheme() ? "Dark" : "Light";
        }
    }
}