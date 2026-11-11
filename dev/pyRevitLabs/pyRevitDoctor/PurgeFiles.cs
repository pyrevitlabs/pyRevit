using System;
using System.Collections.Generic;
using System.IO;
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
    /// an install folder that holds <c>pyRevitfile</c>, which takes precedence over the data folder configs.
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
            if (!BackUpConfigs(session, locations))
                return false;

            var preservedConfig = session.Options.KeepConfig ? PurgeTargets.ConfigFileName : null;
            foreach (var directory in PurgeTargets.InstallDirectories(locations))
                DeleteDirectory(session, directory, preservedConfig);

            foreach (var directory in PurgeTargets.DataDirectories(locations))
                DeleteDirectory(session, directory, preservedConfig);

            foreach (var manifest in PurgeTargets.AddinManifests(locations, ListSubdirectories))
                DeleteFile(session, manifest);
            return true;
        }

        static bool BackUpConfigs(PurgeSession session, MachineLocations locations) {
            if (session.Options.KeepConfig) {
                session.Output.WriteLine($"Keeping {PurgeTargets.ConfigFileName} (--keep-config)");
                return true;
            }

            var timestamp = DateTime.Now.ToString("yyyyMMdd-HHmmss");
            var dataConfigs = PurgeTargets.DataDirectories(locations)
                .Select((directory, index) => (Source: Path.Combine(directory, PurgeTargets.ConfigFileName), Label: index == 0 ? "user" : "all-users"));
            var localConfigs = PurgeTargets.InstallDirectories(locations)
                .Select((directory, index) => (Directory: directory, Label: $"install{index + 1}"))
                .Where(install => session.Exists(Path.Combine(install.Directory, "pyRevitfile")))
                .Select(install => (Source: Path.Combine(install.Directory, PurgeTargets.ConfigFileName), install.Label));
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

        static void DeleteDirectory(PurgeSession session, string directory, string preservedFileName) {
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
                    DeleteContents(directory, preservedFileName);
                session.ReportDeleted(directory, preservedFileName == null ? directory : null);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or SecurityException) {
                session.ReportFailed(directory, ex);
            }
        }

        static void DeleteContents(string directory, string preservedFileName) {
            if (preservedFileName == null) {
                DeleteTree(directory);
                return;
            }
            foreach (var entry in Directory.EnumerateFileSystemEntries(directory)) {
                if (Path.GetFileName(entry).Equals(preservedFileName, StringComparison.OrdinalIgnoreCase))
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
