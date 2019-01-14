using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common;

namespace pyRevitLabs.TargetApps.Revit {
    public static class PyRevitConsts {
        // consts for the official pyRevit repo
        public const string OriginalRepoPath =
            @"https://github.com/eirannejad/pyRevit.git";

        public const string OriginalZipInternalBranchPath = @"{0}-{1}";
        public const string OriginalZipPath =
            @"https://github.com/eirannejad/pyRevit/archive/{0}.zip";

        public const string ExtensionsDefinitionFileUri =
            @"https://github.com/eirannejad/pyRevit/raw/master/extensions/extensions.json";

        // urls
        public const string BlogsUrl = @"https://eirannejad.github.io/pyRevit/";
        public const string DocsUrl = @"https://pyrevit.readthedocs.io/en/latest/";
        public const string SourceRepoUrl = @"https://github.com/eirannejad/pyRevit";
        public const string YoutubeUrl = @"https://www.youtube.com/pyrevit";
        public const string SupportRepoUrl = @"https://www.patreon.com/pyrevit";

        // repo info
        public const string DefaultCloneInstallName = "pyRevit";
        public const string DefaultCopyInstallName = "pyRevitCopy";
        public const string DefaultCloneRemoteName = "origin";
        public const string DefaultExtensionRemoteName = "origin";
        public const string OriginalRepoDefaultBranch = "master";
        public const string ExtensionRepoDefaultBranch = "master";
        public const string PyRevitfileFilename = "PyRevitfile";

        // archive clones
        public const string DeployFromArchiveConfigsFilename = ".pyrevitargs";

        // consts for creating pyRevit addon manifest file
        public const string AddinFileName = "pyRevit";
        public const string AddinName = "PyRevitLoader";
        public const string AddinId = "B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D";
        public const string AddinClassName = "PyRevitLoader.PyRevitLoaderApplication";
        public const string VendorId = "eirannejad";
        public const string DllName = "pyRevitLoader.dll";
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
        public const string ConfigsCompileCSharpKey = "compilecsharp";
        public const string ConfigsCompileVBKey = "compilevb";
        public const string ConfigsLoadBetaKey = "loadbeta";
        public const string ConfigsRocketModeKey = "rocketmode";
        public const string ConfigsBinaryCacheKey = "bincache";
        public const string ConfigsMinDriveSpaceKey = "minhostdrivefreespace";
        public const string ConfigsRequiredHostBuildKey = "requiredhostbuild";
        public const string ConfigsOutputStyleSheet = "outputstylesheet";
        public const string ConfigsUsageLoggingSection = "usagelogging";
        public const string ConfigsUsageLoggingStatusKey = "active";
        public const string ConfigsUsageLogFilePathKey = "logfilepath";
        public const string ConfigsUsageLogServerUrlKey = "logserverurl";
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
        public const string ExtensionJsonDisabledKey = "disabled";
        public const string ExtensionUIPostfix = ".extension";
        public const string ExtensionLibraryPostfix = ".lib";


        public static string GetZipPackageUrl(string branchName) {
            return string.Format(OriginalZipPath, branchName);
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
