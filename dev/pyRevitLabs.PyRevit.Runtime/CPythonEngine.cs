using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;

// cpython
using Python.Runtime;
using CpyRuntime = Python.Runtime.Runtime;

using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public class CPythonEngine : ScriptEngine {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private List<string> _sysPaths = new List<string>();

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            UseNewEngine = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            // if this is the first run
            if (!RecoveredFromCache) {
                // load Python DLL
                CpyRuntime.PythonDLL = GetPythonDll(runtime);
                // initialize
                PythonEngine.ProgramName = "pyrevit";
                if (!PythonEngine.IsInitialized) {
                        PythonEngine.Initialize();
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

        public override void Shutdown() {
            CleanupBuiltins();
            CleanupStreams();
            PythonEngine.Shutdown();
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
            if (!string.IsNullOrEmpty(pythonPath))
            {
                var paths = pythonPath.Split(Path.PathSeparator);
                foreach (var path in paths)
                {
                    if (!string.IsNullOrWhiteSpace(path) && Directory.Exists(path)) 
                    {
                        sysPaths.Append(new PyString(path)); 
                    }
                }
            }

            // now add the search paths for the script bundle
            foreach (string searchPath in runtime.ScriptRuntimeConfigs.SearchPaths)
            {
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

        private void StoreSearchPaths() {
            var currentSysPath = GetSysPaths();
            _sysPaths = new List<string>();
            foreach (var path in currentSysPath)
            {
                _sysPaths.Add(path.As<string>());
            }
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

        private string GetPythonDll(ScriptRuntime runtime)
        {
            // PyRevitConfigs.GetCPythonEngineVersion()
            var engineVersion = new PyRevitEngineVersion(int.Parse(runtime.EngineVersion));
            var attachment = PyRevitAttachments.GetAttached(int.Parse(runtime.App.VersionNumber));
            var clone = attachment.Clone;
            var engine = clone.GetCPythonEngine(engineVersion);
            var dllPath = engine.AssemblyPath;
            if (!File.Exists(dllPath))
            {
                throw new Exception(string.Format("Python DLL not found at {0}", dllPath));
            }
            return dllPath;
        }
    }
}
