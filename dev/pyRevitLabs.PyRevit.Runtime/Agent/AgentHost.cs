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
            if (!IsEnabled()) {
                Stop();
                return;
            }

            lock (sync) {
                searchPaths = scriptSearchPaths != null
                    ? new List<string>(scriptSearchPaths)
                    : new List<string>();
                revitVersion = uiApp.Application.VersionNumber;

                if (dispatcher == null) {
                    dispatcher = new AgentDispatcher();
                    dispatcher.Attach(ExternalEvent.Create(dispatcher));
                }

                if (pipeServer != null)
                    return;

                pipeServer = new AgentPipeServer(PipeName, AgentRequestHandler.Handle);
                pipeServer.Start();
                WriteInstanceFile(uiApp);

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

    internal static class AgentPaths {
        public static string RootDir => Path.Combine(PyRevitLabsConsts.PyRevitPath, "agent");
        public static string InstancesDir => Path.Combine(RootDir, "instances");
        public static string RunsDir => Path.Combine(RootDir, "runs");
        public static string InstanceFile =>
            Path.Combine(InstancesDir, Process.GetCurrentProcess().Id + ".json");

        public static string CreateRunDir(string runId) {
            var runDir = Path.Combine(RunsDir, DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" + runId);
            Directory.CreateDirectory(runDir);
            return runDir;
        }
    }
}
