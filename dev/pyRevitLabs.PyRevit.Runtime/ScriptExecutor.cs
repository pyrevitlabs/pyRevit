using System;
using System.IO;
using System.Threading;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class ScriptExecutorResultCodes {
        public static int Succeeded = 0;
        public static int SysExited = 1;
        public static int ExecutionException = 2;
        public static int CompileException = 3;
        public static int EngineNotImplementedException = 4;
        public static int ExternalInterfaceNotImplementedException = 5;
        public static int FailedLoadingContent = 6;
        public static int BadCommandArguments = 7;
        public static int NotSupportedFeatureException = 8;
        public static int UnknownException = 9;
        public static int MissingTargetScript = 10;
        public static int DelayedExecutionRequested = 11;
        public static int FailedDelayedExecutionRequest = 12;
        public static int DelayedExecutionException = 13;
        public static int ExecutorNotInitialized = 14;
    }

    /// <summary>
    /// One script run requested from a non-main thread. Each request carries its own events and
    /// result, so a request that was withdrawn or replaced can never signal or corrupt the next one.
    /// </summary>
    public sealed class ScriptRequest {
        internal ScriptRequest(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeConfigs) {
            ScriptData = scriptData;
            ScriptRuntimeConfigs = scriptRuntimeConfigs;
        }

        /// <summary>
        /// The script to run.
        /// </summary>
        public ScriptData ScriptData { get; }

        /// <summary>
        /// The runtime configuration of the run. The main-thread <c>UIApp</c> is filled in when Revit
        /// starts the request.
        /// </summary>
        public ScriptRuntimeConfigs ScriptRuntimeConfigs { get; }

        /// <summary>
        /// Result code of the run. Stays <see cref="ScriptExecutorResultCodes.FailedDelayedExecutionRequest"/>
        /// when the request never ran, and becomes <see cref="ScriptExecutorResultCodes.DelayedExecutionException"/>
        /// when the run threw.
        /// </summary>
        public int Result { get; internal set; } = ScriptExecutorResultCodes.FailedDelayedExecutionRequest;

        /// <summary>
        /// Set when Revit begins the request, so a caller can bound how long it waits for Revit to
        /// start it without bounding the script's own run time.
        /// </summary>
        public ManualResetEventSlim Started { get; } = new ManualResetEventSlim(false);

        /// <summary>
        /// Set when the request has finished, so a waiting caller blocks on it instead of polling
        /// <see cref="ExternalEvent.IsPending"/>. Waiting for it after <see cref="Started"/> is
        /// unbounded on purpose: the script is running and its run time is the user's.
        /// </summary>
        public ManualResetEventSlim Completed { get; } = new ManualResetEventSlim(false);

        internal void Abandon() {
            Result = ScriptExecutorResultCodes.FailedDelayedExecutionRequest;
            Started.Set();
            Completed.Set();
        }

        internal void Run(UIApplication uiApp) {
            Started.Set();
            try {
                // provide the given uiapp
                ScriptRuntimeConfigs.UIApp = uiApp;

                // request execution and set results
                Result = ScriptExecutor.ExecuteScript(ScriptData, ScriptRuntimeConfigs);
            }
            catch {
                Result = ScriptExecutorResultCodes.DelayedExecutionException;
                throw;
            }
            finally {
                Completed.Set();
            }
        }
    }

    /// <summary>
    /// Holds at most one pending <see cref="ScriptRequest"/>. Submitting another before the first is
    /// taken abandons the first, which then completes with
    /// <see cref="ScriptExecutorResultCodes.FailedDelayedExecutionRequest"/> rather than being run
    /// or silently dropped.
    /// </summary>
    public sealed class ScriptRequestSlot {
        private ScriptRequest pending;

        /// <summary>
        /// Makes a new request the pending one, abandoning any request that was not taken.
        /// </summary>
        public ScriptRequest Submit(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeConfigs) {
            var request = new ScriptRequest(scriptData, scriptRuntimeConfigs);
            Interlocked.Exchange(ref pending, request)?.Abandon();
            return request;
        }

        /// <summary>
        /// Takes the request back so <see cref="Take"/> cannot return it. Returns false when it was
        /// already taken or abandoned. A taken script is running and the caller must wait for
        /// <see cref="ScriptRequest.Completed"/> instead of reporting a failure.
        /// </summary>
        public bool TryWithdraw(ScriptRequest request) {
            return Interlocked.CompareExchange(ref pending, null, request) == request;
        }

        /// <summary>
        /// Claims the pending request for running, or returns null when there is none.
        /// </summary>
        public ScriptRequest Take() {
            return Interlocked.Exchange(ref pending, null);
        }
    }

    /// <summary>
    /// Runs script requests on the Revit main thread through one process-wide ExternalEvent.
    /// </summary>
    public class ScriptExecutorExternalEventHandler : IExternalEventHandler {
        private readonly ScriptRequestSlot slot = new ScriptRequestSlot();

        /// <summary>
        /// Queues a request for the next time Revit raises the external event. Submitting replaces a
        /// request that was not yet claimed; the replaced request completes with
        /// <see cref="ScriptExecutorResultCodes.FailedDelayedExecutionRequest"/>.
        /// </summary>
        public ScriptRequest Submit(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeConfigs) {
            return slot.Submit(scriptData, scriptRuntimeConfigs);
        }

        /// <summary>
        /// Cancels a request that has not started. Returns false when withdrawal is no longer
        /// possible because execution already claimed the request or a newer submission replaced it;
        /// a claimed request is running and the caller must wait for
        /// <see cref="ScriptRequest.Completed"/>.
        /// </summary>
        public bool TryWithdraw(ScriptRequest request) {
            return slot.TryWithdraw(request);
        }

        public void Execute(UIApplication uiApp) {
            // release the executed script's references; this handler lives
            // for the whole process and would otherwise pin the previous
            // session's runtime objects (UIApp, documents) across reloads.
            slot.Take()?.Run(uiApp);
        }

        public string GetName() {
            return "ScriptExecutorExternalEventHandler";
        }
    }

    public class ScriptExecutorConfigs {
        public bool WaitForResult = true;
        public bool SendTelemetry = false;
    }

    /// Executes a script
    public class ScriptExecutor {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static int mainThreadId;
        private static ScriptExecutorExternalEventHandler extExecEventHandler;
        private static ExternalEvent extExecEvent;

        /// <summary>
        /// How long a request from a non-main thread waits for Revit to start it before failing
        /// with <see cref="ScriptExecutorResultCodes.FailedDelayedExecutionRequest"/>. The default
        /// is 30 seconds. Revit does not start the request while it is busy, for example in a
        /// long command, a modal dialog or a regeneration, so a request made then can fail where an
        /// unbounded wait would have run it once Revit became idle. The bound does not limit the
        /// script's own run time. Set <see cref="Timeout.InfiniteTimeSpan"/> to wait without limit.
        /// </summary>
        public static TimeSpan ExternalEventStartTimeout { get; set; } = TimeSpan.FromSeconds(30);

        public static void Initialize() {
            // Idempotent on purpose. The ExternalEvent is scoped to the add-in
            // lifetime (the loader stays registered for the whole Revit process),
            // not to a pyRevit session, so the same event remains valid across
            // reloads and is reused instead of recreated. Reusing it avoids
            // leaking an undisposed ExternalEvent + handler on every reload
            // (Revit holds a strong reference to the handler) and avoids breaking
            // an in-flight RequestExecuteScript. Both the python and c# session
            // managers call Initialize() during a single load, so the early
            // return also collapses that double call.
            // NOTE: assemblies load into the default (non-collectible)
            // AssemblyLoadContext, so there is no per-session context to pin or
            // unload here; revisit this if pyRevit ever adopts collectible load
            // contexts, where disposing the old event on reload would matter.
            // The check-then-create below is intentionally unlocked: both call
            // sites run on the Revit main thread during init, so there is no
            // concurrent entry to guard against.
            if (extExecEvent == null) {
                mainThreadId = Thread.CurrentThread.ManagedThreadId;
                extExecEventHandler = new ScriptExecutorExternalEventHandler();
                extExecEvent = ExternalEvent.Create(extExecEventHandler);
            }

            try {
                ApiContextQueue.Initialize();
            }
            catch (Exception ex) {
                logger.Error(ex, "Could not create the shared API context queue.");
            }
        }

        internal static bool IsOnMainThread =>
            mainThreadId != 0 && Thread.CurrentThread.ManagedThreadId == mainThreadId;

        /// Run the script and print the output to a new output window.
        public static int ExecuteScript(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs = null) {
            // make sure there is base configs
            scriptExecConfigs = scriptExecConfigs == null ? new ScriptExecutorConfigs() : scriptExecConfigs;

            if (mainThreadId != 0) {
                if (Thread.CurrentThread.ManagedThreadId == mainThreadId)
                    return ExecuteScriptNow(scriptData, scriptRuntimeCfg, scriptExecConfigs);
                else
                    return RequestExecuteScript(scriptData, scriptRuntimeCfg, scriptExecConfigs);
            }

            return ScriptExecutorResultCodes.ExecutorNotInitialized;
        }

        /// <summary>
        /// Executes a script from a Revit API callback that is already authorized to run synchronously.
        /// </summary>
        internal static int ExecuteScriptInApiContext(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs = null) {
            scriptExecConfigs = scriptExecConfigs ?? new ScriptExecutorConfigs();
            return ExecuteScriptNow(scriptData, scriptRuntimeCfg, scriptExecConfigs);
        }

        private static int ExecuteScriptNow(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs) {
            // create runtime
            var runtime = new ScriptRuntime(scriptData, scriptRuntimeCfg);

            // determine which engine to use, and execute
            if (EnsureTargetScript(ref runtime)) {
                switch (runtime.EngineType) {
                    case ScriptEngineType.IronPython:
                        ExecuteManagedScript<IronPythonEngine>(ref runtime);
                        break;

                    case ScriptEngineType.CPython:
                        ExecuteManagedScript<CPythonEngine>(ref runtime);
                        break;

                    case ScriptEngineType.CSharp:
                        ExecuteManagedScript<CLREngine>(ref runtime);
                        break;

                    case ScriptEngineType.Invoke:
                        ExecuteManagedScript<InvokableDLLEngine>(ref runtime);
                        break;

                    case ScriptEngineType.VisualBasic:
                        ExecuteManagedScript<CLREngine>(ref runtime);
                        break;

                    case ScriptEngineType.IronRuby:
                        ExecuteManagedScript<IronRubyEngine>(ref runtime);
                        break;

                    case ScriptEngineType.DynamoBIM:
                        ExecuteManagedScript<DynamoBIMEngine>(ref runtime);
                        break;

                    case ScriptEngineType.Grasshopper:
                        ExecuteManagedScript<GrasshoppertEngine>(ref runtime);
                        break;

                    case ScriptEngineType.Content:
                        ExecuteManagedScript<ContentEngine>(ref runtime);
                        break;

                    case ScriptEngineType.HyperLink:
                        ExecuteManagedScript<HyperlinkEngine>(ref runtime);
                        break;

                    default:
                        // should not get here
                        throw new PyRevitException("Unknown engine type.");
                }
            }
            else
                runtime.ExecutionResult = ScriptExecutorResultCodes.MissingTargetScript;

            // Log results
            int result = runtime.ExecutionResult;
            if (scriptExecConfigs.SendTelemetry)
                ScriptTelemetry.LogScriptTelemetryRecord(ref runtime);

            // Drain any output still buffered by the engine (trailing prints,
            // logger records, uncaught tracebacks) to the live window before the
            // runtime and its window references are torn down below.
            try {
                runtime.OutputStream.Flush();
            }
            catch {
                // output rendering must never break command teardown
            }

            // GC cleanups
            var re = runtime.ExecutionResult;
            runtime.Dispose();
            runtime = null;

            // return the result
            return result;
        }

        private static int RequestExecuteScript(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs) {
            if (extExecEventHandler != null) {
                var request = extExecEventHandler.Submit(scriptData, scriptRuntimeCfg);

                // request command exec now
                var raised = extExecEvent.Raise();
                if (raised != ExternalEventRequest.Accepted && raised != ExternalEventRequest.Pending) {
                    extExecEventHandler.TryWithdraw(request);
                    return ScriptExecutorResultCodes.FailedDelayedExecutionRequest;
                }

                // wait until the script is executed
                if (scriptExecConfigs.WaitForResult) {
                    if (!request.Started.Wait(ExternalEventStartTimeout)
                        && extExecEventHandler.TryWithdraw(request)) {
                        logger.Warn("Revit did not start the external event within {0}s for script: {1}",
                            ExternalEventStartTimeout.TotalSeconds, scriptData.ScriptPath);
                        return ScriptExecutorResultCodes.FailedDelayedExecutionRequest;
                    }
                    request.Completed.Wait();
                    return request.Result;
                }
                // otherwise
                return ScriptExecutorResultCodes.DelayedExecutionRequested;
            }

            return ScriptExecutorResultCodes.FailedDelayedExecutionRequest;
        }

        public static bool EnsureTargetScript(ref ScriptRuntime runtime) {
            if (runtime.ScriptRuntimeConfigs.ConfigMode)
                return EnsureTargetScript(runtime.ScriptData.ConfigScriptPath);
            else
                return EnsureTargetScript(runtime.ScriptData.ScriptPath);
        }

        public static bool EnsureTargetScript(string scriptFile) {
            if (File.Exists(scriptFile))
                return true;
            TaskDialog.Show(PyRevitLabsConsts.ProductName, "Can not find target file. Maybe deleted?");
            return false;
        }

        private static void ExecuteManagedScript<T>(ref ScriptRuntime runtime) where T : ScriptEngine, new() {
            // 1: ----------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            T engine = ScriptEngineManager.GetEngine<T>(ref runtime);

            ScriptEngineManager.EnterEngine(engine.TypeId);
            try {
                // init the engine
                using (LoadTimeline.Active?.StartSpan(engine.RecoveredFromCache ? "cached engine" : "new engine"))
                    engine.Start(ref runtime);
                // execute
                int result;
                using (LoadTimeline.Active?.StartSpan("execute"))
                    result = engine.Execute(ref runtime);
                // stop and cleanup the engine
                engine.Stop(ref runtime);

                // set result
                runtime.ExecutionResult = result;
            }
            finally {
                ScriptEngineManager.ExitEngine(engine.TypeId);
            }
        }
    }
}
