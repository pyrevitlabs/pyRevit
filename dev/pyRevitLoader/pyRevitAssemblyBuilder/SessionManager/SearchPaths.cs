using System;
using System.Collections.Generic;
using System.Linq;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Shared rules for the module search paths the loader hands to a script engine.
    /// Every runtime the loader starts - a generated command, an extension startup
    /// script, a session entry script, an event hook - resolves modules through a
    /// list assembled the same way, so the dedupe rule lives here rather than being
    /// restated per call site. #3687.
    /// </summary>
    internal static class SearchPaths
    {
        /// <summary>
        /// Collapses repeated folders, keeping the earliest occurrence.
        /// </summary>
        /// <param name="paths">The assembled search-path list, in priority order.</param>
        /// <returns>The same folders in the same order, without repeats.</returns>
        /// <remarks>
        /// The sources that feed a search-path list overlap by design and are not
        /// individually aware of each other: an extension contributes its own folder
        /// and its nested lib/, a bundle sits inside both its panel and its
        /// extension, the collected binary paths always end with the script's own
        /// directory, and the core folders are appended unconditionally. Each
        /// collector dedupes only within itself, so the overlap has to be resolved
        /// once the list is assembled.
        ///
        /// <b>Invariant:</b> order is the module-resolution priority, so a later
        /// duplicate must never displace an earlier entry. Comparison is
        /// case-insensitive because Windows paths are, and a folder differing only
        /// in case would otherwise be scanned twice.
        /// </remarks>
        public static IEnumerable<string> DedupeKeepingFirstOccurrence(IEnumerable<string> paths) =>
            paths.Where(p => !string.IsNullOrEmpty(p))
                 .Distinct(StringComparer.OrdinalIgnoreCase);
    }
}
