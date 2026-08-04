using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;

namespace pyRevitLabs.Common {
    /// <summary>
    /// Describes the configuration file resolved for the current process:
    /// where it lives, whether the process is allowed to persist changes to it,
    /// and whether it is the machine-wide (ProgramData) config of an admin install.
    /// </summary>
    public sealed class ActiveConfigInfo {
        internal ActiveConfigInfo(string configPath, bool isReadOnly, bool isMachineConfig) {
            ConfigPath = configPath;
            IsReadOnly = isReadOnly;
            IsMachineConfig = isMachineConfig;
        }

        /// <summary>Full path of the active configuration file.</summary>
        public string ConfigPath { get; private set; }

        /// <summary>
        /// True when the config must be treated as read-only
        /// (admin-locked seed, or a file the process can not write to).
        /// </summary>
        public bool IsReadOnly { get; private set; }

        /// <summary>True when the active config is the machine-wide (ProgramData) config.</summary>
        public bool IsMachineConfig { get; private set; }
    }

    /// <summary>
    /// Resolves pyRevit install scope (per-user vs machine-wide admin install) and
    /// the active configuration file path shared by CLI, Revit Python, and the C# loader.
    /// </summary>
    public static class PyRevitInstallScope {
        public const string ConfigScopeEnvVar = "PYREVIT_CONFIG_SCOPE";
        public const string ConfigScopeAllUsers = "allusers";
        public const string ConfigScopePerUser = "peruser";

        private const string PyRevitfileName = "pyRevitfile";
        private const string ConfigIniRegexPattern = @".*(pyrevit|config).*\.ini";

        // Configs suffixed with a number (pyRevit_config.2025.ini) belong to a
        // specific Revit version and are resolved by their own lookup, never by
        // the generic name match below.
        private const string VersionedConfigIniRegexPattern = @"\.\d+\.ini$";

        private static bool? _isInstallAllUsers;
        private static string _runtimeInstallRoot;

        /// <summary>
        /// Optional install root set by the Revit session (attached clone path).
        /// Clears cached scope when updated.
        /// </summary>
        public static void SetRuntimeInstallRoot(string installRoot) {
            _runtimeInstallRoot = string.IsNullOrWhiteSpace(installRoot)
                ? null
                : installRoot.Trim();
            ClearCachedInstallScope();
        }

        public static bool IsAllUsersInstall() {
            if (_isInstallAllUsers.HasValue)
                return _isInstallAllUsers.Value;

            var scopeEnv = Environment.GetEnvironmentVariable(ConfigScopeEnvVar);
            if (!string.IsNullOrWhiteSpace(scopeEnv)) {
                if (scopeEnv.Equals(ConfigScopeAllUsers, StringComparison.OrdinalIgnoreCase)) {
                    _isInstallAllUsers = true;
                    return true;
                }
                if (scopeEnv.Equals(ConfigScopePerUser, StringComparison.OrdinalIgnoreCase)) {
                    _isInstallAllUsers = false;
                    return false;
                }
            }

            if (LegacyMarkerExists()) {
                _isInstallAllUsers = true;
                return true;
            }

            var installRoot = ResolveInstallRoot();
            _isInstallAllUsers = IsMachineInstallPath(installRoot);
            return _isInstallAllUsers.Value;
        }

        public static string GetConfigDirectory() {
            return IsAllUsersInstall()
                ? PyRevitLabsConsts.PyRevitProgramDataPath
                : PyRevitLabsConsts.PyRevitPath;
        }

        /// <summary>
        /// Active pyRevit configuration file for the current install scope.
        /// Best-effort: creates an empty default file when missing so callers can persist settings.
        /// </summary>
        public static string GetActiveConfigFilePath(bool createIfMissing = true) {
            return GetActiveConfig(createIfMissing).ConfigPath;
        }

        /// <summary>
        /// Resolves the configuration file the current process should use.
        /// A machine-wide config marked with the ReadOnly attribute is a deliberate
        /// admin lock and is used as-is in read-only mode. For all-users installs,
        /// elevated processes (installer / admin CLI) always target ProgramData;
        /// standard users always get a per-user config under AppData, seeded from
        /// the machine-wide file when one exists. Per-user installs always resolve
        /// to AppData unless the admin lock above applies.
        /// </summary>
        public static ActiveConfigInfo GetActiveConfig(bool createIfMissing = true) {
            var machineRoot = PyRevitLabsConsts.PyRevitProgramDataPath;
            var machineConfig = FindConfigIniInDirectory(machineRoot)
                ?? Path.Combine(machineRoot, PyRevitLabsConsts.DefaultConfigsFileName);
            bool machineConfigExists = File.Exists(machineConfig);

            // admin-locked seed applies to every install scope
            if (machineConfigExists && HasReadOnlyAttribute(machineConfig))
                return new ActiveConfigInfo(machineConfig, isReadOnly: true, isMachineConfig: true);

            if (IsAllUsersInstall() && IsElevatedProcess()) {
                if (machineConfigExists) {
                    bool writable = IsFileWritable(machineConfig);
                    return new ActiveConfigInfo(
                        machineConfig, isReadOnly: !writable, isMachineConfig: true);
                }
                if (!createIfMissing || TryCreateFile(machineConfig)) {
                    return new ActiveConfigInfo(machineConfig, isReadOnly: false, isMachineConfig: true);
                }
            }

            return GetUserConfig(machineConfigExists ? machineConfig : null, createIfMissing);
        }

        /// <summary>
        /// True when the current Windows process is elevated (installer / admin CLI).
        /// Always false on non-Windows hosts so CI and cross-platform tooling
        /// resolve to the per-user config path.
        /// </summary>
        public static bool IsElevatedProcess() {
            if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                return false;
            return UserEnv.IsRunAsElevated();
        }

        private static ActiveConfigInfo GetUserConfig(string seedConfig, bool createIfMissing) {
            var userRoot = PyRevitLabsConsts.PyRevitPath;
            var userConfig = FindConfigIniInDirectory(userRoot)
                ?? Path.Combine(userRoot, PyRevitLabsConsts.DefaultConfigsFileName);

            if (createIfMissing && !File.Exists(userConfig))
                EnsureUserConfigFile(userConfig, seedConfig);

            bool isReadOnly = !File.Exists(userConfig) || !IsFileWritable(userConfig);
            return new ActiveConfigInfo(userConfig, isReadOnly, isMachineConfig: false);
        }

        private static void EnsureUserConfigFile(string userConfig, string seedConfig) {
            try {
                var directory = Path.GetDirectoryName(userConfig);
                if (!string.IsNullOrEmpty(directory))
                    Directory.CreateDirectory(directory);
            }
            catch {
                // fall through; TryCreateFile reports failure when the path is unusable
            }

            if (seedConfig != null) {
                try {
                    File.Copy(seedConfig, userConfig, overwrite: false);
                    return;
                }
                catch {
                    // seed unreadable or copy blocked: still give the user a writable ini
                }
            }

            if (File.Exists(userConfig))
                return;

            TryCreateFile(userConfig);
        }

        /// <summary>True when the file carries the DOS ReadOnly attribute (deliberate admin lock).</summary>
        public static bool HasReadOnlyAttribute(string filePath) {
            try {
                return File.Exists(filePath)
                    && (File.GetAttributes(filePath) & FileAttributes.ReadOnly) == FileAttributes.ReadOnly;
            }
            catch {
                return false;
            }
        }

        /// <summary>
        /// True when the current process can write to the existing file.
        /// Probes with a real open-for-write so NTFS ACL restrictions are
        /// detected as well as the ReadOnly attribute.
        /// </summary>
        public static bool IsFileWritable(string filePath) {
            if (string.IsNullOrEmpty(filePath) || !File.Exists(filePath))
                return false;
            try {
                using (File.Open(filePath, FileMode.Open, FileAccess.Write, FileShare.ReadWrite)) { }
                return true;
            }
            catch {
                return false;
            }
        }

        private static bool TryCreateFile(string filePath) {
            try {
                var directory = Path.GetDirectoryName(filePath);
                if (!string.IsNullOrEmpty(directory))
                    Directory.CreateDirectory(directory);
                File.Create(filePath).Dispose();
                return true;
            }
            catch {
                return false;
            }
        }

        /// <summary>
        /// Repo/clone-local config override: the first config file found in the
        /// resolved install root (typically a developer clone), or null when none
        /// exists.
        /// </summary>
        public static string GetLocalConfigFilePath() {
            return FindConfigIniInDirectory(ResolveInstallRoot());
        }

        /// <summary>
        /// Returns the main config file in <paramref name="directory"/>, or null when
        /// none is present. The canonically named file wins outright; the name match
        /// is only a fallback for configs carrying a custom name.
        /// </summary>
        public static string FindConfigIniInDirectory(string directory) {
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
                return null;

            try {
                var defaultPath = Path.Combine(directory, PyRevitLabsConsts.DefaultConfigsFileName);
                if (File.Exists(defaultPath))
                    return defaultPath;

                var configMatcher = new Regex(ConfigIniRegexPattern, RegexOptions.IgnoreCase);
                var versionedMatcher = new Regex(VersionedConfigIniRegexPattern, RegexOptions.IgnoreCase);
                foreach (var fullPath in Directory.GetFiles(directory, "*.ini", SearchOption.TopDirectoryOnly)) {
                    var fileName = Path.GetFileName(fullPath);
                    if (configMatcher.IsMatch(fileName) && !versionedMatcher.IsMatch(fileName))
                        return fullPath;
                }
            }
            catch {
                // ignore
            }

            return null;
        }

        /// <summary>Clears cached install-scope detection (for tests and reload).</summary>
        public static void ClearCachedInstallScope() {
            _isInstallAllUsers = null;
        }

        private static bool LegacyMarkerExists() {
            string markerPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath,
                PyRevitLabsConsts.InstallAllUsersMarkerFileName);
            return File.Exists(markerPath);
        }

        private static string ResolveInstallRoot() {
            if (!string.IsNullOrWhiteSpace(_runtimeInstallRoot))
                return _runtimeInstallRoot;

            string assemblyPath = null;
            try {
                assemblyPath = Assembly.GetExecutingAssembly().Location;
            }
            catch {
                // ignore
            }

            if (string.IsNullOrWhiteSpace(assemblyPath))
                return null;

            return FindInstallRootFromPath(Path.GetDirectoryName(assemblyPath));
        }

        internal static string FindInstallRootFromPath(string startDirectory) {
            if (string.IsNullOrWhiteSpace(startDirectory))
                return null;

            var dir = startDirectory;
            for (int depth = 0; depth < 8 && !string.IsNullOrEmpty(dir); depth++) {
                if (File.Exists(Path.Combine(dir, PyRevitfileName)))
                    return dir;

                if (string.Equals(Path.GetFileName(dir), "bin", StringComparison.OrdinalIgnoreCase)) {
                    var parent = Path.GetDirectoryName(dir);
                    if (parent != null && File.Exists(Path.Combine(parent, PyRevitfileName)))
                        return parent;
                }

                dir = Path.GetDirectoryName(dir);
            }

            if (string.Equals(Path.GetFileName(startDirectory), "bin", StringComparison.OrdinalIgnoreCase))
                return Path.GetDirectoryName(startDirectory);

            return startDirectory;
        }

        internal static bool IsMachineInstallPath(string installRoot) {
            if (string.IsNullOrWhiteSpace(installRoot))
                return false;

            string normalized;
            try {
                normalized = Path.GetFullPath(installRoot)
                    .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            }
            catch {
                return false;
            }

            var machineRoots = new[] {
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                Environment.GetFolderPath(Environment.SpecialFolder.CommonProgramFiles),
            };

            foreach (var root in machineRoots) {
                if (string.IsNullOrWhiteSpace(root))
                    continue;

                string normRoot;
                try {
                    normRoot = Path.GetFullPath(root)
                        .TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                }
                catch {
                    continue;
                }

                if (string.Equals(normalized, normRoot, StringComparison.OrdinalIgnoreCase))
                    return true;

                var prefix = normRoot + Path.DirectorySeparatorChar;
                if (normalized.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }
    }
}
