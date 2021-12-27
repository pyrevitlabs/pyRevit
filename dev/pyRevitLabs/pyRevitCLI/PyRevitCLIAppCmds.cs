using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Drawing;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;
using pyRevitLabs.PyRevit;
using pyRevitLabs.Language.Properties;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitCLI {
    public enum TargetCacheType {
        PyRevitCache,
        BIM360Cache
    }

    public class JsonVersionConverter : JsonConverter<Version> {
        public override Version ReadJson(JsonReader reader, Type objectType, Version existingValue, bool hasExistingValue, JsonSerializer serializer) {
            throw new NotImplementedException();
        }

        public override void WriteJson(JsonWriter writer, Version value, JsonSerializer serializer) {
            writer.WriteValue(value.ToString());
        }
    }

    internal static class PyRevitCLIAppCmds {
        private static Logger logger = LogManager.GetCurrentClassLogger();

        // internal helpers:
        internal static string GetProcessFileName() => Process.GetCurrentProcess().MainModule.FileName;
        internal static string GetProcessPath() => Path.GetDirectoryName(GetProcessFileName());

        internal static void PrintHeader(string header) =>
            Console.WriteLine(string.Format("==> {0}", header), Color.Green);

        internal static void ReportCloneAsNoGit(PyRevitClone clone) =>
            Console.WriteLine(
                string.Format("Clone \"{0}\" is a deployment and is not a git repo.",
                clone.Name)
                );

        internal static bool IsRunningInsideClone(PyRevitClone clone) =>
            GetProcessPath().NormalizeAsPath().Contains(clone.ClonePath.NormalizeAsPath());

        internal static void
        ClearCaches(bool allCaches, string revitYear, TargetCacheType cachetype) {
            switch (cachetype) {
                case TargetCacheType.PyRevitCache:
                    if (allCaches)
                        PyRevitCaches.ClearAllCaches();
                    else {
                        int revitYearNumber = 0;
                        if (int.TryParse(revitYear, out revitYearNumber))
                            PyRevitCaches.ClearCache(revitYearNumber);
                    }
                    break;

                case TargetCacheType.BIM360Cache:
                    if (allCaches)
                        RevitCaches.ClearAllCaches(RevitCacheType.BIM360Cache);
                    else {
                        int revitYearNumber = 0;
                        if (int.TryParse(revitYear, out revitYearNumber))
                            RevitCaches.ClearCache(revitYearNumber, RevitCacheType.BIM360Cache);
                    }
                    break;
            }
        }

        // env commands
        internal static string
        CreateEnvJson() {
            // collecet search paths
            var searchPaths = new List<string>() { PyRevitConsts.DefaultExtensionsPath };
            searchPaths.AddRange(PyRevitExtensions.GetRegisteredExtensionSearchPaths());

            // collect list of lookup sources
            var lookupSrc = new List<string>() { PyRevitExtensions.GetDefaultExtensionLookupSource() };
            lookupSrc.AddRange(PyRevitExtensions.GetRegisteredExtensionLookupSources());

            // create json data object
            var jsonData = new Dictionary<string, object>() {
                        { "meta", new Dictionary<string, object>() {
                                { "version", "0.1.0"}
                            }
                        },
                        { "clones", PyRevitClones.GetRegisteredClones() },
                        { "attachments", PyRevitAttachments.GetAttachments() },
                        { "extensions", PyRevitExtensions.GetInstalledExtensions() },
                        { "searchPaths", searchPaths },
                        { "lookupSources", lookupSrc },
                        { "installed", RevitProduct.ListInstalledProducts() },
                        { "running", RevitController.ListRunningRevits() },
                        { "pyrevitDataDir", PyRevitLabsConsts.PyRevitPath },
                        { "userEnv", new Dictionary<string, object>() {
                                { "osVersion", UserEnv.GetWindowsVersion() },
                                { "execUser", string.Format("{0}\\{1}", Environment.UserDomainName, Environment.UserName) },
                                { "activeUser", UserEnv.GetLoggedInUserName() },
                                { "isAdmin", UserEnv.IsRunAsAdmin() },
                                { "userAppdata", Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData) },
                                { "latestFramework", UserEnv.GetInstalledDotNetVersion() },
                                { "targetPacks", UserEnv.GetInstalledDotnetTargetPacks() },
                                { "targetPacksCore", UserEnv.GetInstalledDotnetCoreTargetPacks() },
                                { "cliVersion", PyRevitCLI.CLIInfoVersion },
                            }
                        },
                    };

            var jsonExportCfg = new JsonSerializerSettings {
                Error = delegate (object sender, pyRevitLabs.Json.Serialization.ErrorEventArgs args) {
                    args.ErrorContext.Handled = true;
                },
                ContractResolver = new CamelCasePropertyNamesContractResolver()
            };
            jsonExportCfg.Converters.Add(new JsonVersionConverter());

            return JsonConvert.SerializeObject(jsonData, jsonExportCfg);
        }

        internal static void
        MakeEnvReport(bool json) {
            if (json)
                Console.WriteLine(CreateEnvJson());
            else {
                PyRevitCLICloneCmds.PrintClones();
                PyRevitCLICloneCmds.PrintAttachments();
                PyRevitCLIExtensionCmds.PrintExtensions();
                PyRevitCLIExtensionCmds.PrintExtensionSearchPaths();
                PyRevitCLIExtensionCmds.PrintExtensionLookupSources();
                PyRevitCLIRevitCmds.PrintLocalRevits();
                PyRevitCLIRevitCmds.PrintLocalRevits(running: true);
                PrinUserEnv();
            }
        }

        internal static void
        PrinUserEnv() {
            PrintHeader("User Environment");
            Console.WriteLine(UserEnv.GetWindowsVersion());
            Console.WriteLine(string.Format("Executing User: {0}\\{1}",
                                            Environment.UserDomainName, Environment.UserName));
            Console.WriteLine(string.Format("Active User: {0}", UserEnv.GetLoggedInUserName()));
            Console.WriteLine(string.Format("Admin Access: {0}", UserEnv.IsRunAsAdmin() ? "Yes" : "No"));
            Console.WriteLine(string.Format("%APPDATA%: \"{0}\"",
                                            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData)));
            Console.WriteLine(string.Format("Latest Installed .Net Framework: {0}",
                                            UserEnv.GetInstalledDotNetVersion()));
            try {
                string targetPacks = "";
                foreach (string targetPackagePath in UserEnv.GetInstalledDotnetTargetPacks())
                    targetPacks += string.Format("{0} ", Path.GetFileName(targetPackagePath));
                Console.WriteLine(string.Format("Installed .Net Target Packs: {0}", targetPacks));
            }
            catch {
                Console.WriteLine("No .Net Target Packs are installed.");
            }

            try {
                string targetPacks = "";
                foreach (string targetPackagePath in UserEnv.GetInstalledDotnetCoreTargetPacks())
                    targetPacks += string.Format("v{0} ", Path.GetFileName(targetPackagePath));
                Console.WriteLine(string.Format("Installed .Net-Core Target Packs: {0}", targetPacks));
            }
            catch {
                Console.WriteLine("No .Ne-Core Target Packs are installed.");
            }

            Console.WriteLine(string.Format("pyRevit CLI v{0}", PyRevitCLI.CLIInfoVersion));
        }

        // cli specific commands
        internal static void
        PrintVersion(bool checkUpdates = false) {
            Console.WriteLine(string.Format(StringLib.ConsoleVersionFormat, PyRevitCLI.CLIInfoVersion));
            if (checkUpdates) {
                if (CommonUtils.CheckInternetConnection()) {
                    try {
                        var latestVersion = PyRevitReleases.GetLatestCLIReleaseVersion();

                        if (latestVersion != null) {
                            logger.Debug("Latest release: {0}", latestVersion);
                            if (PyRevitCLI.CLIVersion < latestVersion) {
                                Console.WriteLine(
                                    string.Format(
                                        "Newer v{0} is available.\nGo to {1} to download the installer.",
                                        latestVersion,
                                        PyRevitLabsConsts.ReleasesUrl)
                                    );
                            }
                            else
                                Console.WriteLine("You have the latest version.");
                        }
                        else
                            logger.Debug("Failed getting latest release list OR no CLI releases.");
                    }
                    catch (Exception getRelEx) {
                        Console.WriteLine(getRelEx.Message);
                    }
                }
            }
        }

        internal static void
        UpdateRemoteDataSources() {
            // update and show progress
            RevitProductData.Update();
            PyRevitProductData.Update();
        }

        internal static void
        RunDoctor(string args, bool dryRun = false) {
            if (dryRun) args += " --dryrun";
            
            string doctorExe = Path.Combine(GetProcessPath(), "pyrevit-doctor.exe");
            ProcessStartInfo cpyProcessInfo = new ProcessStartInfo(doctorExe) {
                WorkingDirectory = GetProcessPath(),
                Arguments = args,
                UseShellExecute = false
            };
            var utilityProcess = Process.Start(cpyProcessInfo);
            utilityProcess.WaitForExit();
        }
    }
}
