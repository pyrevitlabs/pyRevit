using System;
using System.IO;
using System.Text.RegularExpressions;

using pyRevitLabs.NLog;
using pyRevitLabs.Common;

namespace pyRevitLabs.PyRevit {
    public static class PyRevit {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // product
        public const string ProductName = "pyRevit";

        // consts for the official pyRevit repo
        public const string OriginalRepoPath =
            @"https://github.com/eirannejad/pyRevit.git";

        public const string OriginalZipInternalBranchPath = @"{0}-{1}";
        public const string ImageFileExtension = ".zip";
        public const string OriginalImageUrl =
            @"https://github.com/eirannejad/pyRevit/archive/{0}" + ImageFileExtension;

        public static string ExtensionsDefinitionFileUri =
            string.Format(
                @"https://github.com/eirannejad/pyRevit/raw/master/extensions/{0}",
                ExtensionsDefFileName
                );

        // urls
        public const string LicenseUrl = @"https://choosealicense.com/licenses/gpl-3.0/";
        public const string CreditsUrl = @"https://github.com/eirannejad/pyRevit/blob/master/CREDITS.md";
        public const string BlogsUrl = @"https://eirannejad.github.io/pyRevit/";
        public const string DocsUrl = @"https://pyrevit.readthedocs.io/en/latest/";
        public const string SourceRepoUrl = @"https://github.com/eirannejad/pyRevit";
        public const string IssuesUrl = @"https://github.com/eirannejad/pyRevit/issues";
        public const string ReleasesUrl = @"https://github.com/eirannejad/pyRevit/releases";
        public const string YoutubeUrl = @"https://www.youtube.com/pyrevit";
        public const string SupportUrl = @"https://www.patreon.com/pyrevit";

        // cli
        public const string CLIHelpUrl = @"https://github.com/eirannejad/pyRevit/blob/cli-v{0}/docs/cli.md";
        public const string CLIHelpUrlDev = @"https://github.com/eirannejad/pyRevit/blob/develop/docs/cli.md";

        // api
        public const string ReleasePrefix = "v";
        public const string CLIReleasePrefix = "cli-v";
        public const string APIReleasesUrl = @"https://api.github.com/repos/eirannejad/pyrevit/releases";

        // repo info
        public const string DefaultGitDirName = ".git";
        public const string DefaultCloneInstallName = "pyRevit";
        public const string DefaultCopyInstallName = "pyRevitCopy";
        public const string DefaultCloneRemoteName = "origin";
        public const string DefaultExtensionRemoteName = "origin";
        public const string OriginalRepoDefaultBranch = "master";
        public const string ExtensionRepoDefaultBranch = "master";

        // directories and files
        public const string BinDirName = "bin";
        public const string BinEnginesDirName = "engines";
        public const string DevDirName = "dev";
        public const string DocsDirName = "docs";
        public const string ExtensionsDirName = "extensions";
        public const string ExtensionDefFileName = "extension.json";
        public const string ExtensionsDefFileName = "extensions.json";
        public const string LibDirName = "pyrevitlib";
        public const string ModuleDirName = "pyrevit";
        public const string ModuleLoaderDirName = "loader";
        public const string ModuleAddinDirName = "addin";
        public const string VersionFilename = "version";
        public const string ReleaseDirName = "release";
        public const string SitePackagesDirName = "site-packages";
        public const string PyRevitfileFilename = "PyRevitfile";

        // clones
        public const string DeployFromImageConfigsFilename = ".pyrevitargs";

        // consts for creating pyRevit addon manifest file
        public const string AddinFileName = "pyRevit";
        public const string AddinName = "PyRevitLoader";
        public const string AddinId = "B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D";
        public const string AddinClassName = "PyRevitLoader.PyRevitLoaderApplication";
        public const string VendorId = "eirannejad";
        public const string LegacyEngineDllName = "pyRevitLoader.dll";
        public const int ConfigsDynamoCompatibleEnginerVer = 273;

        // consts for recording pyrevit.exe config in the pyRevit configuration file
        public const string AppdataDirName = "pyRevit";
        public const string AppdataLogsDirName = "Logs";

        // core configs
        public const string ConfigsTrueString = "true";
        public const string ConfigsFalseString = "false";
        public const string DefaultConfigsFileName = @"pyRevit_config.ini";
        public const string ConfigsFileRegexPattern = @".*[pyrevit|config].*\.ini";
        public const string ConfigsCoreSection = "core";
        public const string ConfigsCheckUpdatesKey = "checkupdates";
        public const bool ConfigsCheckUpdatesDefault = false;
        public const string ConfigsAutoUpdateKey = "autoupdate";
        public const bool ConfigsAutoUpdateDefault = false;
        public const string ConfigsVerboseKey = "verbose";
        public const bool ConfigsVerboseDefault = false;
        public const string ConfigsDebugKey = "debug";
        public const bool ConfigsDebugDefault = false;
        public const string ConfigsFileLoggingKey = "filelogging";
        public const bool ConfigsFileLoggingDefault = false;
        public const string ConfigsStartupLogTimeoutKey = "startuplogtimeout";
        public const int ConfigsStartupLogTimeoutDefault = 10;
        public const string ConfigsUserExtensionsKey = "userextensions";
        public const string ConfigsCPythonEngine = "cpyengine";
        public const string ConfigsLoadBetaKey = "loadbeta";
        public const bool ConfigsLoadBetaDefault = false;
        public const string ConfigsRocketModeKey = "rocketmode";
        public const bool ConfigsRocketModeDefault = true;
        public const string ConfigsBinaryCacheKey = "bincache";
        public const bool ConfigsBinaryCacheDefault = true;
        public const string ConfigsMinDriveSpaceKey = "minhostdrivefreespace";
        public const string ConfigsRequiredHostBuildKey = "requiredhostbuild";
        public const string ConfigsOutputStyleSheet = "outputstylesheet";
        public const string ConfigsTelemetrySection = "telemetry";
        public const string ConfigsTelemetryStatusKey = "active";
        public const bool ConfigsTelemetryStatusDefault = false;
        public const string ConfigsTelemetryFilePathKey = "telemetry_file_dir";
        public const string ConfigsTelemetryServerUrlKey = "telemetry_server_url";
        public const string ConfigsAppTelemetryStatusKey = "active_app";
        public const bool ConfigsAppTelemetryStatusDefault = false;
        public const string ConfigsAppTelemetryServerUrlKey = "apptelemetry_server_url";
        public const string ConfigsAppTelemetryEventFlagsKey = "apptelemetry_event_flags";
        public const string ConfigsUserCanUpdateKey = "usercanupdate";
        public const bool ConfigsUserCanUpdateDefault = true;
        public const string ConfigsUserCanExtendKey = "usercanextend";
        public const bool ConfigsUserCanExtendDefault = true;
        public const string ConfigsUserCanConfigKey = "usercanconfig";
        public const bool ConfigsUserCanConfigDefault = true;
        // pyrevit.exe specific configs
        public const string EnvConfigsSectionName = "environment";
        public const string EnvConfigsInstalledClonesKey = "clones";
        public const string EnvConfigsExtensionLookupSourcesKey = "sources";
        public const string EnvConfigsTemplateSourcesKey = "templates";
        public const string EnvConfigsExtensionDBFileName = "PyRevitExtensionsDB.json";
        // extensions
        public const string ExtensionsDefaultDirName = "Extensions";
        public const string ExtensionDisabledKey = "disabled";
        public const string ExtensionUIPostfix = ".extension";
        public const string ExtensionLibraryPostfix = ".lib";
        public const string ExtensionRunnerPostfix = ".run";
        public const string ExtensionRunnerCommandPostfix = "_command.py";
        // bundles
        public const string BundleTabPostfix = ".tab";
        public const string BundlePanelPostfix = ".panel";
        public const string BundleLinkButtonPostfix = ".linkbutton";
        public const string BundlePushButtonPostfix = ".pushbutton";
        public const string BundleToggleButtonPostfix = ".toggle";
        public const string BundleSmartButtonPostfix = ".smartbutton";
        public const string BundlePulldownButtonPostfix = ".pulldown";
        public const string BundleStack3Postfix = ".stack3";
        public const string BundleStack2Postfix = ".stack2";
        public const string BundleSplitButtonPostfix = ".splitbutton";
        public const string BundleSplitPushButtonPostfix = ".splitpushbutton";
        public const string BundlePanelButtonPostfix = ".panelbutton";
        public const string BundleNoButtonPostfix = ".nobutton";

        // methods
        public static string GetBranchArchiveUrl(string branchName) {
            return string.Format(OriginalImageUrl, branchName);
        }

        public static string GetTagArchiveUrl(string tagName) {
            return string.Format(OriginalImageUrl, tagName);
        }

        public static string GetZipPackageInternalBranchPath(string branchName) {
            return string.Format(
                OriginalZipInternalBranchPath,
                DefaultCloneInstallName,
                branchName.Replace("/", "-")
                );
        }

        public static string FindConfigFileInDirectory(string sourcePath) {
            var configMatcher = new Regex(ConfigsFileRegexPattern, RegexOptions.IgnoreCase);
            if (CommonUtils.VerifyPath(sourcePath))
                foreach (string subFile in Directory.GetFiles(sourcePath))
                    if (configMatcher.IsMatch(Path.GetFileName(subFile)))
                        return subFile;
            return null;
        }

        // STANDARD PATHS ============================================================================================
        // pyRevit %appdata% path
        // @reviewed
        public static string pyRevitPath =>
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                                          PyRevit.AppdataDirName);

        // pyRevit %programdata% path
        // @reviewed
        public static string pyRevitProgramDataPath =>
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), AppdataDirName);

        // pyRevit default extensions path
        // @reviewed
        public static string DefaultExtensionsPath =>
            Path.Combine(pyRevitPath, PyRevit.ExtensionsDefaultDirName);

        // pyRevit config file path
        // @reviewed
        public static string ConfigFilePath {
            get {
                var cfgFile = FindConfigFileInDirectory(pyRevitPath);
                return cfgFile != null ? cfgFile : Path.Combine(pyRevitPath, DefaultConfigsFileName);
            }
        }

        // pyRevit config file path
        // @reviewed
        public static string SeedConfigFilePath {
            get {
                var cfgFile = FindConfigFileInDirectory(pyRevitProgramDataPath);
                return cfgFile != null ? cfgFile : Path.Combine(pyRevitProgramDataPath, DefaultConfigsFileName);
            }
        }

        // pyrevit logs folder 
        // @reviewed
        public static string LogsDirectory {
            get {
                return Path.Combine(pyRevitPath, AppdataLogsDirName);
            }
        }
    }
}
