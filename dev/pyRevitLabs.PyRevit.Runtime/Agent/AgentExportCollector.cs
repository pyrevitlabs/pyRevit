using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Lists the files a guarded run left in its export folder, for the run's <c>exports</c>.
    /// </summary>
    /// <remarks>
    /// Subfolders are listed too, except links, since <see cref="AgentExportFolder"/> refuses
    /// exports through them. The folder is removed when it holds nothing, so run records
    /// without exports stay as they were; a folder with any entry, even an empty subfolder,
    /// is kept.
    /// </remarks>
    internal static class AgentExportCollector {
        /// <summary>
        /// Returns the full paths of the exported files, sorted ignoring case, or none when the
        /// folder doesn't exist.
        /// </summary>
        public static string[] Collect(string exportDir) {
            if (!Directory.Exists(exportDir))
                return new string[0];
            var files = ListFilesOutsideLinks(exportDir).OrderBy(file => file, StringComparer.OrdinalIgnoreCase).ToArray();
            if (Directory.GetFileSystemEntries(exportDir).Length == 0)
                Directory.Delete(exportDir);
            return files;
        }

        private static IEnumerable<string> ListFilesOutsideLinks(string folder) {
            var subfolders = Directory.GetDirectories(folder)
                .Where(subfolder => !new DirectoryInfo(subfolder).Attributes.HasFlag(FileAttributes.ReparsePoint));
            return Directory.GetFiles(folder).Concat(subfolders.SelectMany(ListFilesOutsideLinks));
        }
    }
}
