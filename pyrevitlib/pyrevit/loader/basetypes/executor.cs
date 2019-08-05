using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.Remoting;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.ApplicationServices;

// iron languages
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using IronPython.Runtime.Exceptions;
using IronPython.Compiler;
//using IronRuby;

// cpython
using Python.Runtime;

// csharp
using System.CodeDom.Compiler;
using Microsoft.CSharp;
//vb
using Microsoft.VisualBasic;


namespace PyRevitBaseClasses {
    /// Executes a script
    public class ScriptExecutor {
        /// Run the script and print the output to a new output window.
        public static int ExecuteScript(ref PyRevitScriptRuntime pyrvtCmd) {
            switch (pyrvtCmd.EngineType) {
                case EngineType.IronPython:
                    return ExecuteIronPythonScript(ref pyrvtCmd);
                case EngineType.CPython:
                    return ExecuteCPythonScript(ref pyrvtCmd);
                case EngineType.CSharp:
                    return ExecuteCSharpScript(ref pyrvtCmd);
                case EngineType.Invoke:
                    return ExecuteInvokableDLL(ref pyrvtCmd);
                case EngineType.VisualBasic:
                    return ExecuteVisualBasicScript(ref pyrvtCmd);
                case EngineType.IronRuby:
                    return ExecuteRubyScript(ref pyrvtCmd);
                case EngineType.Dynamo:
                    return ExecuteDynamoDefinition(ref pyrvtCmd);
                case EngineType.Grasshopper:
                    return ExecuteGrasshopperDocument(ref pyrvtCmd);
                default:
                    // should not get here
                    throw new Exception("Unknown engine type.");
            }
        }

        public static int ExecuteEventHook(EventHook eventHook, object eventSender, object eventArgs) {
            var pyrvtCmdRuntime =
                new PyRevitScriptRuntime(
                    cmdData: null,
                    elements: new ElementSet(),
                    scriptSource: eventHook.Script,
                    configScriptSource: eventHook.Script,
                    syspaths: eventHook.SearchPaths,
                    arguments: new string[] { },
                    helpSource: "",
                    cmdName: "",
                    cmdBundle: "",
                    cmdExtension: eventHook.ExtensionName,
                    cmdUniqueName: eventHook.UniqueId,
                    needsCleanEngine: false,
                    needsFullFrameEngine: false,
                    refreshEngine: false,
                    forcedDebugMode: false,
                    configScriptMode: false,
                    executedFromUI: false
                    );

            if (eventArgs != null)
                pyrvtCmdRuntime.SetBuiltInVariables(new Dictionary<string, object> {
                    { "__eventargs__", eventArgs }
                });


            // detemine sender type
            if (eventSender.GetType() == typeof(UIControlledApplication))
                pyrvtCmdRuntime.UIControlledApp = (UIControlledApplication)eventSender;
            else if (eventSender.GetType() == typeof(UIApplication))
                pyrvtCmdRuntime.UIApp = (UIApplication)eventSender;
            else if (eventSender.GetType() == typeof(Application))
                pyrvtCmdRuntime.App = (Application)eventSender;

            return ExecuteScript(ref pyrvtCmdRuntime);
        }

        /// Run the script using IronPython Engine
        private static int ExecuteIronPythonScript(ref PyRevitScriptRuntime pyrvtCmd) {
            // 1: ----------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            var engineMgr = new EngineManager();
            var engine = engineMgr.GetEngine(ref pyrvtCmd);

            // 2: ----------------------------------------------------------------------------------------------------
            // Setup the command scope in this engine with proper builtin and scope parameters
            var scope = engine.CreateScope();

            // 3: ----------------------------------------------------------------------------------------------------
            // Create the script from source file
            var script = engine.CreateScriptSourceFromFile(
                    pyrvtCmd.ScriptSourceFile,
                    System.Text.Encoding.UTF8,
                    SourceCodeKind.File
                );

            // 4: ----------------------------------------------------------------------------------------------------
            // Setting up error reporter and compile the script
            // setting module to be the main module so __name__ == __main__ is True
            var compiler_options = (PythonCompilerOptions)engine.GetCompilerOptions(scope);
            compiler_options.ModuleName = "__main__";
            compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;

            var errors = new IronPythonErrorReporter();
            var command = script.Compile(compiler_options, errors);

            // Process compile errors if any
            if (command == null) {
                // compilation failed, print errors and return
                pyrvtCmd.OutputStream.WriteError(
                    string.Join("\n", ExternalConfig.ipyerrtitle, string.Join("\n", errors.Errors.ToArray()))
                    );
                return ExecutionErrorCodes.CompileException;
            }

            // 6: ----------------------------------------------------------------------------------------------------
            // Finally let's execute
            try {
                command.Execute(scope);
                return ExecutionErrorCodes.Succeeded;
            }
            catch (SystemExitException) {
                // ok, so the system exited. That was bound to happen...
                return ExecutionErrorCodes.SysExited;
            }
            catch (Exception exception) {
                // show (power) user everything!
                string _dotnet_err_message = exception.ToString();
                string _ipy_err_messages = engine.GetService<ExceptionOperations>().FormatException(exception);

                // Print all errors to stdout and return cancelled to Revit.
                // This is to avoid getting window prompts from Revit.
                // Those pop ups are small and errors are hard to read.
                _ipy_err_messages = _ipy_err_messages.Replace("\r\n", "\n");
                pyrvtCmd.IronLanguageTraceBack = _ipy_err_messages;

                _dotnet_err_message = _dotnet_err_message.Replace("\r\n", "\n");
                pyrvtCmd.ClrTraceBack = _dotnet_err_message;

                _ipy_err_messages = string.Join("\n", ExternalConfig.ipyerrtitle, _ipy_err_messages);
                _dotnet_err_message = string.Join("\n", ExternalConfig.dotneterrtitle, _dotnet_err_message);

                pyrvtCmd.OutputStream.WriteError(_ipy_err_messages + "\n\n" + _dotnet_err_message);
                return ExecutionErrorCodes.ExecutionException;
            }
            finally {
                // clean the scope unless the script is requesting clean engine
                // this is a temporary convention to allow users to keep global references in the scope
                if (!pyrvtCmd.NeedsCleanEngine)
                    CleanupScope(engine, scope);

                engineMgr.CleanupEngine(engine);
            }
        }

        /// Run the script using CPython Engine
        private static int ExecuteCPythonScript(ref PyRevitScriptRuntime pyrvtCmd) {
            using (Py.GIL()) {
                // initialize
                if (!PythonEngine.IsInitialized)
                    PythonEngine.Initialize();

                // set output stream
                dynamic sys = PythonEngine.ImportModule("sys");
                sys.stdout = pyrvtCmd.OutputStream;

                // set uiapplication
                sys.host = pyrvtCmd.UIApp;

                // run
                try {
                    var scriptContents = File.ReadAllText(pyrvtCmd.ScriptSourceFile);
                    PythonEngine.Exec(scriptContents);
                    return ExecutionErrorCodes.Succeeded;
                }
                catch (Exception cpyex) {
                    string _cpy_err_message = cpyex.Message;
                    // Print all errors to stdout and return cancelled to Revit.
                    // This is to avoid getting window prompts from Revit.
                    // Those pop ups are small and errors are hard to read.
                    _cpy_err_message = _cpy_err_message.Replace("\r\n", "\n");
                    pyrvtCmd.CpythonTraceBack = _cpy_err_message;

                    pyrvtCmd.OutputStream.WriteError(_cpy_err_message);
                    return ExecutionErrorCodes.ExecutionException;
                }
                finally {
                    // shutdown halts and breaks Revit
                    // let's not do that!
                    // PythonEngine.Shutdown();
                }
            }
        }

        /// Run the script using C# script engine
        private static int ExecuteCSharpScript(ref PyRevitScriptRuntime pyrvtCmd) {
            return CompileAndRun(ref pyrvtCmd);
        }

        /// Run the script by directly invoking the IExternalCommand type from given dll
        private static int ExecuteInvokableDLL(ref PyRevitScriptRuntime pyrvtCmd) {
            try {
                if (pyrvtCmd.ConfigScriptSourceFile != null || pyrvtCmd.ConfigScriptSourceFile != string.Empty) {
                    // load the binary data from the DLL
                    // Direct invoke commands use the config script source file to point
                    // to the target dll assembly location
                    string assmFile = pyrvtCmd.ConfigScriptSourceFile;
                    string className = null;
                    if (pyrvtCmd.ConfigScriptSourceFile.Contains("::")) {
                        var parts = pyrvtCmd.ConfigScriptSourceFile.Split(
                            new string[] { "::" },
                            StringSplitOptions.RemoveEmptyEntries
                            );
                        assmFile = parts[0];
                        className = parts[1];
                    }

                    byte[] assmBin = File.ReadAllBytes(assmFile);
                    Assembly assmObj = Assembly.Load(assmBin);

                    return ExecuteExternalCommand(assmObj, className, ref pyrvtCmd);
                }
                else {
                    TaskDialog.Show("pyRevit", "Target assembly is not set correctly and can not be loaded.");
                    return ExecutionErrorCodes.ExternalCommandNotImplementedException;
                }
            }
            catch (Exception invokeEx) {
                TaskDialog.Show("pyRevit", invokeEx.Message);
                return ExecutionErrorCodes.ExecutionException;
            }
            finally {
                // whatever
            }
        }

        /// Run the script using visualbasic script engine
        private static int ExecuteVisualBasicScript(ref PyRevitScriptRuntime pyrvtCmd) {
            return CompileAndRun(ref pyrvtCmd);
        }

        /// Run the script using ruby script engine
        private static int ExecuteRubyScript(ref PyRevitScriptRuntime pyrvtCmd) {
            // TODO
            TaskDialog.Show("pyRevit", "Ruby-Script Execution Engine Not Yet Implemented.");
            return ExecutionErrorCodes.EngineNotImplementedException;
            //// https://github.com/hakonhc/RevitRubyShell/blob/master/RevitRubyShell/RevitRubyShellApplication.cs
            //// 1: ----------------------------------------------------------------------------------------------------
            //// start ruby interpreter
            //var engine = Ruby.CreateEngine();
            //var scope = engine.CreateScope();

            //// 2: ----------------------------------------------------------------------------------------------------
            //// Finally let's execute
            //try {
            //    // Run the code
            //    engine.ExecuteFile(pyrvtCmd.ScriptSourceFile, scope);
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
            //    _ruby_err_messages = _ruby_err_messages.Replace("\r\n", "\n");
            //    pyrvtCmd.IronLanguageTraceBack = _ruby_err_messages;

            //    _dotnet_err_message = _dotnet_err_message.Replace("\r\n", "\n");
            //    pyrvtCmd.ClrTraceBack = _dotnet_err_message;

            //    _ruby_err_messages = string.Join("\n", ExternalConfig.irubyerrtitle, _ruby_err_messages);
            //    _dotnet_err_message = string.Join("\n", ExternalConfig.dotneterrtitle, _dotnet_err_message);

            //    pyrvtCmd.OutputStream.WriteError(_ruby_err_messages + "\n\n" + _dotnet_err_message);
            //    return ExecutionErrorCodes.ExecutionException;
            //}
            //finally {
            //    // whatever
            //}
        }

        /// Run the script using DynamoBIM
        private static int ExecuteDynamoDefinition(ref PyRevitScriptRuntime pyrvtCmd) {
            var journalData = new Dictionary<string, string>() {
                // Specifies the path to the Dynamo workspace to execute.
                { "dynPath", pyrvtCmd.ScriptSourceFile },

                // Specifies whether the Dynamo UI should be visible (set to false - Dynamo will run headless).
                { "dynShowUI", pyrvtCmd.DebugMode.ToString() },

                // If the journal file specifies automation mode
                // Dynamo will run on the main thread without the idle loop.
                { "dynAutomation",  "True" },

                // The journal file can specify if the Dynamo workspace opened
                //{ "dynForceManualRun",  "True" }

                // The journal file can specify if the Dynamo workspace opened from DynPathKey will be executed or not. 
                // If we are in automation mode the workspace will be executed regardless of this key.
                { "dynPathExecute",  "True" },

                // The journal file can specify if the existing UIless RevitDynamoModel
                // needs to be shutdown before performing any action.
                // per comments on https://github.com/eirannejad/pyRevit/issues/570
                // Setting this to True slows down Dynamo by a factor of 3
                { "dynModelShutDown",  "True" },

                // The journal file can specify the values of Dynamo nodes.
                //{ "dynModelNodesInfo",  "" }
                };

            //return new DynamoRevit().ExecuteCommand(new DynamoRevitCommandData() {
            //    JournalData = journalData,
            //    Application = commandData.Application
            //});

            try {
                // find the DynamoRevitApp from DynamoRevitDS.dll
                // this should be already loaded since Dynamo loads before pyRevit
                ObjectHandle dynRevitAppObjHandle =
                    Activator.CreateInstance("DynamoRevitDS", "Dynamo.Applications.DynamoRevitApp");
                object dynRevitApp = dynRevitAppObjHandle.Unwrap();
                MethodInfo execDynamo = dynRevitApp.GetType().GetMethod("ExecuteDynamoCommand");

                // run the script
                execDynamo.Invoke(dynRevitApp, new object[] { journalData, pyrvtCmd.UIApp });
                return ExecutionErrorCodes.Succeeded;
            }
            catch (FileNotFoundException) {
                // if failed in finding DynamoRevitDS.dll, assume no dynamo
                TaskDialog.Show("pyRevit",
                    "Can not find dynamo installation or determine which Dynamo version to Run.\n\n" +
                    "Run Dynamo once to select the active version.");
                return ExecutionErrorCodes.ExecutionException;
            }
        }

        /// Run the script using Grasshopper
        private static int ExecuteGrasshopperDocument(ref PyRevitScriptRuntime pyrvtCmd) {
            // TODO
            TaskDialog.Show("pyRevit", "Grasshopper Execution Engine Not Yet Implemented.");
            return ExecutionErrorCodes.EngineNotImplementedException;
        }

        // utility methods -------------------------------------------------------------------------------------------
        // iron python
        private static void CleanupScope(ScriptEngine engine, ScriptScope scope) {
            var script = engine.CreateScriptSourceFromString("for __deref in dir():\n" +
                                                             "    if not __deref.startswith('__'):\n" +
                                                             "        del globals()[__deref]");
            script.Compile();
            script.Execute(scope);
        }

        // csharp, vb.net script
        private static IEnumerable<Type> GetTypesSafely(Assembly assembly) {
            try {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException ex) {
                return ex.Types.Where(x => x != null);
            }
        }

        private static int CompileAndRun(ref PyRevitScriptRuntime pyrvtCmd) {
            // https://stackoverflow.com/a/3188953

            // read the script
            var scriptContents = File.ReadAllText(pyrvtCmd.ScriptSourceFile);

            // read the referenced dlls from env vars
            // pyrevit sets this when loading
            string[] refFiles;
            var envDic = new EnvDictionary();
            if (envDic.ReferencedAssemblies.Count() == 0) {
                var refs = AppDomain.CurrentDomain.GetAssemblies();
                refFiles = refs.Where(a => !a.IsDynamic).Select(a => a.Location).ToArray();
            }
            else {
                refFiles = envDic.ReferencedAssemblies;
            }

            // create compiler parameters
            var compileParams = new CompilerParameters(refFiles);
            // TODO: add DEFINE for revit version
            compileParams.CompilerOptions = string.Format("/optimize -define:REVIT{0}", pyrvtCmd.App.VersionNumber);
            compileParams.GenerateInMemory = true;
            compileParams.GenerateExecutable = false;

            // determine which code provider to use
            CodeDomProvider compiler;
            var compConfig = new Dictionary<string, string>() { { "CompilerVersion", "v4.0" } };
            switch (pyrvtCmd.EngineType) {
                case EngineType.CSharp:
                    compiler = new CSharpCodeProvider(compConfig);
                    break;
                case EngineType.VisualBasic:
                    compiler = new VBCodeProvider(compConfig);
                    break;
                default:
                    throw new Exception("Specified language does not have a compiler.");
            }

            try {
                // compile code first
                var res = compiler.CompileAssemblyFromSource(
                    options: compileParams,
                    sources: new string[] { scriptContents }
                );

                // now run
                return ExecuteExternalCommand(res.CompiledAssembly, null, ref pyrvtCmd);
            }
            catch (Exception runEx) {
                TaskDialog.Show("pyRevit", runEx.Message);
                return ExecutionErrorCodes.ExecutionException;
            }
            finally {
                // whatever
            }

        }

        private static int ExecuteExternalCommand(Assembly assmObj, string className, ref PyRevitScriptRuntime pyrvtCmd) {
            foreach (Type assmType in GetTypesSafely(assmObj)) {
                if (assmType.IsClass) {
                    // find the appropriate type and execute
                    if (className != null) {
                        if (assmType.Name == className)
                            return ExecuteExternalCommandType(assmType, ref pyrvtCmd);
                        else
                            continue;
                    }
                    else if (assmType.GetInterfaces().Contains(typeof(IExternalCommand)))
                        return ExecuteExternalCommandType(assmType, ref pyrvtCmd);
                }
            }

            if (className != null)
                TaskDialog.Show("pyRevit",
                    string.Format("Can not find type \"{0}\" in assembly \"{1}\"", className, assmObj.Location));
            else
                TaskDialog.Show("pyRevit",
                    string.Format("Can not find any type implementing IExternalCommand in assembly \"{1}\"",
                                  className, assmObj.Location));

            return ExecutionErrorCodes.ExternalCommandNotImplementedException;
        }

        private static int ExecuteExternalCommandType(Type extCommandType, ref PyRevitScriptRuntime pyrvtCmd) {
            // execute
            object extCommandInstance = Activator.CreateInstance(extCommandType);
            string commandMessage = string.Empty;
            extCommandType.InvokeMember(
                "Execute",
                BindingFlags.Default | BindingFlags.InvokeMethod,
                null,
                extCommandInstance,
                new object[] {
                    pyrvtCmd.CommandData,
                    commandMessage,
                    pyrvtCmd.SelectedElements}
                );
            return ExecutionErrorCodes.Succeeded;
        }

        // dynamo
        // NOTE: Dyanmo uses XML in older file versions and JSON in newer versions. This needs to support both if ever implemented
        private static bool DetermineShowDynamoGUI() {
            return false;
            //    bool res = false;
            //    var xdoc = new XmlDocument();
            //    try {
            //        xdoc.Load(baked_scriptSource);
            //        XmlNodeList boolnode_list = xdoc.GetElementsByTagName("CoreNodeModels.Input.BoolSelector");
            //        foreach (XmlElement boolnode in boolnode_list) {
            //            string nnattr = boolnode.GetAttribute("nickname");
            //            if ("ShowDynamo" == nnattr) {
            //                Boolean.TryParse(boolnode.FirstChild.FirstChild.Value, out res);
            //                return res;
            //            }
            //        }
            //    }
            //    catch {
            //    }
            //    return res;
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
