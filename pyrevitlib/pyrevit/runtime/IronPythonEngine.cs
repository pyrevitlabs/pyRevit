using System;
using System.IO;
using System.Collections.Generic;

// iron languages
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using IronPython.Hosting;
using IronPython.Compiler;
using IronPython.Runtime.Exceptions;

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

            // extract engine configuration from runtime data
            try {
                ExecEngineConfigs = JsonConvert.DeserializeObject<IronPythonEngineConfigs>(runtime.ScriptRuntimeConfigs.EngineConfigs);
            } catch {}

            // If the command required a fullframe engine
            // or if the command required a clean engine
            // of if the user is asking to refresh the cached engine for the command,
            UseNewEngine = ExecEngineConfigs.clean || runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            if (!RecoveredFromCache) {
                var flags = new Dictionary<string, object>();

                // default flags
                flags["LightweightScopes"] = true;

                if (ExecEngineConfigs.full_frame) {
                    flags["Frames"] = true;
                    flags["FullFrames"] = true;
                    flags["Tracing"] = true;
                }

                Engine = IronPython.Hosting.Python.CreateEngine(flags);

                // also, allow access to the PyRevitLoader internals
                Engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);

                // also, allow access to the PyRevitRuntime internals
                Engine.Runtime.LoadAssembly(typeof(ScriptExecutor).Assembly);

                // reference RevitAPI and RevitAPIUI
                Engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
                Engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

                // save the default stream for later resetting the streams
                DefaultOutputStreamConfig = new Tuple<Stream, System.Text.Encoding>(Engine.Runtime.IO.OutputStream, Engine.Runtime.IO.OutputEncoding);
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

        private void SetupStdlib(Microsoft.Scripting.Hosting.ScriptEngine engine) {
            // ask PyRevitLoader to add it's resource ZIP file that contains the IronPython
            // standard library to this engine
            var tempExec = new PyRevitLoader.ScriptExecutor();
            tempExec.AddEmbeddedLib(engine);
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            Engine.Runtime.IO.SetOutput(runtime.OutputStream, System.Text.Encoding.UTF8);
            Engine.Runtime.IO.SetInput(runtime.OutputStream, System.Text.Encoding.UTF8);
        }

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(Engine);

            // Add timestamp and executuin uuid
            builtin.SetVariable("__execid__", runtime.ExecId);
            builtin.SetVariable("__timestamp__", runtime.ExecTimestamp);

            // Let commands know if they're being run in a cached engine
            builtin.SetVariable("__cachedengine__", RecoveredFromCache);

            // Add current engine id to builtins
            builtin.SetVariable("__cachedengineid__", TypeId);

            // Add this script executor to the the builtin to be globally visible everywhere
            // This support pyrevit functionality to ask information about the current executing command
            builtin.SetVariable("__scriptruntime__", runtime);

            // Add host application handle to the builtin to be globally visible everywhere
            if (runtime.UIApp != null)
                builtin.SetVariable("__revit__", runtime.UIApp);
            else if (runtime.UIControlledApp != null)
                builtin.SetVariable("__revit__", runtime.UIControlledApp);
            else if (runtime.App != null)
                builtin.SetVariable("__revit__", runtime.App);
            else
                builtin.SetVariable("__revit__", (object)null);

            // Adding data provided by IExternalCommand.Execute
            builtin.SetVariable("__commanddata__", runtime.ScriptRuntimeConfigs.CommandData);
            builtin.SetVariable("__elements__", runtime.ScriptRuntimeConfigs.SelectedElements);

            // Add ui button handle
            builtin.SetVariable("__uibutton__", runtime.UIControl);

            // Adding information on the command being executed
            builtin.SetVariable("__commandpath__", Path.GetDirectoryName(runtime.ScriptData.ScriptPath));
            builtin.SetVariable("__configcommandpath__", Path.GetDirectoryName(runtime.ScriptData.ConfigScriptPath));
            builtin.SetVariable("__commandname__", runtime.ScriptData.CommandName);
            builtin.SetVariable("__commandbundle__", runtime.ScriptData.CommandBundle);
            builtin.SetVariable("__commandextension__", runtime.ScriptData.CommandExtension);
            builtin.SetVariable("__commanduniqueid__", runtime.ScriptData.CommandUniqueId);
            builtin.SetVariable("__commandcontrolid__", runtime.ScriptData.CommandControlId);
            builtin.SetVariable("__forceddebugmode__", runtime.ScriptRuntimeConfigs.DebugMode);
            builtin.SetVariable("__shiftclick__", runtime.ScriptRuntimeConfigs.ConfigMode);

            // Add reference to the results dictionary
            // so the command can add custom values for logging
            builtin.SetVariable("__result__", runtime.GetResultsDictionary());

            // EVENT HOOKS BUILTINS ----------------------------------------------------------------------------------
            // set event arguments for engine
            builtin.SetVariable("__eventsender__", runtime.ScriptRuntimeConfigs.EventSender);
            builtin.SetVariable("__eventargs__", runtime.ScriptRuntimeConfigs.EventArgs);
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
            var pythonArgv = new IronPython.Runtime.List();
            // for python make sure the first argument is the script
            pythonArgv.append(runtime.ScriptSourceFile);
            pythonArgv.extend(runtime.ScriptRuntimeConfigs.Arguments);
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
