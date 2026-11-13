using System;
using System.IO;

namespace pyRevitCLI {
    internal static class PyRevitCloneLocation {
        /// <summary>
        /// Tells whether <paramref name="path"/> is <paramref name="root"/> or lies below it. Compares
        /// full paths, ignoring case, at directory boundaries, so <c>C:\pyrevit2\bin</c> is not inside <c>C:\pyrevit</c>.
        /// </summary>
        internal static bool IsInside(string path, string root) {
            var fullPath = Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            if (fullPath.Equals(fullRoot, StringComparison.OrdinalIgnoreCase))
                return true;
            return fullPath.StartsWith(fullRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
        }
    }
}
