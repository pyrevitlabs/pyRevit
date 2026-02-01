using System;
using System.Collections.Generic;

using Autodesk.Revit.Attributes;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using IronPython.Runtime;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;
using PyRevitLabs.PyRevit.Runtime;

using System.Reflection;
using System.IO;

namespace PyRevitRunner {
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public class PyRevitRunnerCommand : IExternalCommand {

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements) {
            // grab application and command data, skip elements since this is a batch runner and user doesn't 
            // see the gui to make selections
            Application = commandData.Application;
            CommandData = commandData;

            try {
                // 1
                // Processing Journal Data and getting the script path to be executed
                IDictionary<string, string> dataMap = commandData.JournalData;
                ScriptSourceFile = dataMap["ScriptSource"];
                ModuleSearchPaths = new List<string>();
                if (dataMap.TryGetValue("SearchPaths", out var searchPaths))
                    AddSearchPaths(ModuleSearchPaths, searchPaths);
                ModelPaths = new List<string>();
                if (dataMap.TryGetValue("Models", out var modelPaths) && !string.IsNullOrEmpty(modelPaths))
                    ModelPaths.AddRange(modelPaths.Split(';'));
                LogFile = dataMap.TryGetValue("LogFile", out var logFile) ? logFile : null;
                dataMap.TryGetValue("EngineConfigs", out var engineConfigs);

                // add pyrevit library path and script directory path to search paths
                ModuleSearchPaths.Add(GetPyRevitLibsPath());
                ModuleSearchPaths.Add(GetSitePkgsPath());
                var scriptDirectory = Path.GetDirectoryName(ScriptSourceFile);
                if (!string.IsNullOrEmpty(scriptDirectory))
                    ModuleSearchPaths.Add(scriptDirectory);

                EnsureLogFile(LogFile);
                SeedEnvDictionary(Application);

                // 2
                // Executing the script via runtime dispatcher
                ScriptExecutor.Initialize();
                var scriptData = BuildScriptData(ScriptSourceFile);
                var runtimeConfigs = new ScriptRuntimeConfigs {
                    CommandData = commandData,
                    SelectedElements = elements,
                    SearchPaths = ModuleSearchPaths,
                    Arguments = new List<string>(),
                    EngineConfigs = NormalizeEngineConfigs(engineConfigs),
                    DebugMode = false,
                    ConfigMode = false,
                    RefreshEngine = false,
                    ExecutedFromUI = false
                };
                try {
                    var logFilePathProp = typeof(ScriptRuntimeConfigs).GetProperty("LogFilePath");
                    if (logFilePathProp != null) logFilePathProp.SetValue(runtimeConfigs, LogFile);
                    
                    var suppressOutputProp = typeof(ScriptRuntimeConfigs).GetProperty("SuppressOutput");
                    if (suppressOutputProp != null) suppressOutputProp.SetValue(runtimeConfigs, true);
                    
                    var variablesProp = typeof(ScriptRuntimeConfigs).GetProperty("Variables");
                    if (variablesProp != null) {
                        variablesProp.SetValue(runtimeConfigs, new Dictionary<string, object>() {
                            {"__batchexec__",  true },
                            {"__logfile__", LogFile ?? string.Empty },
                            {"__models__", ModelPaths },
                        });
                    }
                } catch {
                    // Properties not available in this version of ScriptRuntimeConfigs
                }

                var env = new EnvDictionary();
                var resultCode = ScriptExecutor.ExecuteScript(
                    scriptData,
                    runtimeConfigs,
                    new ScriptExecutorConfigs { SendTelemetry = env.TelemetryState }
                    );

                // 3
                // Log results
                if (resultCode == ScriptExecutorResultCodes.Succeeded)
                    return Result.Succeeded;
                else
                    return Result.Cancelled;
            }
            catch (Exception ex) {
                LogRunnerError(LogFile, ex);
                commandData.JournalData.Add("pyRevitRunner Execution Failure", ex.Message);
                return Result.Cancelled;
            }
        }

        public UIApplication Application { get; private set; }
        public ExternalCommandData CommandData { get; private set; }

        public string ScriptSourceFile { get; private set; }
        public List<string> ModuleSearchPaths { get; private set; }
        public List<string> ModelPaths { get; private set; }
        public string LogFile { get; private set; }
        public bool DebugMode { get; private set; }

        private static string GetDeployPath() {
            var loaderDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var engineDir = Path.GetDirectoryName(loaderDir);
            var runtimeDir = Path.GetDirectoryName(engineDir); // netcore or netfx
            var binDir = Path.GetDirectoryName(runtimeDir);
            return Path.GetDirectoryName(binDir);
        }

        private static string GetPyRevitLibsPath() => Path.Combine(GetDeployPath(), "pyrevitlib");
        private static string GetSitePkgsPath() => Path.Combine(GetDeployPath(), "site-packages");

        private static void AddSearchPaths(List<string> searchPaths, string rawPaths) {
            if (string.IsNullOrWhiteSpace(rawPaths))
                return;

            foreach (var searchPath in rawPaths.Split(';')) {
                if (!string.IsNullOrWhiteSpace(searchPath))
                    searchPaths.Add(searchPath);
            }
        }

        private static ScriptData BuildScriptData(string scriptPath) {
            var scriptDir = Path.GetDirectoryName(scriptPath);
            var commandName = Path.GetFileNameWithoutExtension(scriptPath) ?? string.Empty;
            var commandBundle = scriptDir != null ? Path.GetFileName(scriptDir) : string.Empty;

            return new ScriptData {
                ScriptPath = scriptPath,
                ConfigScriptPath = scriptPath,
                CommandUniqueId = Guid.NewGuid().ToString(),
                CommandControlId = commandName,
                CommandName = commandName,
                CommandBundle = commandBundle,
                CommandExtension = string.Empty,
                CommandContext = string.Empty,
                HelpSource = string.Empty,
                Tooltip = string.Empty
            };
        }

        private static string NormalizeEngineConfigs(string engineConfigsRaw) {
            JObject configs = new JObject();
            if (!string.IsNullOrWhiteSpace(engineConfigsRaw)) {
                try {
                    configs = JObject.Parse(engineConfigsRaw);
                }
                catch (Exception ex) {
                    // Best-effort: invalid JSON falls back to defaults.
                    System.Diagnostics.Debug.WriteLine(
                        string.Format("[PyRevitRunner] Failed to parse EngineConfigs JSON: {0}", ex)
                    );
                    configs = new JObject();
                }
            }

            // Set default values if not specified
            if (!configs.ContainsKey("full_frame"))
                configs["full_frame"] = false;
            if (!configs.ContainsKey("clean"))
                configs["clean"] = false;
            if (!configs.ContainsKey("persistent"))
                configs["persistent"] = false;

            return configs.ToString(Formatting.None);
        }

        private static void EnsureLogFile(string logFilePath) {
            if (string.IsNullOrWhiteSpace(logFilePath))
                return;

            try {
                var logDir = Path.GetDirectoryName(logFilePath);
                if (!string.IsNullOrEmpty(logDir))
                    Directory.CreateDirectory(logDir);
                File.WriteAllText(logFilePath, string.Empty);
            }
            catch (Exception ex) {
                // Best-effort: log file setup should not fail the runner.
                System.Diagnostics.Debug.WriteLine(
                    string.Format("[PyRevitRunner] Failed to initialize log file '{0}': {1}", logFilePath, ex)
                );
            }
        }

        private static void LogRunnerError(string logFilePath, Exception ex) {
            if (string.IsNullOrWhiteSpace(logFilePath))
                return;

            try {
                File.AppendAllText(logFilePath, ex.ToString());
            }
            catch (Exception exInner) {
                // Best-effort: do not throw while writing the runner error log.
                System.Diagnostics.Debug.WriteLine(
                    string.Format("[PyRevitRunner] Failed to append runner error to '{0}': {1}", logFilePath, exInner)
                );
            }
        }

        private static void SeedEnvDictionary(UIApplication uiApp) {
            var envData = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey) as PythonDictionary;
            if (envData == null)
                envData = new PythonDictionary();

            var revitVersion = uiApp?.Application?.VersionNumber ?? string.Empty;
            var revitYear = 0;
            if (!string.IsNullOrEmpty(revitVersion))
                int.TryParse(revitVersion, out revitYear);

            PyRevitAttachment attachment = null;
            if (revitYear != 0)
                attachment = PyRevitAttachments.GetAttached(revitYear);

            var cloneName = attachment?.Clone?.Name ?? "Unknown";
            var pyRevitVersion = attachment?.Clone?.ModuleVersion ?? "Unknown";
            var ipyVersion = attachment?.Engine != null ? attachment.Engine.Version.Version.ToString() : "0";
            var cpyVersion = PyRevitConfigs.GetCpythonEngineVersion().ToString();

            envData[EnvDictionaryKeys.SessionUUID] = Guid.NewGuid().ToString();
            envData[EnvDictionaryKeys.RevitVersion] = revitVersion;
            envData[EnvDictionaryKeys.Version] = pyRevitVersion;
            envData[EnvDictionaryKeys.Clone] = cloneName;
            envData[EnvDictionaryKeys.IPYVersion] = ipyVersion;
            envData[EnvDictionaryKeys.CPYVersion] = cpyVersion;

            envData[EnvDictionaryKeys.LoggingLevel] = (int)PyRevitConfigs.GetLoggingLevel();
            envData[EnvDictionaryKeys.FileLogging] = PyRevitConfigs.GetFileLogging();

            envData[EnvDictionaryKeys.TelemetryUTCTimeStamps] = PyRevitConfigs.GetUTCStamps();
            envData[EnvDictionaryKeys.TelemetryState] = PyRevitConfigs.GetTelemetryStatus();
            envData[EnvDictionaryKeys.TelemetryFilePath] = PyRevitConfigs.GetTelemetryFilePath();
            envData[EnvDictionaryKeys.TelemetryServerUrl] = PyRevitConfigs.GetTelemetryServerUrl();
            envData[EnvDictionaryKeys.TelemetryIncludeHooks] = PyRevitConfigs.GetTelemetryIncludeHooks();

            envData[EnvDictionaryKeys.AppTelemetryState] = PyRevitConfigs.GetAppTelemetryStatus();
            envData[EnvDictionaryKeys.AppTelemetryServerUrl] = PyRevitConfigs.GetAppTelemetryServerUrl();
            envData[EnvDictionaryKeys.AppTelemetryEventFlags] = PyRevitConfigs.GetAppTelemetryFlags();

            envData[EnvDictionaryKeys.AutoUpdating] = PyRevitConfigs.GetAutoUpdate();
            envData[EnvDictionaryKeys.OutputStyleSheet] = PyRevitConfigs.GetOutputStyleSheet();

            if (!envData.Contains(EnvDictionaryKeys.Hooks))
                envData[EnvDictionaryKeys.Hooks] = new Dictionary<string, Dictionary<string, string>>();

            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnvVarsDictKey, envData);
        }
    }


    public class PyRevitRunnerCommandAvail : IExternalCommandAvailability {
        public PyRevitRunnerCommandAvail() {
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) {
            return true;
        }
    }

}
