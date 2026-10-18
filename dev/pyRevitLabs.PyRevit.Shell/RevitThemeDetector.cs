using System;
using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Resolves the active Revit UI theme so the shell can match it.
    /// Uses reflection to support Revit versions without dark theme.
    /// </summary>
    /// <remarks>
    /// Revit 2021-2023 report a "Dark" theme while their ribbon and window chrome stay light, so the
    /// shell must keep its light palette on those hosts or it reads as dark-on-dark (#3742).
    /// </remarks>
    internal static class RevitThemeDetector {
        /// <summary>
        /// First Revit year whose UI is genuinely dark under the Dark theme.
        /// </summary>
        internal const int FirstDarkUiYear = 2024;

        public static bool IsDarkTheme(UIApplication uiapp) {
            try {
                if (!SupportsDarkUi(ReadRevitYear(uiapp)))
                    return false;

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

        /// <summary>
        /// Whether the given Revit year renders a genuinely dark UI under the Dark theme.
        /// </summary>
        /// <remarks>
        /// An unknown year (<c>0</c>) is treated as dark-capable, so a host whose version cannot be
        /// read keeps today's behaviour rather than losing its dark theme.
        /// </remarks>
        internal static bool SupportsDarkUi(int revitYear) {
            return revitYear <= 0 || revitYear >= FirstDarkUiYear;
        }

        internal static int ReadRevitYear(UIApplication uiapp) {
            try {
                var application = uiapp?.Application;
                return int.TryParse(application?.VersionNumber, out var year) ? year : 0;
            }
            catch {
                return 0;
            }
        }
    }
}
