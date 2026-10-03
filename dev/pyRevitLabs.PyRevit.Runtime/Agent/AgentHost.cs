using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// In-Revit endpoint of the pyRevit agent runtime. Serves agent requests over a
    /// current-user named pipe and executes them on the Revit main thread.
    /// </summary>
    /// <remarks>
    /// The host lives for the whole Revit process, like the <see cref="ScriptExecutor"/>
    /// ExternalEvent. <see cref="Configure"/> is called on every session load and is
    /// idempotent: a reload only refreshes the script search paths and never recreates the
    /// pipe or the ExternalEvent.
    /// Invariant: <see cref="Configure"/> must run in a valid Revit API context, because the
    /// first start creates an ExternalEvent.
    /// Warning: off unless <c>[agent] enabled = true</c> is set in the pyRevit config. Agent
    /// scripts run with the user's full rights; the pipe ACL is the only access control.
    /// </remarks>
    public static class AgentHost {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object sync = new object();

        private static AgentDispatcher dispatcher;
        private static AgentPipeServer pipeServer;
        private static List<string> searchPaths = new List<string>();
        private static string revitVersion = string.Empty;
        private static bool exitHandlerRegistered;
        private static string configWatchedPath;
        private static DateTime configLastWrite = DateTime.MinValue;

        [ThreadStatic]
        private static UIApplication inlineApplication;

        public static string PipeName => "pyrevit-agent-" + Process.GetCurrentProcess().Id;

        public static bool IsRunning {
            get {
                lock (sync)
                    return pipeServer != null;
            }
        }

        internal static AgentDispatcher Dispatcher {
            get {
                lock (sync)
                    return dispatcher;
            }
        }

        internal static IList<string> SearchPaths {
            get {
                lock (sync)
                    return new List<string>(searchPaths);
            }
        }

        internal static string RevitVersion {
            get {
                lock (sync)
                    return revitVersion;
            }
        }

        internal static UIApplication InlineApplication => inlineApplication;

        /// <summary>
        /// Handles one agent request in-process and synchronously: the same JSON-RPC request
        /// and response the pipe carries, for tools and tests that run inside Revit.
        /// </summary>
        /// <remarks>
        /// A pyRevit command can't use the pipe, because the pipe executes requests through an
        /// ExternalEvent that never fires while a command is running. This runs the request on
        /// the calling thread instead, through the same policy, guard and dialog handling.
        /// Warning: a CPython caller must save and restore <c>sys.stdout</c>, <c>sys.stderr</c>,
        /// <c>sys.path</c>, <c>sys.argv</c> and the trace function around the call; a nested
        /// CPython run replaces them and doesn't put them back.
        /// </remarks>
        /// <exception cref="InvalidOperationException">
        /// Called off the Revit main thread, where the Revit API can't be used.
        /// </exception>
        public static string HandleRequest(UIApplication app, string requestJson) {
            if (app == null)
                throw new ArgumentNullException(nameof(app));
            if (!ScriptExecutor.IsOnMainThread)
                throw new InvalidOperationException(
                    "HandleRequest must be called on the Revit main thread, from a command or another Revit API callback.");

            var previous = inlineApplication;
            inlineApplication = app;
            try {
                return AgentRequestHandler.Handle(requestJson);
            }
            finally {
                inlineApplication = previous;
            }
        }

        /// <summary>
        /// Drops the process-wide config cache when the loaded config file changed on disk since
        /// the last check, so settings changed from outside Revit (<c>pyrevit configs agent policy</c>)
        /// apply to the next agent request instead of the next pyRevit reload.
        /// </summary>
        /// <remarks>
        /// Invariant: the policy is a safety setting, so every request that runs code must call
        /// this before reading it.
        /// </remarks>
        internal static void RefreshConfigIfChanged() {
            try {
                var configPath = PyRevitConfigs.GetLoadedConfigFilePath();
                var lastWrite = File.Exists(configPath) ? File.GetLastWriteTimeUtc(configPath) : DateTime.MinValue;
                lock (sync) {
                    if (configPath == configWatchedPath && lastWrite == configLastWrite)
                        return;
                    configWatchedPath = configPath;
                    configLastWrite = lastWrite;
                }
                PyRevitConfigs.ReloadConfig();
            }
            catch (Exception ex) {
                logger.Debug("Could not refresh agent config: {0}", ex.Message);
            }
        }

        public static bool IsEnabled() {
            try {
                return PyRevitConfigs.GetAgentEnabled();
            }
            catch (Exception ex) {
                logger.Debug("Could not read agent config: {0}", ex.Message);
                return false;
            }
        }

        /// <summary>
        /// Starts, refreshes, or stops the host to match the current config. Called by the
        /// session manager on every load and reload.
        /// </summary>
        public static void Configure(UIApplication uiApp, IList<string> scriptSearchPaths) {
            lock (sync) {
                searchPaths = scriptSearchPaths != null
                    ? new List<string>(scriptSearchPaths)
                    : new List<string>();
                revitVersion = uiApp.Application.VersionNumber;
            }

            if (!IsEnabled()) {
                Stop();
                return;
            }

            lock (sync) {
                if (dispatcher == null) {
                    dispatcher = new AgentDispatcher();
                    dispatcher.Attach(ExternalEvent.Create(dispatcher));
                }

                if (pipeServer != null)
                    return;

                pipeServer = new AgentPipeServer(PipeName, AgentRequestHandler.Handle);
                pipeServer.Start();
                WriteInstanceFile(uiApp);
                AgentPaths.PruneOldRecordsInBackground();

                if (!exitHandlerRegistered) {
                    AppDomain.CurrentDomain.ProcessExit += (s, e) => DeleteInstanceFile();
                    exitHandlerRegistered = true;
                }
            }

            logger.Info("pyRevit agent host listening on pipe '{0}'", PipeName);
        }

        public static void Stop() {
            lock (sync) {
                if (pipeServer == null)
                    return;
                pipeServer.Dispose();
                pipeServer = null;
                DeleteInstanceFile();
            }

            logger.Info("pyRevit agent host stopped");
        }

        private static void WriteInstanceFile(UIApplication uiApp) {
            try {
                Directory.CreateDirectory(AgentPaths.InstancesDir);
                var instance = new JObject {
                    ["pid"] = Process.GetCurrentProcess().Id,
                    ["pipe"] = PipeName,
                    ["revit_version"] = uiApp.Application.VersionNumber,
                    ["revit_build"] = uiApp.Application.VersionBuild,
                    ["started"] = DateTime.UtcNow.ToString("o"),
                };
                File.WriteAllText(
                    AgentPaths.InstanceFile,
                    instance.ToString(Formatting.Indented),
                    new UTF8Encoding(false)
                );
            }
            catch (Exception ex) {
                logger.Warn("Could not register agent instance: {0}", ex.Message);
            }
        }

        private static void DeleteInstanceFile() {
            try {
                if (File.Exists(AgentPaths.InstanceFile))
                    File.Delete(AgentPaths.InstanceFile);
            }
            catch (Exception ex) {
                logger.Debug("Could not remove agent instance file: {0}", ex.Message);
            }
        }
    }

    /// <remarks>
    /// Run records and captures older than <see cref="RecordRetention"/> are deleted when the
    /// host starts, so a busy agent doesn't fill the user's profile; one night of evals wrote
    /// about 140 runs.
    /// </remarks>
    internal static class AgentPaths {
        private static readonly Logger pathsLogger = LogManager.GetCurrentClassLogger();
        public static readonly TimeSpan RecordRetention = TimeSpan.FromDays(14);

        public static string RootDir => Path.Combine(PyRevitLabsConsts.PyRevitPath, "agent");
        public static string InstancesDir => Path.Combine(RootDir, "instances");
        public static string RunsDir => Path.Combine(RootDir, "runs");
        public static string CapturesDir => Path.Combine(RootDir, "captures");
        public static string InstanceFile =>
            Path.Combine(InstancesDir, Process.GetCurrentProcess().Id + ".json");

        public static string CreateRunDir(string runId) {
            var runDir = Path.Combine(RunsDir, DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + runId);
            Directory.CreateDirectory(runDir);
            return runDir;
        }

        public static void PruneOldRecordsInBackground() {
            System.Threading.Tasks.Task.Run(() => PruneOldRecords(DateTime.Now - RecordRetention));
        }

        private static void PruneOldRecords(DateTime cutoff) {
            var removed = 0;
            try {
                if (Directory.Exists(RunsDir)) {
                    foreach (var runDir in Directory.GetDirectories(RunsDir)) {
                        if (Directory.GetLastWriteTime(runDir) >= cutoff)
                            continue;
                        Directory.Delete(runDir, recursive: true);
                        removed++;
                    }
                }
                if (Directory.Exists(CapturesDir)) {
                    foreach (var capture in Directory.GetFiles(CapturesDir)) {
                        if (File.GetLastWriteTime(capture) >= cutoff)
                            continue;
                        File.Delete(capture);
                        removed++;
                    }
                }
            }
            catch (Exception ex) {
                pathsLogger.Debug("Could not prune agent records: {0}", ex.Message);
            }
            if (removed > 0)
                pathsLogger.Debug("Pruned {0} agent run records and captures older than {1:yyyy-MM-dd}", removed, cutoff);
        }
    }
}
