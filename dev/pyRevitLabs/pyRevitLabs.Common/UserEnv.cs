using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Management;
using System.Security.Principal;
using System.IO;

using DotNetVersionFinder;
using System.Security.AccessControl;

namespace pyRevitLabs.Common {
    public static class UserEnv {
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
            var frameworkPath = @"C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework";
            foreach (string path in Directory.GetDirectories(frameworkPath))
                if (Regex.Match(Path.GetFileName(path), @"\d\..+").Success)
                    targetPackPaths.Add(path);
            return targetPackPaths;
        }

        public static List<string> GetInstalledDotnetCoreTargetPacks() {
            var targetPackPaths = new List<string>();
            var frameworkPath = @"C:\Program Files\dotnet\sdk";
            foreach (string path in Directory.GetDirectories(frameworkPath))
                if (Regex.Match(Path.GetFileName(path), @"\d\..+").Success)
                    targetPackPaths.Add(path);
            return targetPackPaths;
        }

        public static string GetLoggedInUserName() {
            ConnectionOptions oConn = new ConnectionOptions();
            ManagementScope oMs = new ManagementScope("\\\\localhost", oConn);

            ObjectQuery oQuery = new ObjectQuery("select * from Win32_ComputerSystem");
            ManagementObjectSearcher oSearcher = new ManagementObjectSearcher(oMs, oQuery);
            ManagementObjectCollection oReturnCollection = oSearcher.Get();

            foreach (ManagementObject oReturn in oReturnCollection) {
                return oReturn["UserName"].ToString();
            }

            return null;
        }

        public static bool IsRunAsAdmin() {
            WindowsIdentity id = WindowsIdentity.GetCurrent();
            WindowsPrincipal principal = new WindowsPrincipal(id);
            return principal.IsInRole(WindowsBuiltInRole.Administrator);
        }

        public static string UserHome => Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

        public static string UserTemp => Environment.ExpandEnvironmentVariables("%TEMP%");
    }
}
