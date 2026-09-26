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
        public AgentScriptContext(UIApplication uiApp, string runId, string mode, string source, string inputsJson, string workspace) {
            UIApp = uiApp;
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

        public static int Execute(
            AgentScriptContext context, AgentRunRequest request, string runDir, IList<string> searchPaths) {
            var entryPath = Path.Combine(runDir, EntryFileName);
            File.WriteAllText(entryPath, BuildEntryScript(request.Engine), new UTF8Encoding(false));

            var scriptData = new ScriptData {
                ScriptPath = entryPath,
                ConfigScriptPath = null,
                CommandUniqueId = "pyrevit-agent",
                CommandName = "Agent: " + request.Title,
                CommandBundle = string.Empty,
                CommandExtension = AgentExtensionName,
                HelpSource = string.Empty,
            };

            var configs = new ScriptRuntimeConfigs {
                UIApp = context.UIApp,
                SearchPaths = new List<string>(searchPaths),
                Arguments = new List<string>(),
                Variables = new Dictionary<string, object> { ["__agent__"] = context },
                SuppressOutput = true,
                EngineConfigs = request.Engine == AgentEngine.CPython
                    ? "{\"type\":\"CPython\",\"type_explicit\":true,\"clean\":false}"
                    : "{\"type\":\"IronPython\",\"type_explicit\":true,\"clean\":false,\"full_frame\":true,\"persistent\":false}",
                RefreshEngine = false,
                ConfigMode = false,
                DebugMode = false,
                ExecutedFromUI = false,
            };

            return ScriptExecutor.ExecuteScript(scriptData, configs);
        }

        private static string BuildEntryScript(AgentEngine engine) {
            var builder = new StringBuilder();
            if (engine == AgentEngine.CPython)
                builder.Append("#! python3\n");
            builder.Append(
                "try:\n" +
                "    from pyrevit.agent import _runner\n" +
                "except Exception:\n" +
                "    import traceback\n" +
                "    __agent__.SetError('RunnerImportError', 'Could not import pyrevit.agent', traceback.format_exc())\n" +
                "else:\n" +
                "    _runner.run(__agent__)\n");
            return builder.ToString();
        }
    }
}
