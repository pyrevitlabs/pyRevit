#nullable enable
using System.Collections.Generic;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Interface for managing and querying installed pyRevit extensions.
    /// </summary>
    public interface IExtensionManagerService
    {
        /// <summary>
        /// Clears the extension cache, forcing a re-parse on next access.
        /// </summary>
        void ClearCache();

        /// <summary>
        /// Gets all installed extensions that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed extensions.</returns>
        IEnumerable<ParsedExtension> GetInstalledExtensions();

        /// <summary>
        /// Gets all installed UI extensions (extensions ending with .extension) that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed UI extensions.</returns>
        IEnumerable<ParsedExtension> GetInstalledUIExtensions();

        /// <summary>
        /// Gets all installed library extensions (extensions ending with .lib) that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed library extensions.</returns>
        IEnumerable<ParsedExtension> GetInstalledLibraryExtensions();
    }
}
