using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;

// cpython
using Python.Runtime;
using CpyRuntime = Python.Runtime.Runtime;

using pyRevitLabs.PyRevit;
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
                PythonEngine.ProgramName = "pyrevit";
                using (Py.GIL()) {
                    if (!PythonEngine.IsInitialized)
                        CpyRuntime.PythonDLL = GetPythonDll(runtime);
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
                // Setup the builtins
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
            var builtInsDict = new PyDict();
            // Add timestamp and executuin uuid
            builtInsDict.SetItem("__execid__".ToPython(), runtime.ExecId.ToPython());
            builtInsDict.SetItem("__timestamp__".ToPython(), runtime.ExecTimestamp.ToPython());

            builtInsDict.SetItem("__cachedengine__".ToPython(), RecoveredFromCache.ToPython());
            builtInsDict.SetItem("__cachedengineid__".ToPython(), TypeId.ToPython());
            builtInsDict.SetItem("__scriptruntime__".ToPython(), runtime.ToPython());

            if (runtime.UIApp != null)
                builtInsDict.SetItem("__revit__".ToPython(), runtime.UIApp.ToPython());
            else if (runtime.UIControlledApp != null)
                builtInsDict.SetItem("__revit__".ToPython(), runtime.UIControlledApp.ToPython());
            else if (runtime.App != null)
                builtInsDict.SetItem("__revit__".ToPython(), runtime.App.ToPython());
            else
                builtInsDict.SetItem("__revit__".ToPython(), PyObject.FromManagedObject(null));

            // Adding data provided by IExternalCommand.Execute
            builtInsDict.SetItem("__commanddata__".ToPython(), runtime.ScriptRuntimeConfigs.CommandData.ToPython());
            builtInsDict.SetItem("__elements__".ToPython(), runtime.ScriptRuntimeConfigs.SelectedElements.ToPython());

            // Add ui button handle
            builtInsDict.SetItem("__uibutton__".ToPython(), runtime.UIControl.ToPython());

            // Adding information on the command being executed
            builtInsDict.SetItem("__commandpath__".ToPython(), Path.GetDirectoryName(runtime.ScriptData.ScriptPath).ToPython());
            builtInsDict.SetItem("__configcommandpath__".ToPython(), Path.GetDirectoryName(runtime.ScriptData.ConfigScriptPath).ToPython());
            builtInsDict.SetItem("__commandname__".ToPython(), runtime.ScriptData.CommandName.ToPython());
            builtInsDict.SetItem("__commandbundle__".ToPython(), runtime.ScriptData.CommandBundle.ToPython());
            builtInsDict.SetItem("__commandextension__".ToPython(), runtime.ScriptData.CommandExtension.ToPython());
            builtInsDict.SetItem("__commanduniqueid__".ToPython(), runtime.ScriptData.CommandUniqueId.ToPython());
            builtInsDict.SetItem("__commandcontrolid__".ToPython(), runtime.ScriptData.CommandControlId.ToPython());
            builtInsDict.SetItem("__forceddebugmode__".ToPython(), runtime.ScriptRuntimeConfigs.DebugMode.ToPython());
            builtInsDict.SetItem("__shiftclick__".ToPython(), runtime.ScriptRuntimeConfigs.ConfigMode.ToPython());

            // Add reference to the results dictionary
            // so the command can add custom values for logging
            builtInsDict.SetItem("__result__".ToPython(), runtime.GetResultsDictionary().ToPython());

            // EVENT HOOKS BUILTINS ----------------------------------------------------------------------------------
            // set event arguments for engine
            builtInsDict.SetItem("__eventsender__".ToPython(), runtime.ScriptRuntimeConfigs.EventSender.ToPython());
            builtInsDict.SetItem("__eventargs__".ToPython(), runtime.ScriptRuntimeConfigs.EventArgs.ToPython());

            module.SetBuiltins(builtInsDict);
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

            // manually add PYTHONPATH since we are overwriting the sys paths
            var pythonPath = Environment.GetEnvironmentVariable("PYTHONPATH");
            if (!string.IsNullOrEmpty(pythonPath)) {
                var searthPathStr = new PyString(pythonPath);
                sysPaths.Append(searthPathStr);
            }

            // now add the search paths for the script bundle
            foreach (string searchPath in runtime.ScriptRuntimeConfigs.SearchPaths) {
                var searthPathStr = new PyString(searchPath);
                sysPaths.Append(searthPathStr);
            }
        }

        private void SetupArguments(ref ScriptRuntime runtime) {
            // setup arguments (sets sys.argv)
            PyObject sys = PyModule.Import("sys");
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
            foreach (var path in currentSysPath) {
                _sysPaths.Add(path.As<string>());
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
            PyObject sys = PyModule.Import("sys");
            PyObject sysPathsObj = sys.GetAttr("path");
            return PyList.AsList(sysPathsObj);
        }

        private void SetSysPaths(PyList sysPaths) {
            PyObject sys = PyModule.Import("sys");
            sys.SetAttr("path", sysPaths);
        }

        private string GetPythonDll(ScriptRuntime runtime) {
            var engineVersion = new PyRevitEngineVersion(int.Parse(runtime.EngineVersion));
            var attachment = PyRevitAttachments.GetAttached(int.Parse(runtime.App.VersionNumber));
            var clone = attachment.Clone;
            var engine = clone.GetEngine(engineVersion);
            // TODO: build the dll name from the major+minor version, or add it to pyrevitfile
            return Path.Combine(clone.ClonePath, engine.Path, "python312.dll");
        }
    }
}
