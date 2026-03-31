#nullable enable
using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing and querying installed pyRevit extensions.
    /// </summary>
    public class ExtensionManagerService : IExtensionManagerService
    {
        private readonly int _revitYear;
        private List<ParsedExtension>? _cachedExtensions;

        public ExtensionManagerService(int revitYear = 0)
        {
            _revitYear = revitYear;
        }

        /// <summary>
        /// Gets all parsed extensions (cached).
        /// </summary>
        private List<ParsedExtension> GetAllExtensionsCached()
        {
            return _cachedExtensions ??= ExtensionParser.ParseInstalledExtensions(_revitYear).ToList();
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
