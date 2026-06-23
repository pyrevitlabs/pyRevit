using System;
using System.IO;

namespace pyRevitLabs.Common {
    /// <summary>
    /// Resolves pyRevit install scope (per-user vs all-users admin install).
    /// The admin installer creates %ProgramData%\pyRevit\install_all_users before
    /// any post-install CLI commands so clone registry and config stay in ProgramData.
    /// </summary>
    public static class PyRevitInstallScope {
        public const string InstallAllUsersMarkerFileName = "install_all_users";
        public const string DefaultConfigsFileName = "pyRevit_config.ini";

        private static bool? _isInstallAllUsers;

        public static bool IsAllUsersInstall() {
            if (_isInstallAllUsers.HasValue)
                return _isInstallAllUsers.Value;
            string markerPath = Path.Combine(
                PyRevitLabsConsts.PyRevitProgramDataPath,
                InstallAllUsersMarkerFileName);
            _isInstallAllUsers = File.Exists(markerPath);
            return _isInstallAllUsers.Value;
        }

        public static string GetConfigDirectory() {
            return IsAllUsersInstall()
                ? PyRevitLabsConsts.PyRevitProgramDataPath
                : PyRevitLabsConsts.PyRevitPath;
        }

        /// <summary>Clears cached install-scope detection (for tests).</summary>
        public static void ClearCachedInstallScope() {
            _isInstallAllUsers = null;
        }
    }
}
