using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Security.Principal;
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
    /// ExternalEvent, or a pipe server that is still listening.
    /// Invariant: <see cref="Configure"/> must run in a valid Revit API context, because the
    /// first start creates an ExternalEvent.
    /// Warning: off unless <c>[agent] enabled = true</c> is set in the pyRevit config. Agent
    /// scripts run with the user's full rights; the pipe ACL is the only access control.
    /// Important: the host never starts in an elevated Revit. The pipe ACL admits any process of
    /// the user, including unelevated ones, which would let them run code as administrator.
    /// </remarks>
    public static class AgentHost {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object sync = new object();

        private static AgentDispatcher dispatcher;
        private static AgentPipeServer pipeServer;
        private static List<string> searchPaths = new List<string>();
        private static string revitVersion = string.Empty;
        private static bool exitHandlerRegistered;
        private static readonly AgentConfigRefresh configRefresh = new AgentConfigRefresh(
            PyRevitConfigs.GetLoadedConfigFilePath,
            path => File.Exists(path) ? File.GetLastWriteTimeUtc(path) : DateTime.MinValue,
            PyRevitConfigs.ReloadConfig);
        private static AgentTabHighlight tabHighlight;
        private static AgentTabHighlightVisuals tabHighlightVisuals;
        private static bool tabHighlightDisabled;
        private static readonly AgentEngineWarmUp engineWarmUp = new AgentEngineWarmUp();

        internal static AgentTabHighlight.Lease BeginTabHighlight(UIApplication application, Autodesk.Revit.DB.Document document, string title) {
            RefreshConfigIfChanged();
            try {
                if (!PyRevitConfigs.GetAgentTabHighlight()) {
                    DisposeTabHighlight();
                    return null;
                }
                if (document == null || tabHighlightDisabled)
                    return null;
                if (tabHighlight == null) {
                    var window = DocumentTabLocator.GetWindowRoot(application);
                    if (window == null)
                        return null;
                    tabHighlightVisuals = new AgentTabHighlightVisuals(window.Dispatcher);
                    var clock = Stopwatch.StartNew();
                    tabHighlight = new AgentTabHighlight(() => clock.ElapsedMilliseconds,
                        tabHighlightVisuals.Schedule, tabHighlightVisuals, exception => {
                            tabHighlightDisabled = true;
                            logger.Warn("Agent tab highlighting disabled after three visual failures: {0}", exception.Message);
                        });
                    tabHighlightVisuals.Refresh = tabHighlight.Refresh;
                    tabHighlightVisuals.VisualFailure = tabHighlight.VisualFailed;
                }
                var key = DocumentTabLocator.GetAPIDocumentId(document);
                tabHighlightVisuals.Register(application, document, key);
                return tabHighlight.Begin(key, title);
            }
            catch (Exception exception) {
                tabHighlight?.VisualFailed(exception);
                return null;
            }
        }

        internal static void AwaitTabApproval(AgentTabHighlight.Lease lease) => tabHighlight?.AwaitApproval(lease);

        internal static void EndTabHighlight(AgentTabHighlight.Lease lease) => tabHighlight?.End(lease);

        private static void DisposeTabHighlight() {
            tabHighlightVisuals?.Dispose();
            tabHighlight?.Dispose();
            tabHighlightVisuals = null;
            tabHighlight = null;
        }

        [ThreadStatic]
        private static UIApplication inlineApplication;

        internal static readonly int ProcessId = ReadProcessId();

        public static string PipeName => "pyrevit-agent-" + ProcessId;

        /// <summary>
        /// True while the pipe server is up and accepting connections.
        /// </summary>
        /// <remarks>
        /// False after <see cref="Stop"/>, and after the pipe server gave up because Revit kept
        /// refusing to create its pipe; the next <see cref="Configure"/> starts a new one.
        /// </remarks>
        public static bool IsRunning {
            get {
                lock (sync)
                    return pipeServer != null && pipeServer.IsListening;
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
                configRefresh.RefreshIfChanged();
            }
            catch (Exception ex) {
                logger.Debug("Could not refresh agent config: {0}", ex.Message);
            }
        }

        /// <summary>
        /// Whether <c>[agent] enabled</c> is on in the pyRevit config; false when it can't be read.
        /// </summary>
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
        /// <remarks>
        /// A reload also re-enables tab highlighting that visual failures turned off.
        /// </remarks>
        public static void Configure(UIApplication uiApp, IList<string> scriptSearchPaths) {
            if (tabHighlightDisabled) {
                DisposeTabHighlight();
                tabHighlightDisabled = false;
            }

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

            engineWarmUp.Reset();
            if (IsElevated()) {
                Stop();
                logger.Warn("pyRevit agent host not started: Revit is running as administrator.");
                return;
            }

            lock (sync) {
                if (dispatcher == null) {
                    dispatcher = new AgentDispatcher();
                    dispatcher.Attach(ExternalEvent.Create(dispatcher));
                }

                if (pipeServer != null && pipeServer.IsListening)
                    return;

                pipeServer?.Dispose();
                pipeServer = new AgentPipeServer(PipeName, AgentRequestHandler.Handle, ForgetStoppedPipe);
                pipeServer.Start();
                WriteInstanceFile(uiApp);
                AgentPaths.PruneOldRecordsInBackground();

                if (!exitHandlerRegistered) {
                    AppDomain.CurrentDomain.ProcessExit += (s, e) => DeleteInstanceFile();
                    uiApp.ApplicationClosing += (s, e) => Stop();
                    exitHandlerRegistered = true;
                }
            }

            logger.Info("pyRevit agent host listening on pipe '{0}'", PipeName);
        }

        /// <summary>
        /// Closes the pipe and removes this Revit's instance file, so clients stop finding it.
        /// The ExternalEvent stays, so a later <see cref="Configure"/> can start the host again.
        /// </summary>
        public static void Stop() {
            DisposeTabHighlight();
            lock (sync) {
                if (pipeServer == null)
                    return;
                pipeServer.Dispose();
                pipeServer = null;
                DeleteInstanceFile();
            }

            logger.Info("pyRevit agent host stopped");
        }

        private static void ForgetStoppedPipe(AgentPipeServer stopped) {
            lock (sync) {
                if (ReferenceEquals(pipeServer, stopped))
                    DeleteInstanceFile();
            }
        }

        private static bool IsElevated() {
            using (var identity = WindowsIdentity.GetCurrent())
                return new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator);
        }

        private static void WriteInstanceFile(UIApplication uiApp) {
            try {
                Directory.CreateDirectory(AgentPaths.InstancesDir);
                var instance = new JObject {
                    ["pid"] = ProcessId,
                    ["pipe"] = PipeName,
                    ["revit_version"] = uiApp.Application.VersionNumber,
                    ["revit_build"] = uiApp.Application.VersionBuild,
                    ["started"] = DateTime.UtcNow.ToString("o"),
                };
                if (int.TryParse(uiApp.Application.VersionNumber, out var revitYear))
                    instance.Merge(AgentSessionIdentity.Describe(revitYear));
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

        private static int ReadProcessId() {
            using (var process = Process.GetCurrentProcess())
                return process.Id;
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

        /// <summary>
        /// The session load a request starts in; pass it to <see cref="NoteRequest"/>.
        /// </summary>
        internal static int SessionLoad => engineWarmUp.Load;

        /// <summary>
        /// Queues the engine warm-up after the first agent request of a session load, so the
        /// first run finds the engine ready. Called on the pipe thread once a request is handled.
        /// </summary>
        /// <remarks>
        /// The warm-up runs through the dispatcher on the Revit main thread, never on the pipe
        /// thread, and a <c>run</c> queued after it waits for it. Requests made in-process through
        /// <see cref="HandleRequest"/> don't count: they come from a command, not an agent.
        /// Failures are logged at debug level only and never affect the host.
        /// </remarks>
        internal static void NoteRequest(string method, int loadAtStart) {
            if (inlineApplication != null || !engineWarmUp.OnRequest(method, loadAtStart))
                return;
            try {
                Dispatcher?.Post(WarmUpEngine);
            }
            catch (Exception ex) {
                logger.Debug("Could not queue the agent engine warm-up: {0}", ex.Message);
            }
        }

        private static JToken WarmUpEngine(UIApplication uiApp) {
            try {
                var defaultIsIronPython = PyRevitConfigs.GetAgentEngine() == PyRevitConsts.ConfigsAgentEngineIronPython;
                if (!AgentEngineWarmUp.ShouldWarm(IsRunning && IsEnabled(), defaultIsIronPython, AgentScriptRunner.IsIronPythonEngineCached()))
                    return null;
                var clock = Stopwatch.StartNew();
                var exitCode = AgentScriptRunner.WarmUp(uiApp, SearchPaths);
                logger.Debug("[PERF] agent engine warm-up: exit code {0} in {1} ms", exitCode, clock.ElapsedMilliseconds);
            }
            catch (Exception ex) {
                logger.Debug("Agent engine warm-up failed: {0}", ex.Message);
            }
            return null;
        }
    }

    /// <remarks>
    /// Run records and captures older than <see cref="RecordRetention"/> are deleted when the
    /// host starts and again, at most once per <see cref="PruneInterval"/>, when a run record is
    /// created, so a busy agent doesn't fill the user's profile even in a Revit session left open
    /// for weeks; one night of evals wrote about 140 runs.
    /// </remarks>
    internal static class AgentPaths {
        private static readonly Logger pathsLogger = LogManager.GetCurrentClassLogger();
        public static readonly TimeSpan RecordRetention = TimeSpan.FromDays(14);
        public static readonly TimeSpan PruneInterval = TimeSpan.FromDays(1);
        private static readonly object pruneLock = new object();
        private static DateTime nextPrune = DateTime.MinValue;

        public static string RootDir => PyRevitLabsConsts.AgentPath;
        public static string InstancesDir => Path.Combine(RootDir, "instances");
        public static string RunsDir => Path.Combine(RootDir, "runs");
        public static string CapturesDir => Path.Combine(RootDir, "captures");
        public static string InstanceFile =>
            Path.Combine(InstancesDir, AgentHost.ProcessId + ".json");

        public static string CreateRunDir(string runId) {
            var runDir = Path.Combine(RunsDir, DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + runId);
            Directory.CreateDirectory(runDir);
            PruneOldRecordsInBackground();
            return runDir;
        }

        /// <remarks>Does nothing when a prune started less than <see cref="PruneInterval"/> ago.</remarks>
        public static void PruneOldRecordsInBackground() {
            lock (pruneLock) {
                if (DateTime.Now < nextPrune)
                    return;
                nextPrune = DateTime.Now + PruneInterval;
            }
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
