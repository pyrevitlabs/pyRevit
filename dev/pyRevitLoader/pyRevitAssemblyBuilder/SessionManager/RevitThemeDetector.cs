using System;
using System.Reflection;

using Autodesk.Revit.UI;

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
    /// <para>
    /// Note: Revit 2021-2023 expose <c>UIThemeManager.CurrentTheme</c> and report "Dark", but their
    /// ribbon button bar stays light, so <see cref="IconManager"/> must keep the light assets there
    /// or the icons become invisible (#3742). The host year is read once from the running host and
    /// gates every consumer.
    /// </para>
    /// </remarks>
    public class RevitThemeDetector
    {
        private const string ThemeManagerTypeName = "Autodesk.Revit.UI.UIThemeManager";
        private const string CurrentThemePropertyName = "CurrentTheme";
        private const string DarkThemeName = "Dark";
        private const string LightThemeName = "Light";

        /// <summary>
        /// First Revit year whose ribbon button bar is dark when the host theme is Dark.
        /// </summary>
        public const int FirstDarkRibbonYear = 2024;

        private readonly ILogger _logger;
        private readonly Func<string> _themeNameReader;
        private readonly Func<int> _revitYearReader;
        private static bool? _cachedTheme;
        private static bool _themeDetected;
        private static int? _cachedRevitYear;

        public RevitThemeDetector(ILogger logger)
            : this(logger, ReadCurrentThemeName, null)
        {
        }

        internal RevitThemeDetector(ILogger logger, Func<string> themeNameReader, Func<int> revitYearReader = null)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _themeNameReader = themeNameReader ?? throw new ArgumentNullException(nameof(themeNameReader));
            _revitYearReader = revitYearReader;
        }

        /// <summary>
        /// Resolves the running host's UI theme, treating a host with no theme API and a failed
        /// lookup alike as light rather than propagating either.
        /// </summary>
        /// <remarks>
        /// Returns <c>false</c> unconditionally on Revit 2021-2023: those hosts report "Dark" but keep
        /// a light ribbon, so dark assets would be invisible (#3742).
        /// </remarks>
        public bool IsDarkTheme()
        {
            if (!SupportsDarkRibbon(_revitYearReader != null ? _revitYearReader() : HostRevitYear()))
                return Cache(false);

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
        /// Resolves the theme Revit reported into the one pyRevit's ribbon assets should be built
        /// for, honouring the host-version gate.
        /// </summary>
        /// <remarks>
        /// Used by the loader's live theme-change refresh, which receives a theme name from Revit
        /// rather than from a detector instance. Returns <c>false</c> on Revit 2021-2023 (#3742).
        /// </remarks>
        /// <param name="themeName">Theme name as reported by Revit, for example "Dark" or "Light".</param>
        /// <returns>Whether pyRevit ribbon assets should use their dark variants.</returns>
        public static bool IsDarkRibbonTheme(string themeName)
        {
            return IsDarkRibbonThemeFor(themeName, HostRevitYear());
        }

        /// <summary>
        /// Resolves the theme Revit reported into the one pyRevit's ribbon assets should be built
        /// for, for an explicit host year.
        /// </summary>
        /// <param name="themeName">Theme name as reported by Revit, for example "Dark" or "Light".</param>
        /// <param name="revitYear">Running Revit year, or <c>0</c> when unknown.</param>
        /// <returns>Whether pyRevit ribbon assets should use their dark variants.</returns>
        public static bool IsDarkRibbonThemeFor(string themeName, int revitYear)
        {
            if (!SupportsDarkRibbon(revitYear))
                return false;
            return string.Equals(themeName, DarkThemeName, StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// Whether the given Revit year renders its ribbon button bar dark under the Dark theme.
        /// </summary>
        /// <remarks>
        /// An unknown year (<c>0</c>) is treated as supporting dark icons, so a host whose version
        /// cannot be read keeps today's behaviour rather than losing dark icons.
        /// </remarks>
        /// <param name="revitYear">Running Revit year, or <c>0</c> when unknown.</param>
        public static bool SupportsDarkRibbon(int revitYear)
        {
            return revitYear <= 0 || revitYear >= FirstDarkRibbonYear;
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

        /// <summary>
        /// Records the running host's Revit year, which gates the whole theme resolution.
        /// </summary>
        /// <remarks>
        /// Invariant: must be called with a live <c>UIApplication</c> before any theme decision.
        /// The loader and <c>SessionManagerService</c> both hold one, so the year is read directly
        /// from <c>uiApp.Application.VersionNumber</c> rather than reflected. There is no
        /// dependable static route to a live <c>UIApplication</c>: the non-public static
        /// <c>UIApplication.Instance</c> exists on Revit 2027 but not on 2021-2026, and reading
        /// <c>Application</c> as a static yields null because it is an instance property. Either
        /// mistake leaves the year unknown, and an unknown year is treated as dark-capable - which
        /// would silently re-open #3742 on exactly the versions the gate exists for.
        /// <para>
        /// Never throws: reading <c>Application</c> can fail while the host is shutting down, and
        /// this runs on the startup path where an exception would abort the session load. A failed
        /// read records an unknown year, which the gate treats as dark-capable.
        /// </para>
        /// </remarks>
        /// <param name="uiApplication">The running Revit <c>UIApplication</c>.</param>
        public static void SetHostRevitYear(UIApplication uiApplication)
        {
            try
            {
                _cachedRevitYear = ParseRevitYear(uiApplication?.Application?.VersionNumber);
            }
            catch (Exception)
            {
                _cachedRevitYear = 0;
            }
        }

        /// <summary>
        /// Records the running host's Revit year from its version string.
        /// </summary>
        /// <param name="versionNumber">
        /// Revit's <c>VersionNumber</c>, for example "2024". Anything unparsable records an unknown
        /// year, which the gate treats as dark-capable.
        /// </param>
        internal static void SetHostRevitYearFromVersion(string versionNumber)
        {
            _cachedRevitYear = ParseRevitYear(versionNumber);
        }

        /// <summary>
        /// Parses a Revit <c>VersionNumber</c> into a year, returning <c>0</c> when it cannot be
        /// read.
        /// </summary>
        internal static int ParseRevitYear(string versionNumber)
        {
            return int.TryParse(versionNumber, out var year) ? year : 0;
        }

        /// <summary>
        /// The running host's Revit year, recorded at session start. Returns <c>0</c> before it has
        /// been recorded, which is treated as dark-capable.
        /// </summary>
        /// <remarks>
        /// The host cannot change version without restarting, so this is deliberately not cleared
        /// by <see cref="ClearCache"/>.
        /// </remarks>
        public static int HostRevitYear()
        {
            return _cachedRevitYear ?? 0;
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
