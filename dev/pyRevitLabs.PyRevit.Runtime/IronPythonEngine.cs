using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;

// iron languages
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using Microsoft.Scripting.Runtime;
using IronPython.Hosting;
using IronPython.Compiler;
using IronPython.Runtime.Exceptions;
using IronPython.Runtime.Operations;

using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Json;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    public class IronPythonEngineConfigs : ScriptEngineConfigs {
        public bool clean = false;
        public bool full_frame = false;
        public bool persistent = false;
    }

    public class IronPythonEngine : ScriptEngine {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public Microsoft.Scripting.Hosting.ScriptEngine Engine { get; private set; }
        public IronPythonEngineConfigs ExecEngineConfigs = new IronPythonEngineConfigs();

        public static Tuple<Stream, System.Text.Encoding> DefaultOutputStreamConfig {
            get {
                return (Tuple<Stream, System.Text.Encoding>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.IronPythonEngineDefaultOutputStreamCfgKey);
            }

            set {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.IronPythonEngineDefaultOutputStreamCfgKey, value);
            }
        }

        public static Tuple<Stream, System.Text.Encoding> DefaultErrorStreamConfig {
            get {
                return (Tuple<Stream, System.Text.Encoding>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.IronPythonEngineDefaultErrorStreamCfgKey);
            }

            set {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.IronPythonEngineDefaultErrorStreamCfgKey, value);
            }
        }

        public static Tuple<Stream, System.Text.Encoding> DefaultInputStreamConfig {
            get {
                return (Tuple<Stream, System.Text.Encoding>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.IronPythonEngineDefaultInputStreamCfgKey);
            }

            set {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.IronPythonEngineDefaultInputStreamCfgKey, value);
            }
        }

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            LoadExecutionConfigs(ref runtime);

            // If the command required a fullframe engine
            // or if the command required a clean engine
            // of if the user is asking to refresh the cached engine for the command,
            UseNewEngine = ExecEngineConfigs.clean || runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            LoadExecutionConfigs(ref runtime);

            if (!RecoveredFromCache) {
                var flags = new Dictionary<string, object>();

                // default flags
                flags["LightweightScopes"] = true;

                // Bound recursion so a runaway circular import raises a catchable
                // RecursionError instead of overflowing the native stack and crashing
                // Revit. IronPython does not enforce a limit unless one is set.
                flags["RecursionLimit"] = 1000;
                flags["ConsoleSupportLevel"] = SharedIO.SupportLevel.Basic;

                if (ExecEngineConfigs.full_frame) {
                    flags["Frames"] = true;
                    flags["FullFrames"] = true;
                    flags["Tracing"] = true;
                }

                Engine = IronPython.Hosting.Python.CreateEngine(flags);
                TrackContext(Engine);

                // also, allow access to the PyRevitLoader internals
                Engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);

                // also, allow access to the PyRevitRuntime internals
                Engine.Runtime.LoadAssembly(typeof(ScriptExecutor).Assembly);

                // reference RevitAPI and RevitAPIUI
                Engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
                Engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

                // save the default stream for later resetting the streams
                DefaultOutputStreamConfig = new Tuple<Stream, System.Text.Encoding>(Engine.Runtime.IO.OutputStream, Engine.Runtime.IO.OutputEncoding);
                DefaultErrorStreamConfig = new Tuple<Stream, System.Text.Encoding>(Engine.Runtime.IO.ErrorStream, Engine.Runtime.IO.ErrorEncoding);
                DefaultInputStreamConfig = new Tuple<Stream, System.Text.Encoding>(Engine.Runtime.IO.InputStream, Engine.Runtime.IO.InputEncoding);

                // setup stdlib
                SetupStdlib(Engine);
            }

            SetupStreams(ref runtime);
            SetupBuiltins(ref runtime);
            SetupSearchPaths(ref runtime);
            SetupArguments(ref runtime);
        }

        public override int Execute(ref ScriptRuntime runtime) {
            // Setup the command scope in this engine with proper builtin and scope parameters
            var scope = Engine.CreateScope();
            foreach (var variable in ScriptBuiltins.CreateRuntimeVariables(
                runtime, RecoveredFromCache, TypeId))
                scope.SetVariable(variable.Key, variable.Value);

            // Create the script from source file
            var script = Engine.CreateScriptSourceFromFile(
                    runtime.ScriptSourceFile,
                    System.Text.Encoding.UTF8,
                    SourceCodeKind.File
                );

            // Setting up error reporter and compile the script
            // setting module to be the main module so __name__ == __main__ is True
            var compiler_options = (PythonCompilerOptions)Engine.GetCompilerOptions(scope);
            compiler_options.ModuleName = "__main__";
            compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;

            var errors = new IronPythonErrorReporter();
            var command = script.Compile(compiler_options, errors);

            // Process compile errors if any
            if (command == null) {
                // compilation failed, print errors and return
                runtime.OutputStream.WriteError(string.Join(Environment.NewLine, errors.Errors.ToArray()), ScriptEngineType.IronPython);
                return ScriptExecutorResultCodes.CompileException;
            }

            // Finally let's execute
            try {
                command.Execute(scope);
                return ScriptExecutorResultCodes.Succeeded;
            }
            catch (SystemExitException) {
                // ok, so the system exited. That was bound to happen...
                return ScriptExecutorResultCodes.SysExited;
            }
            catch (Exception exception) {
                // show (power) user everything!
                string clrTraceMessage = exception.ToString();
                string ipyTraceMessage = Engine.GetService<ExceptionOperations>().FormatException(exception);

                // Print all errors to stdout and return cancelled to Revit.
                // This is to avoid getting window prompts from Revit.
                // Those pop ups are small and errors are hard to read.
                ipyTraceMessage = ipyTraceMessage.NormalizeNewLine();

                clrTraceMessage = clrTraceMessage.NormalizeNewLine();

                // set the trace messages on runtime for later usage (e.g. logging)
                runtime.TraceMessage = string.Join("\n", ipyTraceMessage, clrTraceMessage);

                // manually add the CLR traceback since this is a two part error message
                clrTraceMessage = string.Join("\n", ScriptConsoleConfigs.ToCustomHtmlTags(ScriptConsoleConfigs.CLRErrorHeader), clrTraceMessage);

                runtime.OutputStream.WriteError(ipyTraceMessage + "\n\n" + clrTraceMessage, ScriptEngineType.IronPython);
                return ScriptExecutorResultCodes.ExecutionException;
            }
            finally {
                if (!ExecEngineConfigs.persistent) {
                    // cleaning removes all references to revit content that's been casualy stored in global-level
                    // variables and prohibit the GC from cleaning them up and releasing memory
                    var scopeClearScript = Engine.CreateScriptSourceFromString(
                    "for __deref in dir():\n" +
                    "    if not __deref.startswith('__'):\n" +
                    "        del globals()[__deref]");
                    scopeClearScript.Compile();
                    scopeClearScript.Execute(scope);
                }
            }
        }

        public override void Stop(ref ScriptRuntime runtime) {
        }

        public override void Shutdown() {
            CleanupBuiltins();
            CleanupStreams();
        }

        private const int MaxBinderContainerDepth = 2;

        private static readonly FieldInfo BinderRuleCacheField =
            typeof(CallSiteBinder).GetField("Cache", BindingFlags.Instance | BindingFlags.NonPublic);

        private static readonly List<WeakReference> startedContexts = new List<WeakReference>();

        private static void TrackContext(Microsoft.Scripting.Hosting.ScriptEngine engine) {
            var context = Microsoft.Scripting.Hosting.Providers.HostingHelpers.GetLanguageContext(engine);
            lock (startedContexts)
                startedContexts.Add(new WeakReference(context));
        }

        private static List<object> LiveContexts() {
            var contexts = new List<object>();
            object defaultContext = IronPython.Runtime.DefaultContext.Default?.LanguageContext;
            if (defaultContext != null)
                contexts.Add(defaultContext);

            lock (startedContexts) {
                startedContexts.RemoveAll(reference => !reference.IsAlive);
                foreach (WeakReference reference in startedContexts) {
                    object context = reference.Target;
                    if (context != null && !contexts.Contains(context))
                        contexts.Add(context);
                }
            }
            return contexts;
        }

        /// <summary>
        /// Drops the call-site rules cached by the binders of every IronPython context still alive:
        /// IronPython's default context (the first engine created in the process) and the contexts
        /// of the engines this runtime started.
        /// </summary>
        /// <remarks>
        /// A binder belongs to one context but caches rules for objects of whichever engine it was
        /// used on, and each rule references that engine's types and functions. IronPython runs some
        /// operations on objects of every engine through the default context (ctypes reads a
        /// library's <c>_handle</c> there, for example), and an engine that Revit keeps alive, such as
        /// one that registered a dockable pane, keeps binding objects of later engines. Those rules
        /// keep every earlier engine alive with all the modules it imported. Dropping them only costs
        /// rebuilding them on next use. Best effort: the binders are found by reflection, and a
        /// failure is logged and leaves the remaining caches in place.
        /// </remarks>
        /// <returns>Number of binders whose rule cache was dropped.</returns>
        internal static int ReleaseCachedRules() {
            if (BinderRuleCacheField == null) {
                logger.Debug("CallSiteBinder has no rule cache field; cached rules are kept.");
                return 0;
            }

            int released = 0;
            const BindingFlags fieldFlags =
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
            List<object> contexts = LiveContexts();
            foreach (object context in contexts) {
                for (Type type = context.GetType(); type != null; type = type.BaseType) {
                    foreach (FieldInfo field in type.GetFields(fieldFlags)) {
                        try {
                            released += ReleaseBinderRules(field.GetValue(context), 0);
                        }
                        catch (Exception ex) {
                            logger.Debug(ex, "Could not release the rules held by {0}.{1}", type.Name, field.Name);
                        }
                    }
                }
            }

            logger.Debug("Released the rule caches of {0} binders in {1} IronPython contexts", released, contexts.Count);
            return released;
        }

        private static int ReleaseBinderRules(object value, int depth) {
            if (value is CallSiteBinder binder) {
                BinderRuleCacheField.SetValue(binder, null);
                return 1;
            }

            if (depth > MaxBinderContainerDepth)
                return 0;

            var items = new List<object>();
            if (value is IDictionary dictionary) {
                lock (dictionary)
                    foreach (object item in dictionary.Values)
                        items.Add(item);
            }
            else if (value is Array array) {
                foreach (object item in array)
                    items.Add(item);
            }

            int released = 0;
            foreach (object item in items)
                released += ReleaseBinderRules(item, depth + 1);
            return released;
        }

        private void SetupStdlib(Microsoft.Scripting.Hosting.ScriptEngine engine) {
            // ask PyRevitLoader to add it's resource ZIP file that contains the IronPython
            // standard library to this engine
            var tempExec = new PyRevitLoader.ScriptExecutor();
            tempExec.AddEmbeddedLib(engine);
        }

        private void LoadExecutionConfigs(ref ScriptRuntime runtime) {
            var configs = new IronPythonEngineConfigs();
            try {
                configs = JsonConvert.DeserializeObject<IronPythonEngineConfigs>(
                    runtime.ScriptRuntimeConfigs.EngineConfigs
                ) ?? configs;
            }
            catch (Exception ex) {
                logger.Warn(
                    ex,
                    "Failed to parse IronPython engine configuration: {0}",
                    runtime.ScriptRuntimeConfigs.EngineConfigs
                );
            }
            ExecEngineConfigs = configs;
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            Engine.Runtime.IO.SetOutput(runtime.OutputStream, System.Text.Encoding.UTF8);
            Engine.Runtime.IO.SetErrorOutput(runtime.OutputStream, System.Text.Encoding.UTF8);
            Engine.Runtime.IO.SetInput(runtime.OutputStream, System.Text.Encoding.UTF8);
        }

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            InjectBuiltins(Engine, runtime, RecoveredFromCache, TypeId);
        }

        // Keep reserved builtins consistent across command and interactive engines.
        internal static void InjectBuiltins(Microsoft.Scripting.Hosting.ScriptEngine engine, ScriptRuntime runtime, bool recoveredFromCache, string typeId) {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);

            foreach (var variable in ScriptBuiltins.CreateRuntimeVariables(
                runtime, recoveredFromCache, typeId))
                builtin.SetVariable(variable.Key, variable.Value);

            foreach (var variable in ScriptBuiltins.FilterUserVariables(runtime.ScriptRuntimeConfigs?.Variables))
                builtin.SetVariable(variable.Key, variable.Value);
        }

        private void SetupSearchPaths(ref ScriptRuntime runtime) {
            // process search paths provided to executor
            Engine.SetSearchPaths(runtime.ScriptRuntimeConfigs.SearchPaths);
        }

        private void SetupArguments(ref ScriptRuntime runtime) {
            // setup arguments (sets sys.argv)
            // engine.Setup.Options["Arguments"] = arguments;
            // engine.Runtime.Setup.HostArguments = new List<object>(arguments);
            var sysmodule = Engine.GetSysModule();
#if IPY342
            var pythonArgv = PythonOps.MakeEmptyList();
#else
            var pythonArgv = PythonOps.MakeEmptyList(2);
#endif
            // for python make sure the first argument is the script
            pythonArgv.append(runtime.ScriptSourceFile);
            foreach (var obj in runtime.ScriptRuntimeConfigs.Arguments) {
                pythonArgv.append(obj);
            }
            sysmodule.SetVariable("argv", pythonArgv);
        }

        private void CleanupBuiltins() {
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(Engine);

            builtin.SetVariable("__cachedengine__", (object)null);
            builtin.SetVariable("__cachedengineid__", (object)null);
            builtin.SetVariable("__scriptruntime__", (object)null);
            builtin.SetVariable("__commanddata__", (object)null);
            builtin.SetVariable("__elements__", (object)null);
            builtin.SetVariable("__uibutton__", (object)null);
            builtin.SetVariable("__commandpath__", (object)null);
            builtin.SetVariable("__configcommandpath__", (object)null);
            builtin.SetVariable("__commandname__", (object)null);
            builtin.SetVariable("__commandbundle__", (object)null);
            builtin.SetVariable("__commandextension__", (object)null);
            builtin.SetVariable("__commanduniqueid__", (object)null);
            builtin.SetVariable("__commandcontrolid__", (object)null);
            builtin.SetVariable("__forceddebugmode__", (object)null);
            builtin.SetVariable("__shiftclick__", (object)null);

            builtin.SetVariable("__result__", (object)null);

            builtin.SetVariable("__eventsender__", (object)null);
            builtin.SetVariable("__eventargs__", (object)null);
        }

        private void CleanupStreams() {
            // Remove IO streams references so GC can collect
            Tuple<Stream, System.Text.Encoding> outStream = DefaultOutputStreamConfig;
            if (outStream != null) {
                Engine.Runtime.IO.SetOutput(outStream.Item1, outStream.Item2);
                outStream.Item1.Dispose();
            }
            Tuple<Stream, System.Text.Encoding> errStream = DefaultErrorStreamConfig;
            if (errStream != null) {
                Engine.Runtime.IO.SetErrorOutput(errStream.Item1, errStream.Item2);
                errStream.Item1.Dispose();
            }
            Tuple<Stream, System.Text.Encoding> inStream = DefaultInputStreamConfig;
            if (inStream != null) {
                Engine.Runtime.IO.SetInput(inStream.Item1, inStream.Item2);
                inStream.Item1.Dispose();
            }
        }
    }

    public class IronPythonErrorReporter : ErrorListener {
        public List<string> Errors = new List<string>();

        public override void ErrorReported(ScriptSource source, string message,
                                           SourceSpan span, int errorCode, Severity severity) {
            Errors.Add(string.Format("{0} (line {1})", message, span.Start.Line));
        }

        public int Count {
            get { return Errors.Count; }
        }
    }
}
