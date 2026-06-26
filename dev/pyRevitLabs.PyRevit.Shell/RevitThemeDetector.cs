using System;
using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Resolves the active Revit UI theme so the shell can match it instead of always
    /// rendering dark. <c>UIThemeManager</c> only exists in Revit 2024 and newer, and this
    /// assembly is referenced against older Revit API versions too, so the type is reached by
    /// reflection. Revit releases that predate the dark theme fall back to light.
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

                // UITheme is an enum; compare by name to stay decoupled from the API version.
                return string.Equals(theme.ToString(), "Dark", StringComparison.Ordinal);
            }
            catch {
                // Any reflection/API mismatch means the running Revit has no dark theme support.
                return false;
            }
        }
    }
}
