using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Management;
using System.Security.Principal;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;

using DotNetVersionFinder;
using pyRevitLabs.NLog;


// user default folder implementation from https://stackoverflow.com/a/21953690/2350244

namespace pyRevitLabs.Common {

    /// <summary>
    /// Standard folders registered with the system. These folders are installed with Windows Vista
    /// and later operating systems, and a computer will have only folders appropriate to it
    /// installed.
    /// </summary>
    public enum KnownFolder {
        Contacts,
        Desktop,
        Documents,
        Downloads,
        Favorites,
        Links,
        Music,
        Pictures,
        SavedGames,
        SavedSearches,
        Videos
    }

    public static class UserEnv {
        private static Logger logger = LogManager.GetCurrentClassLogger();

        public static string GetWindowsVersion() {
            // https://docs.microsoft.com/en-us/windows/desktop/SysInfo/operating-system-version
            // https://stackoverflow.com/a/37700770/2350244
            return OSVersionInfo.GetOSVersionInfo().FullName;
        }

        public static Version GetInstalledDotNetVersion() {
            return DotNetVersion.Find();
        }

        public static List<string> GetInstalledDotnetTargetPacks() {
            var targetPackPaths = new List<string>();
            var frameworkPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                @"Reference Assemblies\Microsoft\Framework\.NETFramework"
                );
            foreach (string path in Directory.GetDirectories(frameworkPath))
                if (Regex.Match(Path.GetFileName(path), @"\d\..+").Success)
                    targetPackPaths.Add(path);
            return targetPackPaths;
        }

        public static List<string> GetInstalledDotnetCoreTargetPacks() {
            var targetPackPaths = new List<string>();
            var frameworkPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                @"dotnet\sdk"
                );
            foreach (string path in Directory.GetDirectories(frameworkPath))
                if (Regex.Match(Path.GetFileName(path), @"\d\..+").Success)
                    targetPackPaths.Add(path);
            return targetPackPaths;
        }

        public static string GetExecutingUserName() {
            return string.Format($"{WindowsIdentity.GetCurrent().Name}");
        }

        public static string GetLoggedInUserName() {
            try {
                ConnectionOptions oConn = new ConnectionOptions();
                ManagementScope oMs = new ManagementScope("\\\\localhost", oConn);

                ObjectQuery oQuery = new ObjectQuery("select * from Win32_ComputerSystem");
                ManagementObjectSearcher oSearcher = new ManagementObjectSearcher(oMs, oQuery);
                ManagementObjectCollection oReturnCollection = oSearcher.Get();

                foreach (ManagementObject oReturn in oReturnCollection) {
                    return oReturn["UserName"].ToString();
                }
            }
            catch (Exception ex) {
                logger.Debug("Failed to get logged in username. | {0}", ex.Message);
            }
            return null;
        }

        public static bool IsRunAsElevated() {
            WindowsIdentity id = WindowsIdentity.GetCurrent();
            return id.Owner != id.User;
        }

        public static bool IsRunAsAdmin() {
            WindowsIdentity id = WindowsIdentity.GetCurrent();
            WindowsPrincipal principal = new WindowsPrincipal(id);
            return principal.IsInRole(WindowsBuiltInRole.Administrator);
        }

        public static string UserHome => Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

        public static string UserTemp => Environment.ExpandEnvironmentVariables("%TEMP%");

        private static string[] _knownFolderGuids = new string[]
    {
        "{56784854-C6CB-462B-8169-88E350ACB882}", // Contacts
        "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}", // Desktop
        "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}", // Documents
        "{374DE290-123F-4565-9164-39C4925E467B}", // Downloads
        "{1777F761-68AD-4D8A-87BD-30B759FA33DD}", // Favorites
        "{BFB9D5E0-C6A9-404C-B2B2-AE6DB6AF4968}", // Links
        "{4BD8D571-6D19-48D3-BE97-422220080E43}", // Music
        "{33E28130-4E1E-4676-835A-98395C3BC3BB}", // Pictures
        "{4C5C32FF-BB9D-43B0-B5B4-2D72E54EAAA4}", // SavedGames
        "{7D1D3A04-DEBB-4115-95CF-2F29DA2920DA}", // SavedSearches
        "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}", // Videos
    };

        /// <summary>
        /// Gets the current path to the specified known folder as currently configured. This does
        /// not require the folder to be existent.
        /// </summary>
        /// <param name="knownFolder">The known folder which current path will be returned.</param>
        /// <returns>The default path of the known folder.</returns>
        /// <exception cref="System.Runtime.InteropServices.ExternalException">Thrown if the path
        ///     could not be retrieved.</exception>
        public static string GetPath(KnownFolder knownFolder) {
            return GetPath(knownFolder, false);
        }

        /// <summary>
        /// Gets the current path to the specified known folder as currently configured. This does
        /// not require the folder to be existent.
        /// </summary>
        /// <param name="knownFolder">The known folder which current path will be returned.</param>
        /// <param name="defaultUser">Specifies if the paths of the default user (user profile
        ///     template) will be used. This requires administrative rights.</param>
        /// <returns>The default path of the known folder.</returns>
        /// <exception cref="System.Runtime.InteropServices.ExternalException">Thrown if the path
        ///     could not be retrieved.</exception>
        public static string GetPath(KnownFolder knownFolder, bool defaultUser) {
            return GetPath(knownFolder, KnownFolderFlags.DontVerify, defaultUser);
        }

        private static string GetPath(KnownFolder knownFolder, KnownFolderFlags flags, bool defaultUser) {
            int result = Shell32.SHGetKnownFolderPath(new Guid(_knownFolderGuids[(int)knownFolder]),
                (uint)flags, new IntPtr(defaultUser ? -1 : 0), out IntPtr outPath);
            if (result >= 0) {
                string path = Marshal.PtrToStringUni(outPath);
                Marshal.FreeCoTaskMem(outPath);
                return path;
            }
            else {
                throw new ExternalException("Unable to retrieve the known folder path. It may not "
                    + "be available on this system.", result);
            }
        }
    }
}
