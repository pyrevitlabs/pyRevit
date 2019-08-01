using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common;

namespace pyRevitLabs.TargetApps.Revit {
    public static class PyRevitConsts {
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
                PyRevitExtensionsDefFileName
                );

        // urls
        public const string BlogsUrl = @"https://eirannejad.github.io/pyRevit/";
        public const string DocsUrl = @"https://pyrevit.readthedocs.io/en/latest/";
        public const string SourceRepoUrl = @"https://github.com/eirannejad/pyRevit";
        public const string YoutubeUrl = @"https://www.youtube.com/pyrevit";
        public const string SupportRepoUrl = @"https://www.patreon.com/pyrevit";
        public const string ReleasesUrl = @"https://github.com/eirannejad/pyRevit/releases";

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
        public const string PyRevitBinDirName = "bin";
        public const string PyRevitBinEnginesDirName = "engines";

        public const string PyRevitDevDirName = "dev";

        public const string PyRevitDocsDirName = "docs";
   
        public const string PyRevitExtensionsDirName = "extensions";
        public const string PyRevitExtensionDefFileName = "extension.json";
        public const string PyRevitExtensionsDefFileName = "extensions.json";

        public const string PyRevitLibDirName = "pyrevitlib";
        public const string PyRevitModuleDirName = "pyrevit";
        public const string PyRevitModuleLoaderDirName = "loader";
        public const string PyRevitModuleAddinDirName = "addin";
        public const string PyRevitVersionFilename = "version";

        public const string PyRevitReleaseDirName = "release";

        public const string PyRevitSitePackagesDirName = "site-packages";

        public const string PyRevitfileFilename = "PyRevitfile";

        // image clones
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
        public const string DefaultConfigsFileName = @"pyRevit_config.ini";
        public const string ConfigsFileRegexPattern = @".*[pyrevit|config].*\.ini";
        public const string ConfigsCoreSection = "core";
        public const string ConfigsCheckUpdatesKey = "checkupdates";
        public const string ConfigsAutoUpdateKey = "autoupdate";
        public const string ConfigsVerboseKey = "verbose";
        public const string ConfigsDebugKey = "debug";
        public const string ConfigsFileLoggingKey = "filelogging";
        public const string ConfigsStartupLogTimeoutKey = "startuplogtimeout";
        public const string ConfigsUserExtensionsKey = "userextensions";
        public const string ConfigsCPythonEngine = "cpyengine";
        public const string ConfigsLoadBetaKey = "loadbeta";
        public const string ConfigsRocketModeKey = "rocketmode";
        public const string ConfigsBinaryCacheKey = "bincache";
        public const string ConfigsMinDriveSpaceKey = "minhostdrivefreespace";
        public const string ConfigsRequiredHostBuildKey = "requiredhostbuild";
        public const string ConfigsOutputStyleSheet = "outputstylesheet";
        public const string ConfigsTelemetrySection = "telemetry";
        public const string ConfigsTelemetryStatusKey = "active";
        public const string ConfigsTelemetryFilePathKey = "telemetrypath";
        public const string ConfigsTelemetryServerUrlKey = "telemetryserverurl";
        public const string ConfigsUserCanUpdateKey = "usercanupdate";
        public const string ConfigsUserCanExtendKey = "usercanextend";
        public const string ConfigsUserCanConfigKey = "usercanconfig";
        // pyrevit.exe specific configs
        public const string EnvConfigsSectionName = "environment";
        public const string EnvConfigsInstalledClonesKey = "clones";
        public const string EnvConfigsExtensionLookupSourcesKey = "sources";
        public const string EnvConfigsTemplateSourcesKey = "templates";
        public const string EnvConfigsExtensionDBFileName = "PyRevitExtensionsDB.json";
        // extensions
        public const string ExtensionsDefaultDirName = "Extensions";
        public const string ExtensionJsonDisabledKey = "disabled";
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
    }
}