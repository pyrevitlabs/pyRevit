using System;
using System.IO;
using System.Reflection;
using System.Text.RegularExpressions;

namespace pyRevitLabs.Common {
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
        /// Creates an empty default file when missing so callers can persist settings.
        /// </summary>
        public static string GetActiveConfigFilePath(bool createIfMissing = true) {
            var configRoot = GetConfigDirectory();
            var discovered = FindConfigIniInDirectory(configRoot);
            var finalPath = discovered ?? Path.Combine(configRoot, PyRevitLabsConsts.DefaultConfigsFileName);

            if (createIfMissing && !File.Exists(finalPath)) {
                var directory = Path.GetDirectoryName(finalPath);
                if (!string.IsNullOrEmpty(directory))
                    Directory.CreateDirectory(directory);
                File.Create(finalPath).Dispose();
            }

            return finalPath;
        }

        /// <summary>
        /// Repo/clone-local config override: the first config file found in the
        /// resolved install root (typically a developer clone), or null when none
        /// exists.
        /// </summary>
        public static string GetLocalConfigFilePath() {
            return FindConfigIniInDirectory(ResolveInstallRoot());
        }

        public static string FindConfigIniInDirectory(string directory) {
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
                return null;

            try {
                var configMatcher = new Regex(ConfigIniRegexPattern, RegexOptions.IgnoreCase);
                foreach (var fullPath in Directory.GetFiles(directory, "*.ini", SearchOption.TopDirectoryOnly)) {
                    if (configMatcher.IsMatch(Path.GetFileName(fullPath)))
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
