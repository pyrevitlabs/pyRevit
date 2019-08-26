using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

// iron languages
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using IronPython.Hosting;
using IronPython.Compiler;
using IronPython.Runtime.Exceptions;
//using IronRuby;

// cpython
using pyRevitLabs.PythonNet;

// csharp
using System.CodeDom.Compiler;
using Microsoft.CSharp;
//vb
using Microsoft.VisualBasic;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public enum EngineType {
        IronPython,
        CPython,
        CSharp,
        Invoke,
        VisualBasic,
        IronRuby,
        Dynamo,
        Grasshopper,
        Content,
    }

    public class ExecutionEngineConfigs {
    }

    public class ExecutionEngine {
        public string Id { get; private set; }
        public string TypeId { get; private set; }

        public virtual bool IsRequiredByRuntime { get; set; }
        public virtual bool RecoveredFromCache { get; set; }

        public virtual void Init(ref ScriptRuntime runtime) {
            Id = CommonUtils.NewShortUUID();
            // unqiue typeid of the engine
            // based on session_id, engine type, and command extension
            TypeId = string.Join(":",
                runtime.SessionUUID,
                runtime.EngineType.ToString(),
                runtime.ScriptData.CommandExtension);

            // default to false since this is a new engine
            RecoveredFromCache = false;
        }

        public virtual void Start(ref ScriptRuntime runtime) { }
        public virtual int Execute(ref ScriptRuntime runtime) { return ExecutionResultCodes.Succeeded; }
        public virtual void Stop(ref ScriptRuntime runtime) { }
        public virtual void Shutdown() { }
    }

    public static class EngineManager {
        public static T GetEngine<T>(ref ScriptRuntime runtime) where T : ExecutionEngine, new() {
            T newEngine = new T();
            newEngine.Init(ref runtime);

            if (newEngine.IsRequiredByRuntime) {
                SetCachedEngine<T>(newEngine.TypeId, newEngine);
            }
            else {
                var cachedEngine = GetCachedEngine<T>(newEngine.TypeId);
                if (cachedEngine != null) {
                    newEngine = cachedEngine;
                    newEngine.RecoveredFromCache = true;
                }
                else
                    SetCachedEngine<T>(newEngine.TypeId, newEngine);
            }
            return newEngine;
        }

        // dicts need to be flexible type since multiple signatures of the ExecutionEngine
        // type could be placed inside this dictionary between pyRevit live reloads
        public static Dictionary<string, object> EngineDict {
            get {
                Dictionary<string, object> engineDict;
                var exstDict = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnginesDictKey);
                if (exstDict == null) {
                    engineDict = new Dictionary<string, object>();
                    AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnginesDictKey, engineDict);
                }
                else
                    engineDict = (Dictionary<string, object>)exstDict;
                return engineDict;
            }
        }

        public static Dictionary<string, object> ClearEngines(string excludeEngine = null) {
            // shutdown all existing engines
            foreach (KeyValuePair<string, object> engineRecord in EngineDict) {
                if (engineRecord.Key == excludeEngine)
                    continue;
                else
                    engineRecord.Value.GetType().GetMethod("Shutdown").Invoke(engineRecord.Value, new object[] { });
            }

            // create a new list
            var newEngineDict = new Dictionary<string, object>();
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnginesDictKey, newEngineDict);
            return newEngineDict;
        }

        private static T GetCachedEngine<T>(string engineTypeId) where T : ExecutionEngine, new() {
            if (EngineDict.ContainsKey(engineTypeId)) {
                try {
                    return (T)EngineDict[engineTypeId];
                }
                catch (InvalidCastException) {
                    return null;
                }
            }
            return null;
        }

        private static void SetCachedEngine<T>(string engineTypeId, T engine) where T : ExecutionEngine, new() {
            var cachedEngine = GetCachedEngine<T>(engine.TypeId);
            if (cachedEngine != null)
                cachedEngine.Shutdown();
            EngineDict[engineTypeId] = engine;
        }
    }

    public class IronPythonEngineConfigs : ExecutionEngineConfigs {
        public bool clean;
        public bool full_frame;
        public bool persistent;
    }

    public class IronPythonEngine : ExecutionEngine {
        public ScriptEngine Engine { get; private set; }
        public IronPythonEngineConfigs ExecEngineConfigs = new IronPythonEngineConfigs();

        public static Tuple<Stream, System.Text.Encoding> DefaultOutputStreamConfig {
            get {
                return (Tuple<Stream, System.Text.Encoding>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.IronPythonEngineDefaultStreamCfgKey);
            }

            set {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.IronPythonEngineDefaultStreamCfgKey, value);
            }
        }

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // extract engine configuration from runtime data
            try {
                ExecEngineConfigs = new JavaScriptSerializer().Deserialize<IronPythonEngineConfigs>(runtime.ScriptRuntimeConfigs.EngineConfigs);
            }
            catch {
                // if any errors switch to defaults
                ExecEngineConfigs.clean = false;
                ExecEngineConfigs.full_frame = false;
                ExecEngineConfigs.persistent = false;
            }

            // If the command required a fullframe engine
            // or if the command required a clean engine
            // of if the user is asking to refresh the cached engine for the command,
            IsRequiredByRuntime = ExecEngineConfigs.clean || ExecEngineConfigs.full_frame || runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            if (!RecoveredFromCache) {
                var flags = new Dictionary<string, object>();

                // default flags
                flags["LightweightScopes"] = true;

                if (ExecEngineConfigs.full_frame) {
                    flags["Frames"] = true;
                    flags["FullFrames"] = true;
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
                runtime.OutputStream.WriteError(string.Join(Environment.NewLine, errors.Errors.ToArray()), EngineType.IronPython);
                return ExecutionResultCodes.CompileException;
            }

            // Finally let's execute
            try {
                command.Execute(scope);
                return ExecutionResultCodes.Succeeded;
            }
            catch (SystemExitException) {
                // ok, so the system exited. That was bound to happen...
                return ExecutionResultCodes.SysExited;
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
                clrTraceMessage = string.Join("\n", ScriptOutputConfigs.ToCustomHtmlTags(ScriptOutputConfigs.CLRErrorHeader), clrTraceMessage);

                runtime.OutputStream.WriteError(ipyTraceMessage + "\n\n" + clrTraceMessage, EngineType.IronPython);
                return ExecutionResultCodes.ExecutionException;
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
            CleanupEngineBuiltins();
            CleanupStreams();
        }

        private void SetupStdlib(ScriptEngine engine) {
            // ask PyRevitLoader to add it's resource ZIP file that contains the IronPython
            // standard library to this engine
            var tempExec = new PyRevitLoader.ScriptExecutor();
            tempExec.AddEmbeddedLib(engine);
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            Engine.Runtime.IO.SetOutput(runtime.OutputStream, System.Text.Encoding.UTF8);
        }

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(Engine);

            // Let commands know if they're being run in a cached engine
            builtin.SetVariable("__cachedengine__", RecoveredFromCache);

            // Add current engine id to builtins
            builtin.SetVariable("__cachedengineid__", TypeId);

            // Add this script executor to the the builtin to be globally visible everywhere
            // This support pyrevit functionality to ask information about the current executing command
            builtin.SetVariable("__externalcommand__", runtime);

            // Add host application handle to the builtin to be globally visible everywhere
            if (runtime.UIApp != null)
                builtin.SetVariable("__revit__", runtime.UIApp);
            else if (runtime.UIControlledApp != null)
                builtin.SetVariable("__revit__", runtime.UIControlledApp);
            else if (runtime.App != null)
                builtin.SetVariable("__revit__", runtime.App);
            else
                builtin.SetVariable("__revit__", null);

            // Adding data provided by IExternalCommand.Execute
            builtin.SetVariable("__commanddata__", runtime.ScriptRuntimeConfigs.CommandData);
            builtin.SetVariable("__elements__", runtime.ScriptRuntimeConfigs.SelectedElements);

            // Adding information on the command being executed
            builtin.SetVariable("__commandpath__", Path.GetDirectoryName(runtime.ScriptData.ScriptPath));
            builtin.SetVariable("__configcommandpath__", Path.GetDirectoryName(runtime.ScriptData.ConfigScriptPath));
            builtin.SetVariable("__commandname__", runtime.ScriptData.CommandName);
            builtin.SetVariable("__commandbundle__", runtime.ScriptData.CommandBundle);
            builtin.SetVariable("__commandextension__", runtime.ScriptData.CommandExtension);
            builtin.SetVariable("__commanduniqueid__", runtime.ScriptData.CommandUniqueId);
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
            pythonArgv.extend(runtime.ScriptRuntimeConfigs.Arguments);
            sysmodule.SetVariable("argv", pythonArgv);
        }

        private void CleanupEngineBuiltins() {
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(Engine);

            builtin.SetVariable("__cachedengine__", (object)null);
            builtin.SetVariable("__cachedengineid__", (object)null);
            builtin.SetVariable("__externalcommand__", (object)null);
            builtin.SetVariable("__commanddata__", (object)null);
            builtin.SetVariable("__elements__", (object)null);
            builtin.SetVariable("__commandpath__", (object)null);
            builtin.SetVariable("__configcommandpath__", (object)null);
            builtin.SetVariable("__commandname__", (object)null);
            builtin.SetVariable("__commandbundle__", (object)null);
            builtin.SetVariable("__commandextension__", (object)null);
            builtin.SetVariable("__commanduniqueid__", (object)null);
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
        }
    }

    public class CPythonEngine : ExecutionEngine {
        private PyObject _sysPaths = null;
        private IntPtr _globals = IntPtr.Zero;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            IsRequiredByRuntime = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            if (!RecoveredFromCache) {
                using (Py.GIL()) {
                    // initialize
                    if (!PythonEngine.IsInitialized)
                        PythonEngine.Initialize();
                }
            }

            SetupStreams(ref runtime);
            SetupBuiltins(ref runtime);
            SetupSearchPaths(ref runtime);
            SetupArguments(ref runtime);
        }

        public override int Execute(ref ScriptRuntime runtime) {
            int result = ExecutionResultCodes.Succeeded;

            using (Py.GIL()) {
                var scriptContents = File.ReadAllText(runtime.ScriptSourceFile, encoding: System.Text.Encoding.UTF8);
                try {
                    PythonEngine.ExecUTF8(scriptContents, globals: _globals);
                }
                catch (PythonException cpyex) {
                    var traceBackParts = cpyex.StackTrace.Split(']');
                    string pyTraceback = traceBackParts[0].Trim() + "]";
                    string cleanedPyTraceback = string.Empty;
                    foreach (string tbLine in pyTraceback.ConvertFromTomlListString()) {
                        if (tbLine.Contains("File \"<string>\"")) {
                            var fixedTbLine = tbLine.Replace("File \"<string>\"", string.Format("File \"{0}\"", runtime.ScriptSourceFile));
                            cleanedPyTraceback += fixedTbLine;
                            var lineNo = new Regex(@"\,\sline\s(?<lineno>\d+)\,").Match(tbLine).Groups["lineno"].Value;
                            cleanedPyTraceback += scriptContents.Split('\n')[int.Parse(lineNo.Trim()) - 1] + "\n";
                        }
                        else {
                            cleanedPyTraceback += tbLine;
                        }
                    }

                    string pyNetTraceback = traceBackParts[1].Trim();

                    string traceMessage = string.Join(
                        "\n",
                        cpyex.Message,
                        cleanedPyTraceback,
                        cpyex.Source,
                        pyNetTraceback
                        );

                    // Print all errors to stdout and return cancelled to Revit.
                    // This is to avoid getting window prompts from Revit.
                    // Those pop ups are small and errors are hard to read.
                    traceMessage = traceMessage.NormalizeNewLine();
                    runtime.TraceMessage = traceMessage;
                    runtime.OutputStream.WriteError(traceMessage, EngineType.CPython);
                    result = ExecutionResultCodes.ExecutionException;
                }
                finally {
                }
            }

            return result;
        }

        public override void Stop(ref ScriptRuntime runtime) {
        }

        public override void Shutdown() {
            using (Py.GIL()) {
                // deref newly created globals
                pyRevitLabs.PythonNet.Runtime.XDecref(_globals);
                _globals = IntPtr.Zero;
            }
            PythonEngine.Shutdown();
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            // set output stream
            PyObject sys = PythonEngine.ImportModule("sys");
            sys.SetAttr("stdout", PyObject.FromManagedObject(runtime.OutputStream));
            // dont write bytecode (__pycache__)
            // https://docs.python.org/3.7/library/sys.html?highlight=pythondontwritebytecode#sys.dont_write_bytecode
            sys.SetAttr("dont_write_bytecode", PyObject.FromManagedObject(true));
        }

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            // get globals
            _globals = pyRevitLabs.PythonNet.Runtime.PyEval_GetGlobals();
            // get builtins
            IntPtr builtins = pyRevitLabs.PythonNet.Runtime.PyEval_GetBuiltins();
            if (_globals == IntPtr.Zero) {
                _globals = pyRevitLabs.PythonNet.Runtime.PyDict_New();
                SetVariable(_globals, "__builtins__", builtins);
            }

            // set builtins
            SetVariable(builtins, "__cachedengine__", RecoveredFromCache);
            SetVariable(builtins, "__cachedengineid__", TypeId);
            SetVariable(builtins, "__externalcommand__", runtime);

            if (runtime.UIApp != null)
                SetVariable(builtins, "__revit__", runtime.UIApp);
            else if (runtime.UIControlledApp != null)
                SetVariable(builtins, "__revit__", runtime.UIControlledApp);
            else if (runtime.App != null)
                SetVariable(builtins, "__revit__", runtime.App);
            else
                SetVariable(builtins, "__revit__", null);

            // Adding data provided by IExternalCommand.Execute
            SetVariable(builtins, "__commanddata__", runtime.ScriptRuntimeConfigs.CommandData);
            SetVariable(builtins, "__elements__", runtime.ScriptRuntimeConfigs.SelectedElements);

            // Adding information on the command being executed
            SetVariable(builtins, "__commandpath__", Path.GetDirectoryName(runtime.ScriptData.ScriptPath));
            SetVariable(builtins, "__configcommandpath__", Path.GetDirectoryName(runtime.ScriptData.ConfigScriptPath));
            SetVariable(builtins, "__commandname__", runtime.ScriptData.CommandName);
            SetVariable(builtins, "__commandbundle__", runtime.ScriptData.CommandBundle);
            SetVariable(builtins, "__commandextension__", runtime.ScriptData.CommandExtension);
            SetVariable(builtins, "__commanduniqueid__", runtime.ScriptData.CommandUniqueId);
            SetVariable(builtins, "__forceddebugmode__", runtime.ScriptRuntimeConfigs.DebugMode);
            SetVariable(builtins, "__shiftclick__", runtime.ScriptRuntimeConfigs.ConfigMode);

            // Add reference to the results dictionary
            // so the command can add custom values for logging
            SetVariable(builtins, "__result__", runtime.GetResultsDictionary());

            // EVENT HOOKS BUILTINS ----------------------------------------------------------------------------------
            // set event arguments for engine
            SetVariable(builtins, "__eventsender__", runtime.ScriptRuntimeConfigs.EventSender);
            SetVariable(builtins, "__eventargs__", runtime.ScriptRuntimeConfigs.EventArgs);

            // set globals
            var fileVarPyObject = new PyString(runtime.ScriptSourceFile);
            SetVariable(_globals, "__file__", fileVarPyObject.Handle);
        }

        private void SetupSearchPaths(ref ScriptRuntime runtime) {
            // set sys paths
            PyObject sys = PythonEngine.ImportModule("sys");
            PyObject sysPaths = sys.GetAttr("path");

            // if this is a new engine, save the syspaths
            if (!RecoveredFromCache) {
                _sysPaths = CopyPyList(sysPaths.Handle);
            }
            // otherwise reset to defautl before changing
            else {
                sysPaths = CopyPyList(_sysPaths.Handle);
                sys.SetAttr("path", sysPaths);
            }

            foreach (string searchPath in runtime.ScriptRuntimeConfigs.SearchPaths.Reverse<string>()) {
                var searthPathStr = new PyString(searchPath);
                pyRevitLabs.PythonNet.Runtime.PyList_Insert(sysPaths.Handle, 0, searthPathStr.Handle);
            }
        }

        private void SetupArguments(ref ScriptRuntime runtime) { }

        private static PyObject CopyPyList(IntPtr sourceList) {
            var newList = new PyList();
            long itemsCount = pyRevitLabs.PythonNet.Runtime.PyList_Size(sourceList);
            for (long i = 0; i < itemsCount; i++) {
                IntPtr listItem = pyRevitLabs.PythonNet.Runtime.PyList_GetItem(sourceList, i);
                pyRevitLabs.PythonNet.Runtime.PyList_Insert(newList.Handle, i, listItem);
            }
            return new PyObject(newList.Handle);
        }

        private static void SetVariable(IntPtr? globals, string key, IntPtr value) {
            pyRevitLabs.PythonNet.Runtime.PyDict_SetItemString(
                pointer: globals.Value,
                key: key,
                value: value
            );
        }

        private static void SetVariable(IntPtr? globals, string key, object value) {
            SetVariable(globals, key, PyObject.FromManagedObject(value).Handle);
        }
    }

    public class ExecParams {
        public string ScriptPath { get; set; }
        public string ConfigScriptPath { get; set; }
        public string CommandUniqueId { get; set; }
        public string CommandName { get; set; }
        public string CommandBundle { get; set; }
        public string CommandExtension { get; set; }
        public string HelpSource { get; set; }
        public bool RefreshEngine { get; set; }
        public bool ConfigMode { get; set; }
        public bool DebugMode { get; set; }
        public bool ExecutedFromUI { get; set; }
    }

    public class CLREngine : ExecutionEngine {
        private string scriptSig = string.Empty;
        private Assembly scriptAssm = null;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            IsRequiredByRuntime = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            // compile first
            // only if the signature doesn't match
            if (scriptSig == null || runtime.ScriptSourceFileSignature != scriptSig) {
                try {
                    scriptSig = runtime.ScriptSourceFileSignature;
                    scriptAssm = CompileCLRScript(ref runtime);
                }
                catch (Exception compileEx) {
                    string traceMessage = compileEx.ToString();
                    traceMessage = traceMessage.NormalizeNewLine();
                    runtime.TraceMessage = traceMessage;

                    // TODO: change to script output for all script types
                    if (runtime.InterfaceType == InterfaceType.ExternalCommand)
                        TaskDialog.Show(PyRevitConsts.ProductName, runtime.TraceMessage);

                    TaskDialog.Show(PyRevitConsts.ProductName, runtime.TraceMessage);

                    return ExecutionResultCodes.CompileException;
                }
            }

            // scriptAssm must have value
            switch (runtime.InterfaceType) {
                // if is an external command
                case InterfaceType.ExternalCommand:
                    try {
                        // execute now
                        var resultCode = ExecuteExternalCommand(scriptAssm, null, ref runtime);
                        if (resultCode == ExecutionResultCodes.ExternalInterfaceNotImplementedException)
                            TaskDialog.Show(PyRevitConsts.ProductName,
                                string.Format(
                                    "Can not find any type implementing IExternalCommand in assembly \"{0}\"",
                                    scriptAssm.Location
                                    ));
                        return resultCode;
                    }
                    catch (Exception execEx) {
                        string traceMessage = execEx.ToString();
                        traceMessage = traceMessage.NormalizeNewLine();
                        runtime.TraceMessage = traceMessage;
                        // TODO: same outp
                        TaskDialog.Show(PyRevitConsts.ProductName, traceMessage);

                        return ExecutionResultCodes.ExecutionException;
                    }

                // if is an event hook
                case InterfaceType.EventHandler:
                    try {
                        return ExecuteEventHandler(scriptAssm, ref runtime);
                    }
                    catch (Exception execEx) {
                        string traceMessage = execEx.ToString();
                        traceMessage = traceMessage.NormalizeNewLine();
                        runtime.TraceMessage = traceMessage;

                        TaskDialog.Show(PyRevitConsts.ProductName, runtime.TraceMessage);
                        return ExecutionResultCodes.ExecutionException;
                    }

                default:
                    return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
            }
        }

        public static IEnumerable<Type> GetTypesSafely(Assembly assembly) {
            try {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException ex) {
                return ex.Types.Where(x => x != null);
            }
        }

        public static Assembly CompileCLRScript(ref ScriptRuntime runtime) {
            // https://stackoverflow.com/a/3188953
            // read the script
            var scriptContents = File.ReadAllText(runtime.ScriptSourceFile);

            // read the referenced dlls from env vars
            // pyrevit sets this when loading
            string[] refFiles;
            var envDic = new EnvDictionary();
            if (envDic.ReferencedAssemblies.Length == 0) {
                var refs = AppDomain.CurrentDomain.GetAssemblies();
                refFiles = refs.Select(a => a.Location).ToArray();
            }
            else {
                refFiles = envDic.ReferencedAssemblies;
            }

            // create compiler parameters
            var compileParams = new CompilerParameters(refFiles);
            compileParams.OutputAssembly = Path.Combine(
                UserEnv.UserTemp,
                string.Format("{0}.dll", runtime.ScriptData.CommandName)
                );
            compileParams.CompilerOptions = string.Format("/optimize /define:REVIT{0}", runtime.App.VersionNumber);
            compileParams.GenerateInMemory = true;
            compileParams.GenerateExecutable = false;
            compileParams.ReferencedAssemblies.Add(typeof(ScriptExecutor).Assembly.Location);

            // determine which code provider to use
            CodeDomProvider compiler;
            var compConfig = new Dictionary<string, string>() { { "CompilerVersion", "v4.0" } };
            switch (runtime.EngineType) {
                case EngineType.CSharp:
                    compiler = new CSharpCodeProvider(compConfig);
                    break;
                case EngineType.VisualBasic:
                    compiler = new VBCodeProvider(compConfig);
                    break;
                default:
                    throw new Exception("Specified language does not have a compiler.");
            }

            // compile code first
            var res = compiler.CompileAssemblyFromSource(
                options: compileParams,
                sources: new string[] { scriptContents }
            );

            return res.CompiledAssembly;
        }

        public static int ExecuteExternalCommand(Assembly assmObj, string className, ref ScriptRuntime runtime) {
            foreach (Type assmType in GetTypesSafely(assmObj)) {
                if (assmType.IsClass) {
                    // find the appropriate type and execute
                    if (className != null) {
                        if (assmType.Name == className)
                            return ExecuteExternalCommandType(assmType, ref runtime);
                        else
                            continue;
                    }
                    else if (assmType.GetInterfaces().Contains(typeof(IExternalCommand)))
                        return ExecuteExternalCommandType(assmType, ref runtime);
                }
            }

            return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
        }

        public static int ExecuteExternalCommandType(Type extCommandType, ref ScriptRuntime runtime) {
            // create instance
            object extCommandInstance = Activator.CreateInstance(extCommandType);

            // set properties if available
            // set ExecParams
            foreach (var fieldInfo in extCommandType.GetFields()) {
                if (fieldInfo.FieldType == typeof(ExecParams)) {
                    fieldInfo.SetValue(
                        extCommandInstance,
                        new ExecParams {
                            ScriptPath = runtime.ScriptData.ScriptPath,
                            ConfigScriptPath = runtime.ScriptData.ConfigScriptPath,
                            CommandUniqueId = runtime.ScriptData.CommandUniqueId,
                            CommandName = runtime.ScriptData.CommandName,
                            CommandBundle = runtime.ScriptData.CommandBundle,
                            CommandExtension = runtime.ScriptData.CommandExtension,
                            HelpSource = runtime.ScriptData.HelpSource,
                            RefreshEngine = runtime.ScriptRuntimeConfigs.RefreshEngine,
                            ConfigMode = runtime.ScriptRuntimeConfigs.ConfigMode,
                            DebugMode = runtime.ScriptRuntimeConfigs.DebugMode,
                            ExecutedFromUI = runtime.ScriptRuntimeConfigs.ExecutedFromUI
                        });
                }
            }

            // reroute console output to runtime stream
            var existingOutStream = Console.Out;
            StreamWriter runtimeOutputStream = new StreamWriter(runtime.OutputStream);
            runtimeOutputStream.AutoFlush = true;
            Console.SetOut(runtimeOutputStream);

            // execute
            string commandMessage = string.Empty;
            extCommandType.InvokeMember(
                "Execute",
                BindingFlags.Default | BindingFlags.InvokeMethod,
                null,
                extCommandInstance,
                new object[] {
                    runtime.ScriptRuntimeConfigs.CommandData,
                    commandMessage,
                    runtime.ScriptRuntimeConfigs.SelectedElements}
                );

            // reroute console output back to original
            Console.SetOut(existingOutStream);
            runtimeOutputStream = null;

            return ExecutionResultCodes.Succeeded;
        }

        public static int ExecuteEventHandler(Assembly assmObj, ref ScriptRuntime runtime) {
            foreach (Type assmType in GetTypesSafely(assmObj))
                foreach (MethodInfo methodInfo in assmType.GetMethods()) {
                    var methodParams = methodInfo.GetParameters();
                    if (methodParams.Count() == 2
                            && methodParams[0].Name == "sender"
                            && (methodParams[1].Name == "e" || methodParams[1].Name == "args")) {
                        object extEventInstance = Activator.CreateInstance(assmType);
                        assmType.InvokeMember(
                            methodInfo.Name,
                            BindingFlags.Default | BindingFlags.InvokeMethod,
                            null,
                            extEventInstance,
                            new object[] {
                                    runtime.ScriptRuntimeConfigs.EventSender,
                                    runtime.ScriptRuntimeConfigs.EventArgs
                                }
                            );
                        return ExecutionResultCodes.Succeeded;
                    }
                }

            return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
        }
    }

    public class RubyEngine : ExecutionEngine {
        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            IsRequiredByRuntime = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            // TODO: ExecuteRubyScript
            TaskDialog.Show(PyRevitConsts.ProductName, "Ruby-Script Execution Engine Not Yet Implemented.");
            return ExecutionResultCodes.EngineNotImplementedException;
            //// https://github.com/hakonhc/RevitRubyShell/blob/master/RevitRubyShell/RevitRubyShellApplication.cs
            //// 1: ----------------------------------------------------------------------------------------------------
            //// start ruby interpreter
            //var engine = Ruby.CreateEngine();
            //var scope = engine.CreateScope();

            //// 2: ----------------------------------------------------------------------------------------------------
            //// Finally let's execute
            //try {
            //    // Run the code
            //    engine.ExecuteFile(pyrvtScript.ScriptSourceFile, scope);
            //    return ExecutionErrorCodes.Succeeded;
            //}
            //catch (SystemExitException) {
            //    // ok, so the system exited. That was bound to happen...
            //    return ExecutionErrorCodes.SysExited;
            //}
            //catch (Exception exception) {
            //    // show (power) user everything!
            //    string _dotnet_err_message = exception.ToString();
            //    string _ruby_err_messages = engine.GetService<ExceptionOperations>().FormatException(exception);

            //    // Print all errors to stdout and return cancelled to Revit.
            //    // This is to avoid getting window prompts from Revit.
            //    // Those pop ups are small and errors are hard to read.
            //    _ruby_err_messages = _ruby_err_messages.NormalizeNewLine();
            //    pyrvtScript.IronLanguageTraceBack = _ruby_err_messages;

            //    _dotnet_err_message = _dotnet_err_message.NormalizeNewLine();
            //    pyrvtScript.TraceMessage = _dotnet_err_message;

            //    _ruby_err_messages = string.Join(Environment.NewLine, ExternalConfig.irubyerrtitle, _ruby_err_messages);
            //    _dotnet_err_message = string.Join(Environment.NewLine, ExternalConfig.dotneterrtitle, _dotnet_err_message);

            //    pyrvtScript.OutputStream.WriteError(_ruby_err_messages + "\n\n" + _dotnet_err_message);
            //    return ExecutionErrorCodes.ExecutionException;
            //}
            //finally {
            //    // whatever
            //}
        }
    }

    public class InvokableDLLEngine : ExecutionEngine {
        private string scriptSig = string.Empty;
        private Assembly scriptAssm = null;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            IsRequiredByRuntime = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            try {
                // first argument is the script name
                // script.py assmFile:className
                if (runtime.ScriptRuntimeConfigs.Arguments.Count == 1) {
                    // load the binary data from the DLL
                    // Direct invoke commands use the config script source file to point
                    // to the target dll assembly location
                    string argumentString = runtime.ScriptRuntimeConfigs.Arguments.First();
                    string assmFile = argumentString;
                    string className = null;
                    if (argumentString.Contains("::")) {
                        var parts = argumentString.Split(
                            new string[] { "::" },
                            StringSplitOptions.RemoveEmptyEntries
                            );

                        assmFile = parts[0];
                        className = parts[1];
                    }

                    if (scriptSig == null || CommonUtils.GetFileSignature(assmFile) != scriptSig) {
                        scriptAssm = Assembly.Load(File.ReadAllBytes(assmFile));
                    }

                    var resultCode = CLREngine.ExecuteExternalCommand(scriptAssm, className, ref runtime);
                    if (resultCode == ExecutionResultCodes.ExternalInterfaceNotImplementedException)
                        TaskDialog.Show(PyRevitConsts.ProductName,
                            string.Format(
                                "Can not find type \"{0}\" in assembly \"{1}\"",
                                className,
                                scriptAssm.Location
                                ));
                    return resultCode;
                }
                else {
                    TaskDialog.Show(PyRevitConsts.ProductName, "Target assembly is not set correctly and can not be loaded.");
                    return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
                }
            }
            catch (Exception invokeEx) {
                TaskDialog.Show(PyRevitConsts.ProductName, invokeEx.Message);
                return ExecutionResultCodes.ExecutionException;
            }
            finally {
                // whatever
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

    public class ContentLoaderOptions : IFamilyLoadOptions {
        public bool OnFamilyFound(bool familyInUse, out bool overwriteParameterValues) {
            overwriteParameterValues = true;
            return overwriteParameterValues;
        }

        public bool OnSharedFamilyFound(Family sharedFamily, bool familyInUse, out FamilySource source, out bool overwriteParameterValues) {
            throw new NotImplementedException();
        }
    }
}
