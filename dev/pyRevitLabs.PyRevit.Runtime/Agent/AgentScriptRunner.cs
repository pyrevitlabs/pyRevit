using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Object handed to the in-engine runner (<c>pyrevit.agent._runner</c>) as
    /// <c>__agent__</c>. The runner reads the request from it and writes the outcome back.
    /// </summary>
    /// <remarks>
    /// Public because both IronPython and pythonnet only bind public members.
    /// </remarks>
    public sealed class AgentScriptContext {
        public AgentScriptContext(
            UIApplication uiApp, string runId, string mode, string source, string inputsJson, string workspace,
            double timeoutSeconds, bool reckless = false) {
            UIApp = uiApp;
            TimeoutSeconds = timeoutSeconds;
            Reckless = reckless;
            Workspace = workspace;
            RunId = runId;
            Mode = mode;
            Source = source;
            InputsJson = inputsJson;
        }

        public UIApplication UIApp { get; }
        public string RunId { get; }
        public string Mode { get; }
        public string Source { get; }
        public string InputsJson { get; }

        /// <summary>
        /// Folder the agent keeps shared modules in, or null. The runner puts it on
        /// <c>sys.path</c> for the run and re-imports its modules fresh.
        /// </summary>
        public string Workspace { get; }

        /// <summary>
        /// Seconds the runner lets the script run before raising a timeout inside it.
        /// </summary>
        public double TimeoutSeconds { get; }

        /// <summary>
        /// Whether the runner skips its in-script checks for this run: no timeout, no loop or
        /// handler rewriting, no trace function. Set by the host from <c>[agent] reckless</c>
        /// before the script starts, so a script can't turn it on for its own run.
        /// </summary>
        public bool Reckless { get; }

        public string ResultJson { get; private set; }
        public string Output { get; private set; } = string.Empty;
        public string ErrorType { get; private set; }
        public string ErrorMessage { get; private set; }
        public string ErrorTraceback { get; private set; }

        public string EngineImplementation { get; private set; }
        public string EnginePythonVersion { get; private set; }
        public string EngineVersionText { get; private set; }

        public bool HasError => ErrorType != null;

        public void SetEngine(string implementation, string pythonVersion, string versionText) {
            EngineImplementation = implementation;
            EnginePythonVersion = pythonVersion;
            EngineVersionText = versionText;
        }

        public void SetResult(string json) {
            ResultJson = json;
        }

        public void SetOutput(string text) {
            Output = text ?? string.Empty;
        }

        public void SetError(string type, string message, string traceback) {
            ErrorType = type;
            ErrorMessage = message;
            ErrorTraceback = traceback;
        }

        internal AgentRunTimings Timings { get; set; }

        /// <summary>
        /// Records how long one runner phase took; it appears under <c>timings_ms</c> in the
        /// run record as <c>script.&lt;phase&gt;</c>.
        /// </summary>
        public void ReportTiming(string phase, double milliseconds) {
            Timings?.Add("script." + phase, milliseconds);
        }
    }

    /// <summary>
    /// Runs agent source through the regular pyRevit <see cref="ScriptExecutor"/> so agent
    /// scripts get the same engines, builtins and search paths as commands.
    /// </summary>
    /// <remarks>
    /// Invariant: must be called on the Revit main thread (inside the dispatcher), so
    /// <see cref="ScriptExecutor.ExecuteScript"/> runs the script immediately instead of
    /// raising its own ExternalEvent.
    /// </remarks>
    internal static class AgentScriptRunner {
        private const string EntryFileName = "agent_entry.py";
        private const string AgentExtensionName = "pyRevitAgent";
        /// <remarks>
        /// The engine is reused between runs and pyrevitlib is loaded live, so a runner module
        /// imported before its file changed on disk is dropped and imported again. Otherwise the
        /// run executes the old code while tracebacks quote the lines of the new file. The file's
        /// size is compared with its modification time, which IronPython 2.7 reports in whole
        /// seconds, so an edit saved in the second of the import is still seen.
        /// Invariant: the warm-up imports the runner through this same block, so the first run
        /// finds the stamp it checks and keeps the warmed module instead of importing it again.
        /// </remarks>
        private const string RunnerImport =
            "import importlib\n" +
            "import os\n" +
            "import sys\n" +
            "def _file_stamp(module):\n" +
            "    info = os.stat(module.__file__)\n" +
            "    return (info.st_mtime, info.st_size)\n" +
            "_loaded = sys.modules.get('pyrevit.agent._runner')\n" +
            "if _loaded is not None and getattr(_loaded, '__agent_stamp__', None) != _file_stamp(_loaded):\n" +
            "    del sys.modules['pyrevit.agent._runner']\n" +
            "_runner = importlib.import_module('pyrevit.agent._runner')\n" +
            "_runner.__agent_stamp__ = _file_stamp(_runner)\n";

        private const string WarmUpSource = RunnerImport + "_runner.warm_up()\n";

        /// <summary>
        /// Starts the IronPython engine agent runs use, imports the runner into it and runs
        /// <c>_runner.warm_up</c>, so the first run finds the engine, the runner and its code
        /// paths ready. No transaction, document access, run record or output.
        /// </summary>
        /// <remarks>
        /// The entry script is a file of this process's own, deleted after it ran (see
        /// <see cref="AgentEngineWarmUp.WithEntryScript"/>), so Revit processes warming at the
        /// same time never share a half-written file.
        /// Invariant: the engine is set up by the same <see cref="CreateScriptData"/> and
        /// <see cref="CreateRuntimeConfigs"/> as <see cref="Execute"/>, so it is cached under the
        /// key a real run asks for and with the same flags. Any difference makes the first run
        /// start an engine of its own.
        /// </remarks>
        /// <returns>The <see cref="ScriptExecutorResultCodes"/> value of the warm-up script.</returns>
        public static int WarmUp(UIApplication uiApp, IList<string> searchPaths) {
            return AgentEngineWarmUp.WithEntryScript(
                AgentPaths.RootDir, System.Diagnostics.Process.GetCurrentProcess().Id, WarmUpSource,
                entryPath => ScriptExecutor.ExecuteScript(
                    CreateScriptData(entryPath, "Agent: engine warm-up"),
                    CreateRuntimeConfigs(uiApp, AgentEngine.IronPython, searchPaths, new Dictionary<string, object>())));
        }

        /// <summary>
        /// Whether this session load already has the IronPython engine agent runs use.
        /// </summary>
        public static bool IsIronPythonEngineCached() {
            var typeId = ScriptEngine.BuildTypeId(
                new EnvDictionary().SessionUUID, ScriptEngineType.IronPython, AgentExtensionName);
            return ScriptEngineManager.EngineDict.ContainsKey(typeId);
        }

        private static ScriptData CreateScriptData(string entryPath, string commandName) {
            return new ScriptData {
                ScriptPath = entryPath,
                ConfigScriptPath = null,
                CommandUniqueId = "pyrevit-agent",
                CommandName = commandName,
                CommandBundle = string.Empty,
                CommandExtension = AgentExtensionName,
                HelpSource = string.Empty,
            };
        }

        private static ScriptRuntimeConfigs CreateRuntimeConfigs(
            UIApplication uiApp, AgentEngine engine, IList<string> searchPaths, Dictionary<string, object> variables) {
            return new ScriptRuntimeConfigs {
                UIApp = uiApp,
                SearchPaths = new List<string>(searchPaths),
                Arguments = new List<string>(),
                Variables = variables,
                SuppressOutput = true,
                EngineConfigs = engine == AgentEngine.CPython
                    ? "{\"type\":\"CPython\",\"type_explicit\":true,\"clean\":false}"
                    : "{\"type\":\"IronPython\",\"type_explicit\":true,\"clean\":false,\"full_frame\":true,\"persistent\":false}",
                RefreshEngine = false,
                ConfigMode = false,
                DebugMode = false,
                ExecutedFromUI = false,
            };
        }

        /// <summary>
        /// Writes the run's entry script and executes it on the agent engine.
        /// </summary>
        /// <param name="starting">
        /// Called once the entry script is prepared, just before the engine runs it, so a caller can
        /// tell a failed preparation, where nothing ran, from a failure of the script.
        /// </param>
        public static int Execute(
            AgentScriptContext context, AgentRunRequest request, string runDir, IList<string> searchPaths, Action starting) {
            var entryPath = Path.Combine(runDir, EntryFileName);
            File.WriteAllText(entryPath, BuildEntryScript(request.Engine), new UTF8Encoding(false));

            var scriptData = CreateScriptData(entryPath, "Agent: " + request.Title);
            var configs = CreateRuntimeConfigs(
                context.UIApp, request.Engine, searchPaths, new Dictionary<string, object> { ["__agent__"] = context });

            starting();
            return ScriptExecutor.ExecuteScript(scriptData, configs);
        }

        private static string BuildEntryScript(AgentEngine engine) {
            var builder = new StringBuilder();
            if (engine == AgentEngine.CPython)
                builder.Append("#! python3\n");
            builder.Append("try:\n");
            foreach (var line in RunnerImport.TrimEnd('\n').Split('\n'))
                builder.Append("    ").Append(line).Append('\n');
            builder.Append(
                "except Exception:\n" +
                "    import traceback\n" +
                "    __agent__.SetError('RunnerImportError', 'Could not import pyrevit.agent', traceback.format_exc())\n" +
                "else:\n" +
                "    _runner.run(__agent__)\n");
            return builder.ToString();
        }
    }
}
