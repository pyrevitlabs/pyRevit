using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

using Microsoft.Win32.SafeHandles;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The host-owned folder a guarded run may export Revit files into, and the check that
    /// decides whether an export target lies inside it.
    /// </summary>
    /// <remarks>
    /// A guard against an agent's mistakes, not a sandbox: the script runs with the user's
    /// rights and can still write files by other means.
    /// Invariant: <see cref="Contains"/> fails closed. A target that is not a fully qualified
    /// drive or UNC path (device paths included), or whose deepest existing part doesn't
    /// resolve, is outside. A UNC target only matches a folder resolved through the same share.
    /// Invariant: the folder is resolved once, when this object is created before the script
    /// runs, and targets are compared by their resolved final path, so links, short names
    /// and a folder the script swaps for a link afterwards can't move where exports land.
    /// </remarks>
    internal sealed class AgentExportFolder {
        private readonly string resolvedFolder;

        public AgentExportFolder(string folder) {
            resolvedFolder = ResolveExisting(folder);
        }

        /// <summary>
        /// The folder as scripts get it in <c>export_dir</c>: with one trailing separator, so
        /// <c>ImageExportOptions.FilePath = export_dir</c> writes inside it. Revit treats a
        /// <c>FilePath</c> without one as a file name prefix and would write beside the folder.
        /// </summary>
        public static string ForScripts(string folder) {
            return folder.TrimEnd('\\', '/') + Path.DirectorySeparatorChar;
        }

        /// <summary>
        /// True when <paramref name="target"/>, a file, file name prefix or folder as Revit
        /// reports it in <c>FileExportingEventArgs.Path</c>, is the folder or lies inside it.
        /// </summary>
        public bool Contains(string target) {
            if (resolvedFolder == null || !IsFullyQualified(target))
                return false;
            string fullPath;
            try {
                fullPath = Path.GetFullPath(target);
            }
            catch (Exception) {
                return false;
            }
            var resolved = ResolveExisting(DeepestExisting(fullPath));
            return resolved != null
                && (string.Equals(resolved, resolvedFolder, StringComparison.OrdinalIgnoreCase)
                    || resolved.StartsWith(resolvedFolder + "\\", StringComparison.OrdinalIgnoreCase));
        }

        private static bool IsFullyQualified(string path) {
            if (path == null || path.Length < 3)
                return false;
            if (IsSeparator(path[0]) && IsSeparator(path[1]))
                return path[2] != '?' && path[2] != '.' && !IsSeparator(path[2]);
            return char.IsLetter(path[0]) && path[1] == ':' && IsSeparator(path[2]);
        }

        private static bool IsSeparator(char character) {
            return character == '\\' || character == '/';
        }

        private static string DeepestExisting(string fullPath) {
            var current = fullPath;
            while (!string.IsNullOrEmpty(current)) {
                if (File.Exists(current) || Directory.Exists(current))
                    return current;
                current = Path.GetDirectoryName(current);
            }
            return null;
        }

        private static string ResolveExisting(string path) {
            if (string.IsNullOrEmpty(path))
                return null;
            try {
                using (var handle = CreateFile(path, 0, FileShareAll, IntPtr.Zero, OpenExisting, BackupSemantics, IntPtr.Zero)) {
                    if (handle.IsInvalid)
                        return null;
                    var buffer = new StringBuilder(512);
                    var length = GetFinalPathNameByHandle(handle, buffer, buffer.Capacity, 0);
                    if (length >= buffer.Capacity) {
                        buffer = new StringBuilder(length + 1);
                        length = GetFinalPathNameByHandle(handle, buffer, buffer.Capacity, 0);
                    }
                    if (length <= 0 || length >= buffer.Capacity)
                        return null;
                    return buffer.ToString().TrimEnd('\\');
                }
            }
            catch (Exception) {
                return null;
            }
        }

        private const uint FileShareAll = 0x1 | 0x2 | 0x4;
        private const uint OpenExisting = 3;
        private const uint BackupSemantics = 0x02000000;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern SafeFileHandle CreateFile(
            string fileName, uint desiredAccess, uint shareMode, IntPtr securityAttributes,
            uint creationDisposition, uint flagsAndAttributes, IntPtr templateFile);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern int GetFinalPathNameByHandle(
            SafeFileHandle file, StringBuilder filePath, int filePathLength, uint flags);
    }
}
