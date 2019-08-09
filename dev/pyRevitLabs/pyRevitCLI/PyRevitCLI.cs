using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Reflection;
using System.IO;
using System.Diagnostics;

using pyRevitCLI.Properties;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;

using DocoptNet;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.PyRevit;

using Console = Colorful.Console;


// NOTE:
// ## Add a new command:
// 1) Update docopt usage pattern file
// 2) Add new command to PyRevitCLICommandType
// 3) Update the logic in PyRevitCLI.ProcessArguments
// 4) Add command code and make sure PyRevitCLI.ProcessArguments correctly parses the arguments
// 5) Update AppHelps to accept and print help for new command type
// 6) Make sure PyRevitCLI.ProcessArguments checks and ask for help print
// 7) Update the pyrevit-complete.go file with command completion suggestions


namespace pyRevitCLI {

    internal enum PyRevitCLILogLevel {
        Quiet,
        InfoMessages,
        Debug,
    }

    internal enum PyRevitCLICommandType {
        Main,
        Version,
        Help,
        Blog,
        Docs,
        Source,
        YouTube,
        Support,
        Env,
        Clone,
        Clones,
        Attach,
        Attached,
        Switch,
        Detach,
        Extend,
        Extensions,
        ExtensionsPaths,
        ExtensionsSources,
        Releases,
        Image,
        Revits,
        RevitsAddons,
        Run,
        Init,
        Caches,
        Doctor,
        Config,
        Configs,
        Cli
    }

    internal static class PyRevitCLI {
        private static Logger logger = LogManager.GetCurrentClassLogger();

        // uage patterns
        internal static string UsagePatterns => Resources.UsagePatterns;

        // arguments dict
        private static IDictionary<string, ValueObject> arguments = null;

        internal static bool IsVersionMode = false;
        internal static bool IsHelpMode = false;
        internal static bool IsHelpUsagePatternMode = false;

        // cli version property
        public static Version CLIVersion => Assembly.GetExecutingAssembly().GetName().Version;

        // cli entry point:
        static void Main(string[] args) {

            // process arguments for logging level
            var argsList = new List<string>(args);

            // check for testing and set the global test flag
            if (argsList.Contains("--test")) {
                argsList.Remove("--test");
                GlobalConfigs.UnderTest = true;
            }

            // setup logger
            // process arguments for hidden debug mode switch
            PyRevitCLILogLevel logLevel = PyRevitCLILogLevel.InfoMessages;
            var config = new LoggingConfiguration();
            var logconsole = new ConsoleTarget("logconsole") { Layout = @"${level}: ${message} ${exception}" };
            config.AddTarget(logconsole);
            config.AddRule(LogLevel.Error, LogLevel.Fatal, logconsole);

            if (argsList.Contains("--verbose")) {
                argsList.Remove("--verbose");
                logLevel = PyRevitCLILogLevel.InfoMessages;
                config.AddRule(LogLevel.Info, LogLevel.Info, logconsole);
            }

            if (argsList.Contains("--debug")) {
                argsList.Remove("--debug");
                logLevel = PyRevitCLILogLevel.Debug;
                config.AddRule(LogLevel.Debug, LogLevel.Debug, logconsole);
            }

            // config logger
            LogManager.Configuration = config;

            try {
                // process docopt
                // docopt raises exception if pattern matching fails
                arguments = new Docopt().Apply(UsagePatterns, argsList, exit: false, help: false);

                // print active arguments in debug mode
                if (logLevel == PyRevitCLILogLevel.Debug)
                    PrintArguments(arguments);

                // setup output log
                if (arguments["--log"] != null) {
                    var logfile = new FileTarget("logfile") { FileName = arguments["--log"].Value as string };
                    config.AddTarget(logfile);
                    config.AddRuleForAllLevels(logfile);

                    arguments.Remove("--log");

                    // update logger config
                    LogManager.Configuration = config;
                }

                // check if requesting version
                IsVersionMode = arguments["--version"].IsTrue || arguments["-V"].IsTrue;

                // check if requesting help
                IsHelpMode = arguments["--help"].IsTrue || arguments["-h"].IsTrue;

                // check if requesting help with full usage patterns
                IsHelpUsagePatternMode = arguments["--usage"].IsTrue;

                try {
                    // now call methods based on inputs
                    ProcessArguments();

                    // process global error codes
                    ProcessErrorCodes();
                }
                catch (Exception ex) {
                    LogException(ex, logLevel);
                }

                // Flush and close down internal threads and timers
                LogManager.Shutdown();
            }
            catch (Exception ex) {
                // when docopt fails, print help
                logger.Debug("Arg processing failed. | {0}", ex.Message);
                PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Main);
            }
        }

        // cli argument processor
        private static void ProcessArguments() {
            if (IsHelpUsagePatternMode) Console.WriteLine(UsagePatterns.Replace("\t", "    "));

            else if (IsVersionMode) PyRevitCLIAppCmds.PrintVersion();

            else if (all("help")) PyRevitCLIAppHelps.OpenHelp();

            else if (all("blog")) CommonUtils.OpenUrl(PyRevit.BlogsUrl);

            else if (all("docs")) CommonUtils.OpenUrl(PyRevit.DocsUrl);

            else if (all("source")) CommonUtils.OpenUrl(PyRevit.SourceRepoUrl);

            else if (all("youtube")) CommonUtils.OpenUrl(PyRevit.YoutubeUrl);

            else if (all("support")) CommonUtils.OpenUrl(PyRevit.SupportUrl);

            else if (all("env")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Env);
                else
                    PyRevitCLIAppCmds.MakeEnvReport(json: arguments["--json"].IsTrue);
            }

            else if (all("clone")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Clone);
                else
                    PyRevitCLICloneCmds.CreateClone(
                        cloneName: TryGetValue("<clone_name>"),
                        deployName: TryGetValue("<deployment_name>"),
                        branchName: TryGetValue("--branch"),
                        repoUrl: TryGetValue("--source"),
                        imagePath: TryGetValue("--image"),
                        destPath: TryGetValue("--dest")
                    );
            }

            else if (all("clones")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Clones);

                else if (all("info"))
                    PyRevitCLICloneCmds.PrintCloneInfo(TryGetValue("<clone_name>"));

                else if (all("open"))
                    PyRevitCLICloneCmds.OpenClone(TryGetValue("<clone_name>"));

                else if (all("add"))
                    PyRevitCLICloneCmds.RegisterClone(
                        TryGetValue("<clone_name>"),
                        TryGetValue("<clone_path>"),
                        force: arguments["--force"].IsTrue
                        );

                else if (all("forget"))
                    PyRevitCLICloneCmds.ForgetClone(
                        allClones: arguments["--all"].IsTrue,
                        cloneName: TryGetValue("<clone_name>")
                        );

                else if (all("rename"))
                    PyRevitCLICloneCmds.RenameClone(
                        cloneName: TryGetValue("<clone_name>"),
                        cloneNewName: TryGetValue("<clone_new_name>")
                        );

                else if (all("delete"))
                    PyRevitCLICloneCmds.DeleteClone(
                        allClones: arguments["--all"].IsTrue,
                        cloneName: TryGetValue("<clone_name>"),
                        clearConfigs: arguments["--clearconfigs"].IsTrue
                        );

                else if (all("branch"))
                    PyRevitCLICloneCmds.GetSetCloneBranch(
                       cloneName: TryGetValue("<clone_name>"),
                       branchName: TryGetValue("<branch_name>")
                       );

                else if (all("version"))
                    PyRevitCLICloneCmds.GetSetCloneTag(
                       cloneName: TryGetValue("<clone_name>"),
                       tagName: TryGetValue("<tag_name>")
                       );

                else if (all("commit"))
                    PyRevitCLICloneCmds.GetSetCloneCommit(
                       cloneName: TryGetValue("<clone_name>"),
                       commitHash: TryGetValue("<commit_hash>")
                       );

                else if (all("origin"))
                    PyRevitCLICloneCmds.GetSetCloneOrigin(
                       cloneName: TryGetValue("<clone_name>"),
                       originUrl: TryGetValue("<origin_url>"),
                       reset: arguments["--reset"].IsTrue
                       );

                else if (all("deployments"))
                    PyRevitCLICloneCmds.PrintCloneDeployments(TryGetValue("<clone_name>"));

                else if (all("engines"))
                    PyRevitCLICloneCmds.PrintCloneEngines(TryGetValue("<clone_name>"));

                else if (all("update"))
                    PyRevitCLICloneCmds.UpdateClone(
                        allClones: arguments["--all"].IsTrue,
                        cloneName: TryGetValue("<clone_name>")
                        );

                else
                    PyRevitCLICloneCmds.PrintClones();
            }

            else if (all("attach")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Attach);
                else
                    PyRevitCLICloneCmds.AttachClone(
                        cloneName: TryGetValue("<clone_name>"),
                        latest: arguments["latest"].IsTrue,
                        dynamoSafe: arguments["dynamosafe"].IsTrue,
                        engineVersion: TryGetValue("<engine_version>"),
                        revitYear: TryGetValue("<revit_year>"),
                        installed: arguments["--installed"].IsTrue,
                        attached: arguments["--attached"].IsTrue,
                        allUsers: arguments["--allusers"].IsTrue
                        );
            }

            else if (all("detach")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Detach);
                else
                    PyRevitCLICloneCmds.DetachClone(
                        revitYear: TryGetValue("<revit_year>"),
                        all: arguments["--all"].IsTrue
                        );
            }

            else if (all("attached")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Attached);
                else
                    PyRevitCLICloneCmds.ListAttachments(revitYear: TryGetValue("<revit_year>"));
            }

            else if (all("switch")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Switch);
                else
                    PyRevitCLICloneCmds.SwitchAttachment(
                        cloneName: TryGetValue("<clone_name>"),
                        revitYear: TryGetValue("<revit_year>")
                        );
            }

            else if (all("extend")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Extend);

                else if (any("ui", "lib", "run"))
                    PyRevitCLIExtensionCmds.Extend(
                        ui: arguments["ui"].IsTrue,
                        lib: arguments["lib"].IsTrue,
                        run: arguments["run"].IsTrue,
                        extName: TryGetValue("<extension_name>"),
                        destPath: TryGetValue("--dest"),
                        repoUrl: TryGetValue("<repo_url>"),
                        branchName: TryGetValue("--branch")
                        );

                else
                    PyRevitCLIExtensionCmds.Extend(
                        extName: TryGetValue("<extension_name>"),
                        destPath: TryGetValue("--dest"),
                        branchName: TryGetValue("--branch")
                        );
            }

            else if (all("extensions")) {
                if (all("search"))
                    PyRevitCLIExtensionCmds.PrintExtensionDefinitions(
                        searchPattern: TryGetValue("<search_pattern>"),
                        headerPrefix: "Matched"
                    );

                else if (any("info", "help", "open"))
                    PyRevitCLIExtensionCmds.ProcessExtensionInfoCommands(
                        extName: TryGetValue("<extension_name>"),
                        info: arguments["info"].IsTrue,
                        help: arguments["help"].IsTrue,
                        open: arguments["open"].IsTrue
                    );

                else if (all("delete"))
                    PyRevitCLIExtensionCmds.DeleteExtension(TryGetValue("<extension_name>"));

                else if (all("origin"))
                    PyRevitCLIExtensionCmds.GetSetExtensionOrigin(
                        extName: TryGetValue("<extension_name>"),
                        originUrl: TryGetValue("<origin_url>"),
                        reset: arguments["--reset"].IsTrue
                        );

                else if (all("paths")) {
                    if (IsHelpMode)
                        PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.ExtensionsPaths);

                    else if (all("add"))
                        PyRevitCLIExtensionCmds.AddExtensionPath(
                            searchPath: TryGetValue("<extensions_path>")
                        );

                    else if (all("forget"))
                        PyRevitCLIExtensionCmds.ForgetAllExtensionPaths(
                            all: arguments["--all"].IsTrue,
                            searchPath: TryGetValue("<extensions_path>")
                        );

                    else
                        PyRevitCLIExtensionCmds.PrintExtensionSearchPaths();
                }

                else if (any("enable", "disable"))
                    PyRevitCLIExtensionCmds.ToggleExtension(
                        enable: arguments["enable"].IsTrue,
                        extName: TryGetValue("<extension_name>")
                    );

                else if (all("sources")) {
                    Console.WriteLine("dfsdfsd");
                    if (IsHelpMode)
                        PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.ExtensionsSources);

                    else if (all("add"))
                        PyRevitCLIExtensionCmds.AddExtensionLookupSource(
                            lookupPath: TryGetValue("<source_json_or_url>")
                        );

                    else if (all("forget"))
                        PyRevitCLIExtensionCmds.ForgetExtensionLookupSources(
                            all: arguments["--all"].IsTrue,
                            lookupPath: TryGetValue("<source_json_or_url>")
                        );

                    else
                        PyRevitCLIExtensionCmds.PrintExtensionLookupSources();
                }

                else if (all("update"))
                    PyRevitCLIExtensionCmds.UpdateExtension(
                        all: arguments["--all"].IsTrue,
                        extName: TryGetValue("<extension_name>")
                    );

                else if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Extensions);

                else
                    PyRevitCLIExtensionCmds.PrintExtensions();
            }

            else if (all("releases")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Releases);

                else if (all("open"))
                    PyRevitCLIReleaseCmds.OpenReleasePage(
                        searchPattern: TryGetValue("<search_pattern>"),
                        latest: arguments["latest"].IsTrue,
                        listPreReleases: arguments["--pre"].IsTrue
                        );

                else if (all("download"))
                    PyRevitCLIReleaseCmds.DownloadReleaseAsset(
                        arguments["archive"].IsTrue ? PyRevitReleaseAssetType.Archive : PyRevitReleaseAssetType.Installer,
                        destPath: TryGetValue("--dest"),
                        searchPattern: TryGetValue("<search_pattern>"),
                        latest: arguments["latest"].IsTrue,
                        listPreReleases: arguments["--pre"].IsTrue
                        );

                else
                    PyRevitCLIReleaseCmds.PrintReleases(
                        searchPattern: TryGetValue("<search_pattern>"),
                        latest: arguments["latest"].IsTrue,
                        printReleaseNotes: arguments["--notes"].IsTrue,
                        listPreReleases: arguments["--pre"].IsTrue
                        );
            }

            else if (all("image")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Image);
                else
                    PyRevitCLICloneCmds.BuildImage(
                        cloneName: TryGetValue("<clone_name>"),
                        configFile: TryGetValue("--config"),
                        imageFilePath: TryGetValue("--dest")
                        );
            }

            else if (all("revits")) {
                if (all("killall"))
                    PyRevitCLIRevitCmds.KillAllRevits(
                        revitYear: TryGetValue("<revit_year>")
                    );

                else if (all("fileinfo"))
                    PyRevitCLIRevitCmds.ProcessFileInfo(
                        targetPath: TryGetValue("<file_or_dir_path>"),
                        outputCSV: TryGetValue("--csv"),
                        IncludeRVT: arguments["--rvt"].IsTrue,
                        includeRTE: arguments["--rte"].IsTrue,
                        includeRFA: arguments["--rfa"].IsTrue,
                        includeRFT: arguments["--rft"].IsTrue
                        );

                else if (all("addons")) {
                    if (IsHelpMode)
                        PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.RevitsAddons);

                    else if (all("prepare"))
                        PyRevitCLIRevitCmds.PrepareAddonsDir(
                            revitYear: TryGetValue("<revit_year>"),
                            allUses: arguments["--allusers"].IsTrue
                            );

                    else if (any("install", "uninstall"))
                        // TODO: implement revit addon manager
                        logger.Error("Revit addon manager is not implemented yet");
                }

                else if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Revits);

                else if (arguments["--supported"].IsTrue)
                    PyRevitCLIRevitCmds.ProcessBuildInfo(
                        outputCSV: TryGetValue("--csv")
                        );

                else
                    PyRevitCLIRevitCmds.PrintLocalRevits(running: arguments["--installed"].IsFalse);
            }

            else if (all("run")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Run);
                else
                    PyRevitCLIRevitCmds.RunPythonCommand(
                        inputCommand: TryGetValue("<script_or_command_name>"),
                        targetFile: TryGetValue("<model_file>"),
                        revitYear: TryGetValue("--revit"),
                        runOptions: new PyRevitRunnerOptions() {
                            PurgeTempFiles = arguments["--purge"].IsTrue,
                            ImportPath = TryGetValue("--import", null)
                        }
                    );
            }

            else if (all("init")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Init);

                else if (any("ui", "lib", "run"))
                    PyRevitCLLInitCmds.InitExtension(
                        ui: arguments["ui"].IsTrue,
                        lib: arguments["lib"].IsTrue,
                        run: arguments["run"].IsTrue,
                        extensionName: TryGetValue("<extension_name>"),
                        templatesDir: TryGetValue("--templates"),
                        useTemplate: arguments["--usetemplate"].IsTrue
                        );

                else if (any("tab", "panel", "panelopt", "pull", "split", "splitpush", "push", "smart", "command"))
                    PyRevitCLLInitCmds.InitBundle(
                        tab: arguments["tab"].IsTrue,
                        panel: arguments["panel"].IsTrue,
                        panelopt: arguments["panelopt"].IsTrue,
                        pull: arguments["pull"].IsTrue,
                        split: arguments["split"].IsTrue,
                        splitpush: arguments["splitpush"].IsTrue,
                        push: arguments["push"].IsTrue,
                        smart: arguments["smart"].IsTrue,
                        command: arguments["command"].IsTrue,
                        bundleName: TryGetValue("<bundle_name>"),
                        templatesDir: TryGetValue("--templates"),
                        useTemplate: arguments["--usetemplate"].IsTrue
                        );
            }

            else if (all("caches")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Caches);

                else if (all("clear"))
                    PyRevitCLIAppCmds.ClearCaches(
                        allCaches: arguments["--all"].IsTrue,
                        revitYear: TryGetValue("<revit_year>")
                        );
            }

            else if (all("doctor")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Doctor);

                else
                    PyRevitCLIAppCmds.InspectAndFixEnv();
            }

            else if (all("config")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Config);
                else
                    PyRevitCLIConfigCmds.SeedConfigs(
                        templateConfigFilePath: TryGetValue("<template_config_path>")
                    );
            }

            else if (all("configs")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Configs);

                else if (all("logs"))
                    Console.WriteLine(string.Format("Logging Level is {0}", PyRevitConfigs.GetLoggingLevel().ToString()));

                else if (all("logs", "none"))
                    PyRevitConfigs.SetLoggingLevel(PyRevitLogLevels.None);

                else if (all("logs", "verbose"))
                    PyRevitConfigs.SetLoggingLevel(PyRevitLogLevels.Verbose);

                else if (all("logs", "debug"))
                    PyRevitConfigs.SetLoggingLevel(PyRevitLogLevels.Debug);

                // TODO: Implement allowremotedll
                else if (all("allowremotedll"))
                    throw new NotImplementedException();

                else if (all("checkupdates")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetCheckUpdates(arguments["enable"].IsTrue);
                    else
                        Console.WriteLine(string.Format("Check Updates is {0}",
                                                        PyRevitConfigs.GetCheckUpdates() ? "Enabled" : "Disabled"));
                }

                else if (all("autoupdate")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetAutoUpdate(arguments["enable"].IsTrue);
                    else
                        Console.WriteLine(string.Format("Auto Update is {0}",
                                                        PyRevitConfigs.GetAutoUpdate() ? "Enabled" : "Disabled"));
                }

                else if (all("rocketmode")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetRocketMode(arguments["enable"].IsTrue);
                    else
                        Console.WriteLine(string.Format("Rocket Mode is {0}",
                                                        PyRevitConfigs.GetRocketMode() ? "Enabled" : "Disabled"));
                }

                else if (all("filelogging")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetFileLogging(arguments["enable"].IsTrue);
                    else
                        Console.WriteLine(string.Format("File Logging is {0}",
                                                        PyRevitConfigs.GetFileLogging() ? "Enabled" : "Disabled"));
                }


                else if (all("loadbeta")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetLoadBetaTools(arguments["enable"].IsTrue);
                    else
                        Console.WriteLine(string.Format("Load Beta is {0}",
                                                        PyRevitConfigs.GetLoadBetaTools() ? "Enabled" : "Disabled"));
                }

                else if (all("usercanupdate")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetUserCanUpdate(arguments["Yes"].IsTrue);
                    else
                        Console.WriteLine(string.Format("User {0} update.",
                                                        PyRevitConfigs.GetUserCanUpdate() ? "CAN" : "CAN NOT"));
                }


                else if (all("usercanextend")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetUserCanExtend(arguments["Yes"].IsTrue);
                    else
                        Console.WriteLine(string.Format("User {0} extend.",
                                                        PyRevitConfigs.GetUserCanExtend() ? "CAN" : "CAN NOT"));
                }


                else if (all("usercanconfig")) {
                    if (any("enable", "disable"))
                        PyRevitConfigs.SetUserCanConfig(arguments["Yes"].IsTrue);
                    else
                        Console.WriteLine(string.Format("User {0} config.",
                                                        PyRevitConfigs.GetUserCanConfig() ? "CAN" : "CAN NOT"));

                }

                else if (all("telemetry")) {
                    if (all("enable", "file"))
                        PyRevitConfigs.EnableTelemetry(telemetryFilePath: TryGetValue("<dest_path>"));

                    else if (all("enable", "server"))
                        PyRevitConfigs.EnableTelemetry(telemetryServerUrl: TryGetValue("<dest_path>"));

                    else if (all("disable"))
                        PyRevitConfigs.DisableTelemetry();

                    else {
                        Console.WriteLine(string.Format("Telemetry is {0}",
                                                        PyRevitConfigs.GetTelemetryStatus() ? "Enabled" : "Disabled"));
                        Console.WriteLine(string.Format("Log File Path: {0}", PyRevitConfigs.GetTelemetryFilePath()));
                        Console.WriteLine(string.Format("Log Server Url: {0}", PyRevitConfigs.GetTelemetryServerUrl()));
                    }
                }

                else if (all("outputcss")) {
                    if (arguments["<css_path>"] == null)
                        Console.WriteLine(string.Format("Output Style Sheet is set to: {0}",
                                                        PyRevitConfigs.GetOutputStyleSheet()));
                    else
                        PyRevitConfigs.SetOutputStyleSheet(TryGetValue("<css_path>"));
                }

                else if (all("seed"))
                    PyRevitConfigs.SeedConfig(makeCurrentUserAsOwner: arguments["--lock"].IsTrue);

                else if (all("enable", "disable")) {
                    if (arguments["<option_path>"] != null) {
                        // extract section and option names
                        string orignalOptionValue = TryGetValue("<option_path>");
                        if (orignalOptionValue.Split(':').Count() == 2) {
                            string configSection = orignalOptionValue.Split(':')[0];
                            string configOption = orignalOptionValue.Split(':')[1];

                            PyRevitConfigs.SetConfig(configSection, configOption, arguments["enable"].IsTrue);
                        }
                    }
                }

                else {
                    if (arguments["<option_path>"] != null) {
                        // extract section and option names
                        string orignalOptionValue = TryGetValue("<option_path>");
                        if (orignalOptionValue.Split(':').Count() == 2) {
                            string configSection = orignalOptionValue.Split(':')[0];
                            string configOption = orignalOptionValue.Split(':')[1];

                            // if no value provided, read the value
                            if (arguments["<option_value>"] != null)
                                PyRevitConfigs.SetConfig(
                                    configSection,
                                    configOption,
                                    TryGetValue("<option_value>")
                                    );
                            else if (arguments["<option_value>"] == null)
                                Console.WriteLine(
                                    string.Format("{0} = {1}",
                                    configOption,
                                    PyRevitConfigs.GetConfig(configSection, configOption)
                                    ));
                        }
                    }
                }
            }

            else if (all("cli")) {
                if (IsHelpMode)
                    PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Cli);

                else if (all("addshortcut"))
                    PyRevitCLIAppCmds.AddCLIShortcut(
                        shortcutName: TryGetValue("<shortcut_name>"),
                        shortcutArgs: TryGetValue("<shortcut_args>"),
                        shortcutDesc: TryGetValue("--desc"),
                        allUsers: arguments["--allusers"].IsTrue
                    );
            }

            else if (IsHelpMode) PyRevitCLIAppHelps.PrintHelp(PyRevitCLICommandType.Main);
        }

        // internal helper functions:
        private static bool all(params string[] keywords) {
            logger.Debug("Checking for all: {0}", string.Join(",", keywords));
            foreach (var keyword in keywords)
                if (!arguments.ContainsKey(keyword) || !arguments[keyword].IsTrue) {
                    logger.Debug("Missing: {0}", keyword);
                    return false;
                }
            return true;
        }

        private static bool any(params string[] keywords) {
            logger.Debug("Checking for any: {0}", string.Join(",", keywords));
            foreach (var keyword in keywords)
                if (arguments[keyword].IsTrue) {
                    logger.Debug("Matching: {0}", keyword);
                    return true;
                }
            return false;
        }

        internal static string TryGetValue(string key, string defaultValue = null) {
            return arguments[key] != null ? arguments[key].Value as string : defaultValue;
        }

        // private:
        private static void PrintArguments(IDictionary<string, ValueObject> arguments) {
            var activeArgs = arguments.Where(x => x.Value != null && (x.Value.IsTrue || x.Value.IsString));
            foreach (var arg in activeArgs)
                Console.WriteLine("{0} = {1}", arg.Key, arg.Value.ToString());
        }

        private static void ProcessErrorCodes() {
        }

        private static void LogException(Exception ex, PyRevitCLILogLevel logLevel) {
            if (logLevel == PyRevitCLILogLevel.Debug)
                logger.Error(string.Format("{0} ({1})\n{2}", ex.Message, ex.GetType().ToString(), ex.StackTrace));
            else
                logger.Error(string.Format("{0}\nRun with \"--debug\" option to see debug messages", ex.Message));
        }
    }
}
