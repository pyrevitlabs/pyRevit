using System;
using System.IO;

namespace pyRevitCLI {
    internal static class PyRevitCloneLocation {
        /// <summary>
        /// Tells whether <paramref name="path"/> is <paramref name="root"/> or lies below it. Compares
        /// full paths, ignoring case, at directory boundaries, so <c>C:\pyrevit2\bin</c> is not inside <c>C:\pyrevit</c>.
        /// Returns <c>false</c> when either path is null, empty or not a valid path, so one malformed clone
        /// entry can't fail a command that checks every registered clone.
        /// </summary>
        internal static bool IsInside(string path, string root) {
            if (string.IsNullOrWhiteSpace(path) || string.IsNullOrWhiteSpace(root))
                return false;
            try {
                return IsInsideFullPaths(Path.GetFullPath(path), Path.GetFullPath(root));
            }
            catch (Exception ex) when (ex is ArgumentException || ex is NotSupportedException || ex is PathTooLongException) {
                return false;
            }
        }

        private static bool IsInsideFullPaths(string path, string root) {
            var fullPath = path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var fullRoot = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            if (fullPath.Equals(fullRoot, StringComparison.OrdinalIgnoreCase))
                return true;
            return fullPath.StartsWith(fullRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
        }
    }
}
