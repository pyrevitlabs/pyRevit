using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitDoctor {
    /// <summary>
    /// The well-known folders the purge targets are derived from.
    /// </summary>
    public sealed class MachineLocations {
        public string AppData { get; init; }
        public string LocalAppData { get; init; }
        public string ProgramFiles { get; init; }
        public string ProgramData { get; init; }
        public string Documents { get; init; }

        /// <summary>Resolves the folders for the user and machine the process runs as.</summary>
        public static MachineLocations FromEnvironment() => new() {
            AppData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            LocalAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            ProgramFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            ProgramData = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
            Documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        };
    }

    /// <summary>
    /// The exact paths <c>purge-files</c> may delete, derived from where the shipped installers put things.
    /// </summary>
    /// <remarks>
    /// Invariant: the purge deletes only what these members return, never a wildcard or a path built from
    /// user input. Directories are additionally gated by <see cref="HasPyRevitMarker"/>.
    /// </remarks>
    public static class PurgeTargets {
        public const string ConfigFileName = "pyRevit_config.ini";
        public const string AddinFileName = "pyRevit.addin";
        const int FirstProgramFilesManifestYear = 2027;
        static readonly string[] DirectoryMarkers = { "pyRevitfile", Path.Combine("bin", "pyrevit.exe"), ConfigFileName };

        /// <summary>
        /// Install folders of the per-user and all-users pyRevit and pyRevit CLI installers.
        /// </summary>
        public static IReadOnlyList<string> InstallDirectories(MachineLocations locations) => new[] {
            Path.Combine(locations.AppData, "pyRevit-Master"),
            Path.Combine(locations.ProgramFiles, "pyRevit-Master"),
            Path.Combine(locations.ProgramFiles, "pyRevit CLI"),
            Path.Combine(locations.LocalAppData, "Programs", "pyRevit CLI"),
        };

        /// <summary>
        /// Per-user and all-users data folders holding configs and caches.
        /// </summary>
        public static IReadOnlyList<string> DataDirectories(MachineLocations locations) => new[] {
            Path.Combine(locations.AppData, "pyRevit"),
            Path.Combine(locations.ProgramData, "pyRevit"),
        };

        /// <summary>
        /// <c>pyRevit.addin</c> paths for every Revit year folder found under the add-in roots.
        /// </summary>
        /// <remarks>
        /// All-users manifests live under ProgramData up to Revit 2026 and under ProgramFiles from Revit 2027.
        /// Years come from the folders on disk so manifests of clones that no longer exist are found too.
        /// </remarks>
        public static IReadOnlyList<string> AddinManifests(MachineLocations locations, Func<string, IEnumerable<string>> listSubdirectories) {
            var roots = new (string Root, int FirstYear)[] {
                (locations.AppData, 0),
                (locations.ProgramData, 0),
                (locations.ProgramFiles, FirstProgramFilesManifestYear),
            };
            var manifests = new List<string>();
            foreach (var (root, firstYear) in roots) {
                var addinsFolder = Path.Combine(root, "Autodesk", "Revit", "Addins");
                foreach (var yearFolder in listSubdirectories(addinsFolder)) {
                    if (int.TryParse(Path.GetFileName(yearFolder), out var year) && year >= firstYear)
                        manifests.Add(Path.Combine(addinsFolder, year.ToString(), AddinFileName));
                }
            }
            return manifests;
        }

        /// <summary>
        /// True when the folder contains <c>pyRevitfile</c>, <c>bin\pyrevit.exe</c> or <c>pyRevit_config.ini</c>.
        /// </summary>
        public static bool HasPyRevitMarker(string directory, Func<string, bool> fileExists) =>
            DirectoryMarkers.Any(marker => fileExists(Path.Combine(directory, marker)));

        /// <summary>
        /// Removes the entries of a <c>PATH</c> value that point at <c>bin</c> under one of the install folders.
        /// </summary>
        /// <param name="expand">Expands <c>%VAR%</c> references, so unexpanded registry values compare correctly.</param>
        /// <returns>The new value; entries that do not match are kept verbatim and in order.</returns>
        public static string RemoveBinEntries(
            string pathValue,
            Func<string, string> expand,
            IEnumerable<string> installDirectories,
            out IReadOnlyList<string> removedEntries) {
            var binDirectories = installDirectories.Select(dir => NormalizeDirectory(Path.Combine(dir, "bin"))).ToHashSet(StringComparer.OrdinalIgnoreCase);
            var kept = new List<string>();
            var removed = new List<string>();
            foreach (var entry in (pathValue ?? string.Empty).Split(';')) {
                if (entry.Length > 0 && binDirectories.Contains(NormalizeDirectory(expand(entry))))
                    removed.Add(entry);
                else
                    kept.Add(entry);
            }
            removedEntries = removed;
            return string.Join(";", kept);
        }

        static string NormalizeDirectory(string path) => path.Trim().Trim('"').TrimEnd('\\', '/');
    }
}
