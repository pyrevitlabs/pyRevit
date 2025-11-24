using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing and querying installed pyRevit extensions.
    /// </summary>
    public class ExtensionManagerService
    {
        /// <summary>
        /// Gets all installed extensions that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();
            return installedExtensions.Where(ext => ext.Config?.Disabled != true);
        }

        /// <summary>
        /// Gets all installed UI extensions (extensions ending with .extension) that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed UI extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledUIExtensions()
        {
            return ExtensionParser.ParseInstalledExtensions()
                .Where(ext => ext.Config?.Disabled != true && ext.Directory.EndsWith(".extension", System.StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Gets all installed library extensions (extensions ending with .lib) that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed library extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledLibraryExtensions()
        {
            return ExtensionParser.ParseInstalledExtensions()
                .Where(ext => ext.Config?.Disabled != true && ext.Directory.EndsWith(".lib", System.StringComparison.OrdinalIgnoreCase));
        }
    }
}
