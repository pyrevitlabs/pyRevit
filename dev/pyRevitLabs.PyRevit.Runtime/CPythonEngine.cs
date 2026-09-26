using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;

// cpython
using Python.Runtime;
using CpyRuntime = Python.Runtime.Runtime;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Json;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public class CPythonEngineConfigs : ScriptEngineConfigs {
        public bool clean = false;
    }

    /// <summary>
    /// Runs <c>#! python3</c> commands on the process-wide CPython interpreter via pythonnet.
    /// </summary>
    /// <remarks>
    /// <para>
    /// The interpreter and its pythonnet metatype are a process-wide singleton that outlives the
    /// engine object: a Reload drops the engine from the session cache and the next CPython command
    /// re-attaches to the still-running interpreter instead of starting a new one. See
    /// <see cref="Shutdown"/> for why the interpreter is never torn down mid-session.
    /// </para>
    /// <para>
    /// Invariant: <see cref="PythonEngine.Initialize"/> is only ever called on the first CPython
    /// command of the Revit process. Everything pythonnet treats as initialize-only configuration
    /// (<see cref="CpyRuntime.PythonDLL"/>, <see cref="PythonEngine.ProgramName"/>) must stay
    /// behind the same guard, because pythonnet rejects those assignments once the runtime is up.
    /// </para>
    /// <para>
    /// Consequence: the <c>clean</c> engine config yields a fresh engine object but not a fresh
    /// interpreter, so <c>sys.modules</c> entries imported before a Reload survive it, as do the
    /// CLR type wrappers the metatype holds for the pre-Reload runtime assembly.
    /// </para>
    /// </remarks>
    public class CPythonEngine : ScriptEngine {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public CPythonEngineConfigs ExecEngineConfigs = new CPythonEngineConfigs();
        private List<string> _sysPaths = new List<string>();

        private static List<string> _interpreterSearchPaths;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            try {
                ExecEngineConfigs = JsonConvert.DeserializeObject<CPythonEngineConfigs>(
                    runtime.ScriptRuntimeConfigs.EngineConfigs
                ) ?? ExecEngineConfigs;
            }
            catch { }

            // If the user is asking to refresh the cached engine for the command,
            UseNewEngine = ExecEngineConfigs.clean || runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            // if this is the first run
            if (!RecoveredFromCache) {
                if (!PythonEngine.IsInitialized) {
                    // load Python DLL
                    CpyRuntime.PythonDLL = GetPythonDll(runtime);
                    // initialize
                    PythonEngine.ProgramName = "pyrevit";
                    try {
                        PythonEngine.Initialize();
                    }
                    catch (Exception ex) when (
                        ex.ToString().IndexOf("DesktopConnector", StringComparison.OrdinalIgnoreCase) >= 0) {
                        // Pythonnet scans all AppDomain assemblies during Initialize().
                        // If a Revit document was opened, ADC assemblies are loaded but
                        // DesktopConnectorInterop may be missing (ADC not installed).
                        // Pythonnet may still have initialized successfully despite this.
                        logger.Warn("CPython init encountered missing DesktopConnector assembly: {0}", ex.Message);
                        if (!PythonEngine.IsInitialized) {
                            throw new Exception(
                                "CPython engine failed to initialize. "
                                + "DesktopConnectorInterop assembly could not be loaded. "
                                + "Install Autodesk Desktop Connector or retry before opening a document.",
                                ex);
                        }
                    }
                }
                else {
                    logger.Debug(
                        "CPython engine {0} re-attaching to the interpreter already up in this process.",
                        Id
                        );
                    WarnOnPythonVersionChange(ref runtime);
                    DropStaleSessionModules();
                }
                // if this is a new engine, save the syspaths
                StoreSearchPaths();
            }

            SetupStreams(ref runtime);
            SetupCaching(ref runtime);
            SetupSearchPaths(ref runtime);
            SetupArguments(ref runtime);
        }

        public override int Execute(ref ScriptRuntime runtime) {
            int result = ScriptExecutorResultCodes.Succeeded;

            using (Py.GIL()) {
                // read script
                var scriptContents = File.ReadAllText(runtime.ScriptSourceFile, encoding: System.Text.Encoding.UTF8);

                // create new scope and set globals
                var scope = Py.CreateScope("__main__");
                scope.Set("__file__", runtime.ScriptSourceFile);
                // set up builtins
                SetupBuiltins(ref runtime, scope);
                // execute
                try {
                    scope.Exec(scriptContents);
                }
                catch (PythonException cpyex) {
                    string cleanedPyTraceback = string.Empty;
                    string pyNetTraceback = string.Empty;
                    if (cpyex.StackTrace != null && cpyex.StackTrace != string.Empty) {
                        var traceBackParts = cpyex.StackTrace.Split(']');
                        int nextIdx = 0;
                        // if stack trace contains file info, clean it up
                        if (traceBackParts.Count() == 2) {
                            nextIdx = 1;
                            string pyTraceback = traceBackParts[0].Trim() + "]";
                            cleanedPyTraceback = string.Empty;
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
                        }
                        // grab the dotnet cpython stack trace
                        pyNetTraceback = traceBackParts[nextIdx].Trim();
                    }

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
                    runtime.OutputStream.WriteError(traceMessage, ScriptEngineType.CPython);
                    result = ScriptExecutorResultCodes.ExecutionException;
                }
                catch (Exception ex) {
                    runtime.OutputStream.WriteError(ex.Message, ScriptEngineType.CPython);
                    result = ScriptExecutorResultCodes.ExecutionException;
                }
                finally {
                    // remove scope
                    scope.Dispose();
                }
            }

            return result;
        }

        public override void Stop(ref ScriptRuntime runtime) {
        }

        /// <summary>
        /// Releases the engine back to the session cache, on Reload or on Refresh Engine.
        /// </summary>
        /// <remarks>
        /// <para>
        /// The CPython interpreter is deliberately left running. pythonnet's
        /// <c>PythonEngine.Shutdown</c> is a soft shutdown: it disposes the CLR metatype, import
        /// hook and managed type wrappers while the interpreter stays alive, and stashes that state
        /// as a <c>BinaryFormatter</c> blob in <c>sys.clr_data</c> for the next
        /// <c>PythonEngine.Initialize</c> to read back. Reload duplicates assemblies into Revit's
        /// assembly load context, so deserializing that blob fails with "Invalid BinaryFormatter
        /// stream" and leaves pythonnet flagged as initialized but missing the metatype it skipped
        /// re-creating, wedging every later CPython command for the rest of the Revit session.
        /// </para>
        /// <para>
        /// Leaving the interpreter up skips the stash entirely, so post-Reload commands reuse the
        /// live runtime. Final process shutdown is unaffected: pythonnet subscribes to
        /// <see cref="AppDomain"/>'s process-exit notification on initialize and tears the runtime
        /// down there with <c>Runtime.ProcessIsTerminating</c> set, so nothing is stashed at Revit
        /// exit. That hook is also the reason this path must not call
        /// <c>PythonEngine.Shutdown</c>: doing so unsubscribes it.
        /// </para>
        /// <para>
        /// Invariant: never call <c>PythonEngine.Shutdown</c> from this path. It is the single
        /// funnel for both Reload (<c>ScriptEngineManager.ClearEngines</c>) and Refresh Engine
        /// (<c>ScriptEngineManager.SetCachedEngine</c>), so a single call here would break every
        /// post-Reload CPython command, not just the reloaded one.
        /// </para>
        /// </remarks>
        public override void Shutdown() {
            CleanupBuiltins();
            CleanupStreams();
            logger.Debug(
                "CPython engine {0} released; interpreter left up for the lifetime of the Revit process.",
                Id
                );
        }

        private void SetupBuiltins(ref ScriptRuntime runtime, PyModule module) {
            var builtins = new PyDict(module.Variables()["__builtins__"]);

            // Add timestamp and executuin uuid
            SetVariable(builtins, "__execid__", runtime.ExecId);
            SetVariable(builtins, "__timestamp__", runtime.ExecTimestamp);

            // set builtins
            SetVariable(builtins, "__cachedengine__", RecoveredFromCache);
            SetVariable(builtins, "__cachedengineid__", TypeId);
            SetVariable(builtins, "__scriptruntime__", runtime);

            if (runtime.UIApp != null)
                SetVariable(builtins, "__revit__", runtime.UIApp);
            else if (runtime.UIControlledApp != null)
                SetVariable(builtins, "__revit__", runtime.UIControlledApp);
            else if (runtime.App != null)
                SetVariable(builtins, "__revit__", runtime.App);
            else
                builtins.SetItem("__revit__".ToPython(), PyObject.FromManagedObject(null));

            // Adding data provided by IExternalCommand.Execute
            SetVariable(builtins, "__commanddata__", runtime.ScriptRuntimeConfigs.CommandData);
            SetVariable(builtins, "__elements__", runtime.ScriptRuntimeConfigs.SelectedElements);

            // Add ui button handle
            SetVariable(builtins, "__uibutton__", runtime.UIControl);

            // Adding information on the command being executed
            SetVariable(builtins, "__commandpath__", Path.GetDirectoryName(runtime.ScriptData.ScriptPath));
            SetVariable(builtins, "__configcommandpath__", Path.GetDirectoryName(runtime.ScriptData.ConfigScriptPath));
            SetVariable(builtins, "__commandname__", runtime.ScriptData.CommandName);
            SetVariable(builtins, "__commandbundle__", runtime.ScriptData.CommandBundle);
            SetVariable(builtins, "__commandextension__", runtime.ScriptData.CommandExtension);
            SetVariable(builtins, "__commanduniqueid__", runtime.ScriptData.CommandUniqueId);
            SetVariable(builtins, "__commandcontrolid__", runtime.ScriptData.CommandControlId);
            SetVariable(builtins, "__forceddebugmode__", runtime.ScriptRuntimeConfigs.DebugMode);
            SetVariable(builtins, "__shiftclick__", runtime.ScriptRuntimeConfigs.ConfigMode);

            // Add reference to the results dictionary
            // so the command can add custom values for logging
            SetVariable(builtins, "__result__", runtime.GetResultsDictionary());

            // EVENT HOOKS BUILTINS ----------------------------------------------------------------------------------
            // set event arguments for engine
            SetVariable(builtins, "__eventsender__", runtime.ScriptRuntimeConfigs.EventSender);
            SetVariable(builtins, "__eventargs__", runtime.ScriptRuntimeConfigs.EventArgs);

            if (runtime.ScriptRuntimeConfigs?.Variables != null) {
                foreach (var variable in runtime.ScriptRuntimeConfigs.Variables) {
                    SetVariable(builtins, variable.Key, variable.Value);
                }
            }

            module.SetBuiltins(builtins);
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            // set output stream
            PyObject sys = PyModule.Import("sys");
            var baseStream = PyObject.FromManagedObject(runtime.OutputStream);
            sys.SetAttr("stdout", baseStream);
            sys.SetAttr("stdin", baseStream);
            sys.SetAttr("stderr", baseStream);
        }

        private void SetupCaching(ref ScriptRuntime runtime) {
            // set output stream
            PyObject sys = PyModule.Import("sys");
            // dont write bytecode (__pycache__)
            // https://docs.python.org/3.7/library/sys.html?highlight=pythondontwritebytecode#sys.dont_write_bytecode
            sys.SetAttr("dont_write_bytecode", PyObject.FromManagedObject(true));
        }

        private void SetupSearchPaths(ref ScriptRuntime runtime) {
            // set sys paths
            PyList sysPaths = RestoreSearchPaths();

            // manually add each path in PYTHONPATH since we are overwriting the sys paths
            var pythonPath = Environment.GetEnvironmentVariable("PYTHONPATH");
            if (!string.IsNullOrEmpty(pythonPath)) {
                var paths = pythonPath.Split(Path.PathSeparator);
                foreach (var path in paths) {
                    if (!string.IsNullOrWhiteSpace(path) && Directory.Exists(path)) {
                        sysPaths.Append(new PyString(path));
                    }
                }
            }

            // now add the search paths for the script bundle
            foreach (string searchPath in runtime.ScriptRuntimeConfigs.SearchPaths) {
                sysPaths.Append(new PyString(searchPath));
            }
        }

        private void SetupArguments(ref ScriptRuntime runtime) {
            // setup arguments (sets sys.argv)
            PyObject sys = PyModule.Import("sys");

            var pythonArgv = new PyList();

            // for python make sure the first argument is the script
            var scriptSourceStr = new PyString(runtime.ScriptSourceFile);
            pythonArgv.Append(scriptSourceStr);

            // add the rest of the args
            foreach (string arg in runtime.ScriptRuntimeConfigs.Arguments) {
                var argStr = new PyString(arg);
                pythonArgv.Append(argStr);
            }

            sys.SetAttr("argv", pythonArgv);
        }

        private void CleanupBuiltins() {

        }

        private void CleanupStreams() {

        }

        /// <summary>
        /// Warn when the configured CPython version is not the one this process is running.
        /// </summary>
        /// <remarks>
        /// The interpreter is initialized once per process, so a version change only takes effect
        /// after Revit restarts. Silently keeping the old interpreter would run every tool on a
        /// version the user no longer asked for.
        /// </remarks>
        private void WarnOnPythonVersionChange(ref ScriptRuntime runtime) {
            try {
                var configured = GetPythonDll(runtime);
                if (!string.IsNullOrEmpty(CpyRuntime.PythonDLL)
                        && !string.Equals(configured, CpyRuntime.PythonDLL, StringComparison.OrdinalIgnoreCase)) {
                    logger.Warn(
                        "CPython is configured for \"{0}\" but this Revit process is running \"{1}\". "
                            + "The change takes effect the next time Revit starts.",
                        configured, CpyRuntime.PythonDLL);
                }
            }
            catch (Exception ex) {
                logger.Debug(ex, "Could not compare the configured CPython version with the running one");
            }
        }

        /// <summary>
        /// Forget the pyRevit modules this interpreter imported for a previous session.
        /// </summary>
        /// <remarks>
        /// A re-attaching engine reuses the interpreter, so a module imported before a session
        /// reload is still cached in <c>sys.modules</c> and keeps whatever host objects it bound
        /// then - a reloaded session would otherwise run against the previous session's handles.
        /// Only pyRevit's own modules are dropped; site-packages and the standard library stay.
        /// </remarks>
        private static void DropStaleSessionModules() {
            using (Py.GIL()) {
                try {
                    var scope = Py.CreateScope();
                    scope.Exec(
                        "import sys, importlib\n"
                            + "for _pyrevit_name in [_n for _n in list(sys.modules) "
                            + "if _n == 'pyrevit' or _n.startswith('pyrevit.')]:\n"
                            + "    del sys.modules[_pyrevit_name]\n"
                            + "importlib.invalidate_caches()\n");
                }
                catch (Exception ex) {
                    logger.Warn(ex, "Could not drop the pyRevit modules cached by the previous session");
                }
            }
        }

        private void StoreSearchPaths() {            if (_interpreterSearchPaths == null) {
                _interpreterSearchPaths = new List<string>();
                foreach (var path in GetSysPaths()) {
                    _interpreterSearchPaths.Add(path.As<string>());
                }
            }

            _sysPaths = new List<string>(_interpreterSearchPaths);
        }

        private PyList RestoreSearchPaths() {
            var newList = new PyList();
            foreach (var searchPath in _sysPaths) {
                newList.Append(new PyString(searchPath));
            }
            SetSysPaths(newList);
            return newList;
        }

        private PyList GetSysPaths() {
            // set sys paths
            PyObject sys = PyModule.Import("sys");
            PyObject sysPathsObj = sys.GetAttr("path");
            return PyList.AsList(sysPathsObj);
        }

        private void SetSysPaths(PyList sysPaths) {
            PyObject sys = PyModule.Import("sys");
            sys.SetAttr("path", sysPaths);
        }

        private static void SetVariable(PyDict container, string key, object value) {
            container.SetItem(key.ToPython(), value.ToPython());
        }

        private string GetPythonDll(ScriptRuntime runtime) {
            // PyRevitConfigs.GetCPythonEngineVersion()
            var engineVersion = new PyRevitEngineVersion(int.Parse(runtime.EngineVersion));
            var attachment = PyRevitAttachments.GetAttachedCached(int.Parse(runtime.App.VersionNumber));
            if (attachment?.Clone is null)
                throw new PyRevitException("pyRevit is not attached to this Revit version; cannot resolve the CPython engine.");
            var clone = attachment.Clone;
            var engine = clone.GetCPythonEngine(engineVersion);
            var dllPath = engine.AssemblyPath;
            if (!File.Exists(dllPath)) {
                throw new Exception(string.Format("Python DLL not found at {0}", dllPath));
            }
            return dllPath;
        }
    }
}
