#nullable enable
using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;
// using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing and querying installed pyRevit extensions.
    /// </summary>
    public class ExtensionManagerService : IExtensionManagerService
    {
        private readonly int _revitYear;
        private readonly ILogger _logger;
        private List<ParsedExtension>? _cachedExtensions;

        /// <summary>
        /// Initialises the service with the running Revit version year for version-compatibility filtering.
        /// </summary>
        /// <param name="revitYear">
        /// The four-digit Revit release year (e.g. 2024). Pass 0 to disable version filtering.
        /// </param>
        /// <param name="logger">The logger instance.</param>
        public ExtensionManagerService(int revitYear = 0, ILogger? logger = null)
        {
            _revitYear = revitYear;
            _logger = logger ?? new LoggingHelper(null);
        }

        /// <summary>
        /// Gets all parsed extensions (cached).
        /// </summary>
        private List<ParsedExtension> GetAllExtensionsCached()
        {
            if (_cachedExtensions != null)
                return _cachedExtensions;

            ExtensionParser.SetLogger(new ExtensionParserLoggerAdapter(_logger));
            _cachedExtensions = ExtensionParser.ParseInstalledExtensions(_revitYear).ToList();
            return _cachedExtensions;
        }

        /// <summary>
        /// Clears the extension cache, forcing a re-parse on next access.
        /// </summary>
        public void ClearCache()
        {
            _cachedExtensions = null;
        }

        /// <summary>
        /// Clears all parser caches including the static caches in ExtensionParser.
        /// This ensures newly installed or enabled extensions are discovered on reload.
        /// </summary>
        public void ClearParserCaches()
        {
            _cachedExtensions = null;
            ExtensionParser.ClearAllCaches();
        }

        /// <summary>
        /// Gets all installed extensions that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => ext.Config?.Disabled != true);
        }

        /// <summary>
        /// Gets all installed UI extensions (extensions ending with .extension) that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed UI extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledUIExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => ext.Config?.Disabled != true &&
                       ext.Directory.EndsWith(ExtensionConstants.UI_EXTENSION_SUFFIX, System.StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Gets all installed library extensions (extensions ending with .lib) that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed library extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledLibraryExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => ext.Config?.Disabled != true &&
                       ext.Directory.EndsWith(ExtensionConstants.LIBRARY_EXTENSION_SUFFIX, System.StringComparison.OrdinalIgnoreCase));
        }
    }
}