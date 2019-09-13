using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;

// cpython
using pyRevitLabs.PythonNet;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    public class CPythonEngine : ScriptEngine {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private List<string> _sysPaths = new List<string>();
        private IntPtr _globals = IntPtr.Zero;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            UseNewEngine = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override void Start(ref ScriptRuntime runtime) {
            if (!RecoveredFromCache) {
                using (Py.GIL()) {
                    // initialize
                    if (!PythonEngine.IsInitialized)
                        PythonEngine.Initialize();
                }
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
                    runtime.OutputStream.WriteError(traceMessage, ScriptEngineType.CPython);
                    result = ScriptExecutorResultCodes.ExecutionException;
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

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            // get globals
            _globals = pyRevitLabs.PythonNet.Runtime.PyEval_GetGlobals();
            // get builtins
            IntPtr builtins = pyRevitLabs.PythonNet.Runtime.PyEval_GetBuiltins();
            if (_globals == IntPtr.Zero) {
                _globals = pyRevitLabs.PythonNet.Runtime.PyDict_New();
                SetVariable(_globals, "__builtins__", builtins);
            }

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

            // set globals
            var fileVarPyObject = new PyString(runtime.ScriptSourceFile);
            SetVariable(_globals, "__file__", fileVarPyObject.Handle);
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
            PyObject sys = PythonEngine.ImportModule("sys");
            PyObject sysPaths = sys.GetAttr("path");

            // if this is a new engine, save the syspaths
            if (!RecoveredFromCache) {
                SaveSearchPaths(sysPaths.Handle);
            }
            // otherwise reset to default before changing
            else {
                sysPaths = RestoreSearchPaths();
                sys.SetAttr("path", sysPaths);
            }

            foreach (string searchPath in runtime.ScriptRuntimeConfigs.SearchPaths.Reverse<string>()) {
                var searthPathStr = new PyString(searchPath);
                pyRevitLabs.PythonNet.Runtime.PyList_Insert(sysPaths.Handle, 0, searthPathStr.Handle);
            }
        }

        private void SetupArguments(ref ScriptRuntime runtime) {
            // setup arguments (sets sys.argv)
            PyObject sys = PythonEngine.ImportModule("sys");
            PyObject sysArgv = sys.GetAttr("argv");

            var pythonArgv = new PyList();

            // for python make sure the first argument is the script
            var scriptSourceStr = new PyString(runtime.ScriptSourceFile);
            pyRevitLabs.PythonNet.Runtime.PyList_Append(pythonArgv.Handle, scriptSourceStr.Handle);

            // add the rest of the args
            foreach (string arg in runtime.ScriptRuntimeConfigs.Arguments) {
                var argStr = new PyString(arg);
                pyRevitLabs.PythonNet.Runtime.PyList_Append(pythonArgv.Handle, argStr.Handle);
            }

            sys.SetAttr("argv", pythonArgv);
        }

        private static PyObject CopyPyList(IntPtr sourceList) {
            var newList = new PyList();
            long itemsCount = pyRevitLabs.PythonNet.Runtime.PyList_Size(sourceList);
            for (long i = 0; i < itemsCount; i++) {
                IntPtr listItem = pyRevitLabs.PythonNet.Runtime.PyList_GetItem(sourceList, i);
                pyRevitLabs.PythonNet.Runtime.PyList_Insert(newList.Handle, i, listItem);
            }
            return new PyObject(newList.Handle);
        }

        private void SaveSearchPaths(IntPtr sourceList) {
            _sysPaths = new List<string>();
            long itemsCount = pyRevitLabs.PythonNet.Runtime.PyList_Size(sourceList);
            for (long i = 0; i < itemsCount; i++) {
                IntPtr listItem = pyRevitLabs.PythonNet.Runtime.PyList_GetItem(sourceList, i);
                var value = new PyObject(listItem).As<string>();
                _sysPaths.Add(value);
            }
        }

        private PyObject RestoreSearchPaths() {
            var newList = new PyList();
            int i = 0;
            foreach (var searchPath in _sysPaths) {
                var searthPathStr = new PyString(searchPath);
                pyRevitLabs.PythonNet.Runtime.PyList_Insert(newList.Handle, i, searthPathStr.Handle);
                i++;
            }
            return newList;
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
}
