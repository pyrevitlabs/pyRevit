using System;
using System.IO;

namespace pyRevitCLI {
    /// <summary>
    /// Detects links and junctions (reparse points) on a path and on its ancestors.
    /// </summary>
    /// <remarks>
    /// Note: the answer holds at the time of the call; it does not stop a link from being
    /// swapped in before the path is used. Same semantics as the runtime's workspace check:
    /// any existing path component that reports the reparse attribute (junction, symlink, mount
    /// point) counts. Cloud placeholder folders, such as a OneDrive root, do not report it to
    /// this process and are not detected.
    /// </remarks>
    internal static class ReparsePoints {
        /// <summary>
        /// Whether an existing file or folder is itself a link or junction.
        /// </summary>
        public static bool IsLink(string path) {
            return (File.Exists(path) || Directory.Exists(path))
                && (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0;
        }

        /// <summary>
        /// The first path, from <paramref name="path"/> upward, that is a link or junction, or null.
        /// </summary>
        /// <param name="path">A file or folder; a path that does not exist is walked from its parent.</param>
        /// <param name="boundary">When set, the walk stops after this ancestor.</param>
        public static string FindLink(string path, string boundary = null) {
            var stop = boundary == null ? null : Trim(Path.GetFullPath(boundary));
            for (var current = Path.GetFullPath(path); current != null; current = Path.GetDirectoryName(current)) {
                if (IsLink(current))
                    return current;
                if (stop != null && string.Equals(Trim(current), stop, StringComparison.OrdinalIgnoreCase))
                    return null;
            }
            return null;
        }

        private static string Trim(string path) {
            return path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        }
    }
}
