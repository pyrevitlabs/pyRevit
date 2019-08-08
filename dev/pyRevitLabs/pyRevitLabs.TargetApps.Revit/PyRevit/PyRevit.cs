using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text.RegularExpressions;
using System.Security.Principal;
using System.Text;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public static class PyRevit {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

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
        public const string ConfigsTelemetryFilePathKey = "telemetry_file_dir";
        public const string ConfigsTelemetryServerUrlKey = "telemetry_server_url";
        public const string ConfigsAppTelemetryStatusKey = "active_app";
        public const string ConfigsAppTelemetryServerUrlKey = "apptelemetry_server_url";
        public const string ConfigsAppTelemetryEventFlagsKey = "apptelemetry_event_flags";
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

        // STANDARD PATHS ============================================================================================
        // pyRevit %appdata% path
        // @reviewed
        public static string pyRevitAppDataPath =>
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                                          PyRevit.AppdataDirName);

        // pyRevit %programdata% path
        // @reviewed
        public static string pyRevitProgramDataPath =>
            Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                                          PyRevit.AppdataDirName);

        // pyRevit default extensions path
        // @reviewed
        public static string pyRevitDefaultExtensionsPath =>
            Path.Combine(pyRevitAppDataPath, PyRevit.ExtensionsDefaultDirName);

        // pyRevit config file path
        // @reviewed
        public static string pyRevitConfigFilePath {
            get {
                var cfgFile = PyRevitConfigs.FindConfigFileInDirectory(pyRevitAppDataPath);
                return cfgFile != null ? cfgFile : Path.Combine(pyRevitAppDataPath, PyRevit.DefaultConfigsFileName);
            }
        }

        // pyRevit config file path
        // @reviewed
        public static string pyRevitSeedConfigFilePath {
            get {
                var cfgFile = PyRevitConfigs.FindConfigFileInDirectory(pyRevitProgramDataPath);
                return cfgFile != null ? cfgFile : Path.Combine(pyRevitProgramDataPath,
                                                        PyRevit.DefaultConfigsFileName);
            }
        }

        // pyrevit logs folder 
        // @reviewed
        public static string GetLogsDirectory() {
            return Path.Combine(pyRevitAppDataPath, PyRevit.AppdataLogsDirName);
        }

    }
}


//from pyrevit import HOST_APP, EXEC_PARAMS

//# Extension types
//# ------------------------------------------------------------------------------
//LIB_EXTENSION_POSTFIX = '.lib'
//UI_EXTENSION_POSTFIX = '.extension'


//class UIExtensionType :
//    ID = 'extension'
//    POSTFIX = '.extension'


//class LIBExtensionType :
//    ID = 'lib'
//    POSTFIX = '.lib'


//class RUNExtensionType :
//    ID = 'run'
//    POSTFIX = '.run'


//class ExtensionTypes :
//    UI_EXTENSION = UIExtensionType
//    LIB_EXTENSION = LIBExtensionType
//    RUN_EXTENSION = RUNExtensionType

//    @classmethod
//    def get_ext_types(cls):
//        ext_types = set()
//        for attr in dir(cls):
//            if attr.endswith('_EXTENSION'):
//                ext_types.add(getattr(cls, attr))
//        return ext_types


//# -----------------------------------------------------------------------------
//# supported scripting languages
//PYTHON_LANG = 'python'
//CSHARP_LANG = 'csharp'
//VB_LANG = 'visualbasic'
//RUBY_LANG = 'ruby'
//DYNAMO_LANG = 'dynamobim'
//GRASSHOPPER_LANG = 'grasshopper'

//# supported script files
//PYTHON_SCRIPT_FILE_FORMAT = '.py'
//CSHARP_SCRIPT_FILE_FORMAT = '.cs'
//VB_SCRIPT_FILE_FORMAT = '.vb'
//RUBY_SCRIPT_FILE_FORMAT = '.rb'
//DYNAMO_SCRIPT_FILE_FORMAT = '.dyn'
//GRASSHOPPER_SCRIPT_FILE_FORMAT = '.gh'
//CONTENT_FILE_FORMAT = '.rfa'

//# extension startup script
//EXT_STARTUP_NAME = 'startup'
//EXT_STARTUP_FILE = EXT_STARTUP_NAME + PYTHON_SCRIPT_FILE_FORMAT

//# -----------------------------------------------------------------------------
//# supported metadata formats
//YAML_FILE_FORMAT = '.yaml'
//JSON_FILE_FORMAT = '.json'

//# metadata filenames
//EXT_MANIFEST_NAME = 'extension'
//EXT_MANIFEST_FILE = EXT_MANIFEST_NAME + YAML_FILE_FORMAT
//LEGACY_EXT_MANIFEST_FILE = EXT_MANIFEST_NAME + JSON_FILE_FORMAT

//DEFAULT_BUNDLEMATA_NAME = 'script'
//ALT_BUNDLEMATA_NAME = 'bundle'
//BUNDLEMATA_POSTFIX = DEFAULT_BUNDLEMATA_NAME + YAML_FILE_FORMAT
//ALT_BUNDLEMATA_POSTFIX = ALT_BUNDLEMATA_NAME + YAML_FILE_FORMAT

//# metadata schema: Exensions
//EXT_MANIFEST_TEMPLATES_KEY = 'templates'

//# metadata schema: Bundles
//MDATA_ICON_FILE = 'icon'
//MDATA_UI_TITLE = 'title'
//MDATA_TOOLTIP = 'tooltip'
//MDATA_AUTHOR = 'author'
//MDATA_AUTHORS = 'authors'
//MDATA_COMMAND_HELP_URL = 'help_url'
//MDATA_COMMAND_CONTEXT = 'context'
//MDATA_MIN_REVIT_VERSION = 'min_revit_version'
//MDATA_MAX_REVIT_VERSION = 'max_revit_version'
//MDATA_BETA_SCRIPT = 'is_beta'
//MDATA_ENGINE = 'engine'
//MDATA_ENGINE_CLEAN = 'clean'
//MDATA_ENGINE_FULLFRAME = 'full_frame'
//MDATA_ENGINE_PERSISTENT = 'persistent'
//MDATA_LINK_BUTTON_MODULES = 'modules'
//MDATA_LINK_BUTTON_ASSEMBLY = 'assembly'
//MDATA_LINK_BUTTON_COMMAND_CLASS = 'command_class'
//MDATA_CONTENT_BUTTON_ALT_CONTENT = 'alternate_content'

//# metadata schema: Bundles | legacy
//UI_TITLE_PARAM = '__title__'
//DOCSTRING_PARAM = '__doc__'
//AUTHOR_PARAM = '__author__'
//AUTHORS_PARAM = '__authors__'
//COMMAND_HELP_URL_PARAM = '__helpurl__'
//COMMAND_CONTEXT_PARAM = '__context__'
//MIN_REVIT_VERSION_PARAM = '__min_revit_ver__'
//MAX_REVIT_VERSION_PARAM = '__max_revit_ver__'
//SHIFT_CLICK_PARAM = '__shiftclick__'
//BETA_SCRIPT_PARAM = '__beta__'
//CLEAN_ENGINE_SCRIPT_PARAM = '__cleanengine__'
//FULLFRAME_ENGINE_PARAM = '__fullframeengine__'
//PERSISTENT_ENGINE_PARAM = '__persistentengine__'
//LINK_BUTTON_ASSEMBLY = '__assembly__'
//LINK_BUTTON_COMMAND_CLASS = '__commandclass__'

//# -----------------------------------------------------------------------------
//# supported bundles
//TAB_POSTFIX = '.tab'
//PANEL_POSTFIX = '.panel'
//LINK_BUTTON_POSTFIX = '.linkbutton'
//INVOKE_BUTTON_POSTFIX = '.invokebutton'
//PUSH_BUTTON_POSTFIX = '.pushbutton'
//TOGGLE_BUTTON_POSTFIX = '.toggle'
//SMART_BUTTON_POSTFIX = '.smartbutton'
//PULLDOWN_BUTTON_POSTFIX = '.pulldown'
//STACKTHREE_BUTTON_POSTFIX = '.stack3'
//STACKTWO_BUTTON_POSTFIX = '.stack2'
//SPLIT_BUTTON_POSTFIX = '.splitbutton'
//SPLITPUSH_BUTTON_POSTFIX = '.splitpushbutton'
//PANEL_PUSH_BUTTON_POSTFIX = '.panelbutton'
//NOGUI_COMMAND_POSTFIX = '.nobutton'
//CONTENT_BUTTON_POSTFIX = '.content'

//# known bundle sub-directories
//COMP_LIBRARY_DIR_NAME = 'lib'
//COMP_BIN_DIR_NAME = 'bin'
//COMP_HOOKS_DIR_NAME = 'hooks'

//# unique ids
//UNIQUE_ID_SEPARATOR = '-'

//# bundle layout elements
//DEFAULT_LAYOUT_FILE_NAME = '_layout'
//SEPARATOR_IDENTIFIER = '---'
//SLIDEOUT_IDENTIFIER = '>>>'

//# bundle icon
//ICON_FILE_FORMAT = '.png'
//DEFAULT_ICON_FILE = 'icon' + ICON_FILE_FORMAT
//DEFAULT_ON_ICON_FILE = 'on' + ICON_FILE_FORMAT
//DEFAULT_OFF_ICON_FILE = 'off' + ICON_FILE_FORMAT

//# bundle image for tooltips
//DEFAULT_TOOLTIP_IMAGE_FILE = 'tooltip.png'
//# bundle video for tooltips
//DEFAULT_TOOLTIP_VIDEO_FILE = 'tooltip.swf'
//if not EXEC_PARAMS.doc_mode and HOST_APP.is_newer_than(2019, or_equal=True):
//    DEFAULT_TOOLTIP_VIDEO_FILE = 'tooltip.mp4'

//# bundle scripts
//DEFAULT_SCRIPT_NAME = 'script'
//DEFAULT_CONFIG_NAME = 'config'

//# script files
//PYTHON_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + PYTHON_SCRIPT_FILE_FORMAT
//CSHARP_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + CSHARP_SCRIPT_FILE_FORMAT
//VB_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + VB_SCRIPT_FILE_FORMAT
//RUBY_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + RUBY_SCRIPT_FILE_FORMAT
//DYNAMO_SCRIPT_POSTFIX = DEFAULT_SCRIPT_NAME + DYNAMO_SCRIPT_FILE_FORMAT
//GRASSHOPPER_SCRIPT_POSTFIX = \
//    DEFAULT_SCRIPT_NAME + GRASSHOPPER_SCRIPT_FILE_FORMAT
//CONFIG_SCRIPT_POSTFIX = DEFAULT_CONFIG_NAME + PYTHON_SCRIPT_FILE_FORMAT
//CONTENT_POSTFIX = CONTENT_FILE_FORMAT

//# -----------------------------------------------------------------------------
//# Command bundle defaults
//CTX_SELETION = 'selection'
//CTX_ZERODOC = ['zero-doc', 'zerodoc']
