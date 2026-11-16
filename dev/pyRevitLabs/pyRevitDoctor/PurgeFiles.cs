using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security;
using Microsoft.Win32;

namespace pyRevitDoctor {
    /// <summary>
    /// <c>purge-files</c>: removes the pyRevit install and data folders, <c>pyRevit.addin</c> manifests and
    /// <c>bin</c> entries on the user and machine <c>PATH</c>.
    /// </summary>
    /// <remarks>
    /// Needs no working <c>pyrevit.exe</c>. Only paths from <see cref="PurgeTargets"/> are touched, and a
    /// folder is deleted only if it holds a pyRevit marker and is not a link. Unless
    /// <see cref="PurgeOptions.KeepConfig"/> is set, <c>pyRevit_config.ini</c> is first copied to the
    /// Documents folder, and when that copy fails nothing is deleted. That covers the clone-local config in
    /// an install folder, which takes precedence over the data folder configs, including a config left alone
    /// by an earlier <see cref="PurgeOptions.KeepConfig"/> run. The same holds for the <c>Extensions</c> folder
    /// of the data folders, which holds user-installed extensions: unless <see cref="PurgeOptions.KeepExtensions"/>
    /// is set it is first zipped to the Documents folder.
    /// </remarks>
    public static class PurgeFiles {
        sealed record PathScope(string Name, RegistryHive Hive, string SubKey);

        static readonly PathScope[] PathScopes = {
            new("user", RegistryHive.CurrentUser, "Environment"),
            new("machine", RegistryHive.LocalMachine, @"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        };

        /// <returns>False when the config backup failed and nothing was deleted.</returns>
        public static bool Run(PurgeSession session, MachineLocations locations) {
            session.Output.WriteLine("Purging pyRevit files...");
            if (!PurgeFilesAndFolders(session, locations))
                return false;
            PurgePathEntries(session, PurgeTargets.InstallDirectories(locations));
            return true;
        }

        internal static bool PurgeFilesAndFolders(PurgeSession session, MachineLocations locations) {
            var timestamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
            if (!BackUpConfigs(session, locations, timestamp) || !BackUpExtensions(session, locations, timestamp))
                return false;

            var preservedConfig = session.Options.KeepConfig ? new[] { PurgeTargets.ConfigFileName } : Array.Empty<string>();
            var preservedInDataDirectories = session.Options.KeepExtensions ? preservedConfig.Append(PurgeTargets.ExtensionsFolderName).ToArray() : preservedConfig;
            foreach (var directory in PurgeTargets.InstallDirectories(locations))
                DeleteDirectory(session, directory, preservedConfig);

            foreach (var directory in PurgeTargets.DataDirectories(locations))
                DeleteDirectory(session, directory, preservedInDataDirectories);

            foreach (var manifest in PurgeTargets.AddinManifests(locations, ListSubdirectories))
                DeleteFile(session, manifest);
            return true;
        }

        static bool BackUpConfigs(PurgeSession session, MachineLocations locations, string timestamp) {
            if (session.Options.KeepConfig) {
                session.Output.WriteLine($"Keeping {PurgeTargets.ConfigFileName} (--keep-config)");
                return true;
            }

            var dataConfigs = PurgeTargets.DataDirectories(locations)
                .Select((directory, index) => (Source: Path.Combine(directory, PurgeTargets.ConfigFileName), Label: index == 0 ? "user" : "all-users"));
            var localConfigs = PurgeTargets.InstallDirectories(locations)
                .Select((directory, index) => (Source: Path.Combine(directory, PurgeTargets.ConfigFileName), Label: $"install{index + 1}"));
            var configs = dataConfigs.Concat(localConfigs).Where(config => session.Exists(config.Source));
            foreach (var (source, label) in configs) {
                var backup = Path.Combine(locations.Documents, $"pyRevit_config.{label}.{timestamp}.ini");
                try {
                    if (!session.Options.DryRun)
                        File.Copy(source, backup, overwrite: false);
                    session.Output.WriteLine($"{(session.Options.DryRun ? "Fake Backed up" : "Backed up")} {source} to {backup}");
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) {
                    session.ReportFailed($"{source} backup, nothing was deleted", ex);
                    return false;
                }
            }
            return true;
        }

        static bool BackUpExtensions(PurgeSession session, MachineLocations locations, string timestamp) {
            var extensionFolders = PurgeTargets.DataDirectories(locations)
                .Select((directory, index) => (Source: Path.Combine(directory, PurgeTargets.ExtensionsFolderName), Label: index == 0 ? "user" : "all-users"))
                .Where(folder => session.Exists(folder.Source));
            foreach (var (source, label) in extensionFolders) {
                if (session.Options.KeepExtensions) {
                    session.Output.WriteLine($"Keeping {source} (--keep-extensions)");
                    continue;
                }

                var backup = Path.Combine(locations.Documents, $"pyRevit_extensions.{label}.{timestamp}.zip");
                try {
                    if (!session.Options.DryRun && Directory.EnumerateFileSystemEntries(source).Any())
                        ZipFile.CreateFromDirectory(source, backup, CompressionLevel.Optimal, includeBaseDirectory: true);
                    session.Output.WriteLine($"{(session.Options.DryRun ? "Fake Backed up" : "Backed up")} {source} to {backup}");
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) {
                    DeleteIncompleteBackup(backup);
                    session.ReportFailed($"{source} backup, nothing was deleted", ex);
                    return false;
                }
            }
            return true;
        }

        static void DeleteIncompleteBackup(string backup) {
            try {
                File.Delete(backup);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) {
            }
        }

        static void DeleteDirectory(PurgeSession session, string directory, IReadOnlyCollection<string> preservedNames) {
            if (!session.Exists(directory)) {
                session.ReportSkipped("not found", directory);
                return;
            }
            if (new DirectoryInfo(directory).Attributes.HasFlag(FileAttributes.ReparsePoint)) {
                session.ReportSkipped("is a link", directory);
                return;
            }
            if (!PurgeTargets.HasPyRevitMarker(directory, session.Exists)) {
                session.ReportSkipped("no pyRevit marker", directory);
                return;
            }

            try {
                if (!session.Options.DryRun)
                    DeleteContents(directory, preservedNames);
                session.ReportDeleted(directory, preservedNames.Count == 0 ? directory : null);
                if (preservedNames.Count > 0)
                    session.MarkCleared(directory);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or SecurityException) {
                session.ReportFailed(directory, ex);
            }
        }

        static void DeleteContents(string directory, IReadOnlyCollection<string> preservedNames) {
            if (preservedNames.Count == 0) {
                DeleteTree(directory);
                return;
            }
            foreach (var entry in Directory.EnumerateFileSystemEntries(directory)) {
                if (preservedNames.Contains(Path.GetFileName(entry), StringComparer.OrdinalIgnoreCase))
                    continue;
                if (Directory.Exists(entry))
                    DeleteTree(entry);
                else
                    DeleteFileClearingReadOnly(entry);
            }
        }

        static void DeleteTree(string directory) {
            try {
                Directory.Delete(directory, recursive: true);
            }
            catch (UnauthorizedAccessException) {
                ClearReadOnlyAttributes(directory);
                Directory.Delete(directory, recursive: true);
            }
        }

        static void ClearReadOnlyAttributes(string directory) {
            foreach (var file in Directory.EnumerateFiles(directory))
                File.SetAttributes(file, FileAttributes.Normal);
            foreach (var subdirectory in Directory.EnumerateDirectories(directory))
                if (!new DirectoryInfo(subdirectory).Attributes.HasFlag(FileAttributes.ReparsePoint))
                    ClearReadOnlyAttributes(subdirectory);
        }

        static void DeleteFile(PurgeSession session, string file) {
            if (!session.Exists(file)) {
                session.ReportSkipped("not found", file);
                return;
            }
            try {
                if (!session.Options.DryRun)
                    DeleteFileClearingReadOnly(file);
                session.ReportDeleted(file, file);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or SecurityException) {
                session.ReportFailed(file, ex);
            }
        }

        static void DeleteFileClearingReadOnly(string file) {
            File.SetAttributes(file, FileAttributes.Normal);
            File.Delete(file);
        }

        static IEnumerable<string> ListSubdirectories(string directory) =>
            Directory.Exists(directory) ? Directory.EnumerateDirectories(directory) : Enumerable.Empty<string>();

        static void PurgePathEntries(PurgeSession session, IReadOnlyList<string> installDirectories) {
            var changedAny = false;
            foreach (var scope in PathScopes) {
                var label = $"pyRevit bin entries on the {scope.Name} PATH";
                try {
                    using var baseKey = RegistryKey.OpenBaseKey(scope.Hive, RegistryView.Default);
                    using var key = baseKey.OpenSubKey(scope.SubKey, writable: !session.Options.DryRun);
                    if (key?.GetValue("Path", null, RegistryValueOptions.DoNotExpandEnvironmentNames) is not string currentValue) {
                        session.ReportSkipped("not found", label);
                        continue;
                    }

                    var updatedValue = PurgeTargets.RemoveBinEntries(currentValue, Environment.ExpandEnvironmentVariables, installDirectories, out var removed);
                    if (removed.Count == 0) {
                        session.ReportSkipped("not found", label);
                        continue;
                    }

                    if (!session.Options.DryRun) {
                        key.SetValue("Path", updatedValue, key.GetValueKind("Path"));
                        changedAny = true;
                    }
                    foreach (var entry in removed)
                        session.ReportDeleted($"{entry} from the {scope.Name} PATH");
                }
                catch (Exception ex) when (ex is UnauthorizedAccessException or SecurityException or IOException) {
                    session.ReportFailed(label, ex);
                }
            }
            if (changedAny)
                BroadcastEnvironmentChange();
        }

        static void BroadcastEnvironmentChange() {
            const uint wmSettingChange = 0x001A;
            const uint smtoAbortIfHung = 0x0002;
            SendMessageTimeout((IntPtr)0xFFFF, wmSettingChange, UIntPtr.Zero, "Environment", smtoAbortIfHung, 2000, out _);
        }

        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        static extern IntPtr SendMessageTimeout(IntPtr windowHandle, uint message, UIntPtr wParam, string lParam, uint flags, uint timeoutMilliseconds, out UIntPtr result);
    }
}
