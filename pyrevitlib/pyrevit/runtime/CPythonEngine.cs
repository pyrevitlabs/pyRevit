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
                // initialize
                using (Py.GIL()) {
                    if (!PythonEngine.IsInitialized)
                        PythonEngine.Initialize();
                }
                // if this is a new engine, save the syspaths
                StoreSearchPaths();
            }

            SetupBuiltins(ref runtime);
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

                // execute
                try {
                    scope.Exec(scriptContents);
                }
                catch (PythonException cpyex) {
                    string cleanedPyTraceback = string.Empty;
                    string pyNetTraceback = string.Empty;
                    runtime.OutputStream.WriteError(cpyex.StackTrace, ScriptEngineType.CPython);
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

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            // get builtins
            IntPtr builtins = CpyRuntime.PyEval_GetBuiltins();

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
                SetVariable(builtins, "__revit__", null);

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
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            // set output stream
            PyObject sys = PythonEngine.ImportModule("sys");
            sys.SetAttr("stdout", PyObject.FromManagedObject(runtime.OutputStream));
        }

        private void SetupCaching(ref ScriptRuntime runtime) {
            // set output stream
            PyObject sys = PythonEngine.ImportModule("sys");
            // dont write bytecode (__pycache__)
            // https://docs.python.org/3.7/library/sys.html?highlight=pythondontwritebytecode#sys.dont_write_bytecode
            sys.SetAttr("dont_write_bytecode", PyObject.FromManagedObject(true));
        }

        private void SetupSearchPaths(ref ScriptRuntime runtime) {
            // set sys paths
            PyList sysPaths = RestoreSearchPaths();

            // manually add PYTHONPATH since we are overwriting the sys paths
            var pythonPath = Environment.GetEnvironmentVariable("PYTHONPATH");
            if (pythonPath != null && pythonPath != string.Empty) {
                var searthPathStr = new PyString(pythonPath);
                sysPaths.Insert(0, searthPathStr);
            }

            // now add the search paths for the script bundle
            foreach (string searchPath in runtime.ScriptRuntimeConfigs.SearchPaths.Reverse<string>()) {
                var searthPathStr = new PyString(searchPath);
                sysPaths.Insert(0, searthPathStr);
            }
        }

        private void SetupArguments(ref ScriptRuntime runtime) {
            // setup arguments (sets sys.argv)
            PyObject sys = PythonEngine.ImportModule("sys");
            PyObject sysArgv = sys.GetAttr("argv");

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
            long itemsCount = currentSysPath.Length();
            for (long i = 0; i < itemsCount; i++) {
                BorrowedReference item = 
                    CpyRuntime.PyList_GetItem(currentSysPath.Handle, i);
                string path = CpyRuntime.GetManagedString(item);
                _sysPaths.Add(path);
            }
        }

        private PyList RestoreSearchPaths() {
            var newList = new PyList();
            int i = 0;
            foreach (var searchPath in _sysPaths) {
                var searthPathStr = new PyString(searchPath);
                newList.Insert(i, searthPathStr);
                i++;
            }
            SetSysPaths(newList);
            return newList;
        }

        private PyList GetSysPaths() {
            // set sys paths
            PyObject sys = PythonEngine.ImportModule("sys");
            PyObject sysPathsObj = sys.GetAttr("path");
            return PyList.AsList(sysPathsObj);
        }

        private void SetSysPaths(PyList sysPaths) {
            PyObject sys = PythonEngine.ImportModule("sys");
            sys.SetAttr("path", sysPaths);
        }

        private static void SetVariable(IntPtr? globals, string key, IntPtr value) {
            CpyRuntime.PyDict_SetItemString(
                pointer: globals.Value,
                key: key,
                value: value
            );
        }

        private static void SetVariable(IntPtr? globals, string key, object value) {
            SetVariable(globals, key, PyObject.FromManagedObject(value).Handle);
        }
    }
}
