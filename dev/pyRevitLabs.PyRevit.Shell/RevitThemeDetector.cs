using System;
using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Resolves the active Revit UI theme so the shell can match it.
    /// Uses reflection to support Revit versions without dark theme.
    /// </summary>
    internal static class RevitThemeDetector {
        public static bool IsDarkTheme(UIApplication uiapp) {
            try {
                var themeManagerType = Type.GetType("Autodesk.Revit.UI.UIThemeManager, RevitAPIUI");
                if (themeManagerType == null)
                    return false;

                var currentThemeProp = themeManagerType.GetProperty("CurrentTheme");
                if (currentThemeProp == null)
                    return false;

                var theme = currentThemeProp.GetValue(null, null);
                if (theme == null)
                    return false;

                return string.Equals(theme.ToString(), "Dark", StringComparison.Ordinal);
            }
            catch {
                // The running Revit has no dark theme support.
                return false;
            }
        }
    }
}
