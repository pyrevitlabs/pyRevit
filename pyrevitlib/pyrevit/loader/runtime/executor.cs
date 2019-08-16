using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.Remoting;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

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

using pyRevitLabs.PyRevit;

namespace PyRevitRuntime {
    public static class ExecutionResultCodes {
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
    }

    /// Executes a script
    public class ScriptExecutor {
        /// Run the script and print the output to a new output window.
        public static int ExecuteScript(ref ScriptRuntime pyrvtScript) {
            switch (pyrvtScript.EngineType) {
                case EngineType.IronPython:
                    return ExecuteIronPythonScript(ref pyrvtScript);
                case EngineType.CPython:
                    return ExecuteCPythonScript(ref pyrvtScript);
                case EngineType.CSharp:
                    return ExecuteCLRScript(ref pyrvtScript);
                case EngineType.Invoke:
                    return ExecuteInvokableDLL(ref pyrvtScript);
                case EngineType.VisualBasic:
                    return ExecuteCLRScript(ref pyrvtScript);
                case EngineType.IronRuby:
                    return ExecuteRubyScript(ref pyrvtScript);
                case EngineType.Dynamo:
                    return ExecuteDynamoDefinition(ref pyrvtScript);
                case EngineType.Grasshopper:
                    return ExecuteGrasshopperDocument(ref pyrvtScript);
                case EngineType.Content:
                    return ExecuteContentLoader(ref pyrvtScript);
                default:
                    // should not get here
                    throw new Exception("Unknown engine type.");
            }
        }

        /// Run the script using IronPython Engine
        private static int ExecuteIronPythonScript(ref ScriptRuntime pyrvtScript) {
            // 1: ----------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            var engineMgr = new IronPythonEngineManager();
            var engine = engineMgr.GetEngine(ref pyrvtScript);

            // 2: ----------------------------------------------------------------------------------------------------
            // Setup the command scope in this engine with proper builtin and scope parameters
            var scope = engine.CreateScope();

            // 3: ----------------------------------------------------------------------------------------------------
            // Create the script from source file
            var script = engine.CreateScriptSourceFromFile(
                    pyrvtScript.ScriptSourceFile,
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
                pyrvtScript.OutputStream.WriteError(
                    string.Join(Environment.NewLine,
                                ScriptOutputConfigs.ipyerrtitle,
                                string.Join(Environment.NewLine, errors.Errors.ToArray()))
                    );
                return ExecutionResultCodes.CompileException;
            }

            // 6: ----------------------------------------------------------------------------------------------------
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
                string _clr_err_message = exception.ToString();
                string _ipy_err_messages = engine.GetService<ExceptionOperations>().FormatException(exception);

                // Print all errors to stdout and return cancelled to Revit.
                // This is to avoid getting window prompts from Revit.
                // Those pop ups are small and errors are hard to read.
                _ipy_err_messages = _ipy_err_messages.Replace("\r\n", "\n");
                pyrvtScript.IronLanguageTraceBack = _ipy_err_messages;

                _clr_err_message = _clr_err_message.Replace("\r\n", "\n");
                pyrvtScript.CLRTraceBack = _clr_err_message;

                _ipy_err_messages = string.Join("\n", ScriptOutputConfigs.ipyerrtitle, _ipy_err_messages);
                _clr_err_message = string.Join("\n", ScriptOutputConfigs.clrerrtitle, _clr_err_message);

                pyrvtScript.OutputStream.WriteError(_ipy_err_messages + "\n\n" + _clr_err_message);
                return ExecutionResultCodes.ExecutionException;
            }
            finally {
                // clean the scope unless the script is requesting persistent engine
                if (!pyrvtScript.NeedsPersistentEngine) {
                    // cleaning removes all references to revit content that's been casualy stored in global-level
                    // variables and prohibit the GC from cleaning them up and releasing memory
                    var cleanupScript = engine.CreateScriptSourceFromString(
                        "for __deref in dir():\n" +
                        "    if not __deref.startswith('__'):\n" +
                        "        del globals()[__deref]");
                    cleanupScript.Compile();
                    cleanupScript.Execute(scope);

                    engineMgr.CleanupEngine(engine);
                }
            }
        }

        /// Run the script using CPython Engine
        private static int ExecuteCPythonScript(ref ScriptRuntime pyrvtScript) {
            using (Py.GIL()) {
                // initialize
                if (!PythonEngine.IsInitialized)
                    PythonEngine.Initialize();

                // set output stream
                // TODO: implement __builtins__ like ironpython
                dynamic sys = PythonEngine.ImportModule("sys");
                sys.stdout = pyrvtScript.OutputStream;

                // set uiapplication
                sys.host = pyrvtScript.UIApp;

                // run
                try {
                    var scriptContents = File.ReadAllText(pyrvtScript.ScriptSourceFile);
                    PythonEngine.Exec(scriptContents);
                    return ExecutionResultCodes.Succeeded;
                }
                catch (Exception cpyex) {
                    string _cpy_err_message = cpyex.Message;
                    // Print all errors to stdout and return cancelled to Revit.
                    // This is to avoid getting window prompts from Revit.
                    // Those pop ups are small and errors are hard to read.
                    _cpy_err_message = _cpy_err_message.Replace("\r\n", Environment.NewLine);
                    pyrvtScript.CpythonTraceBack = _cpy_err_message;

                    pyrvtScript.OutputStream.WriteError(_cpy_err_message);
                    return ExecutionResultCodes.ExecutionException;
                }
                finally {
                    // shutdown halts and breaks Revit
                    // let's not do that!
                    // PythonEngine.Shutdown();
                }
            }
        }

        /// Run the script using C# or VisualBasic script engine
        private static int ExecuteCLRScript(ref ScriptRuntime pyrvtScript) {
            // compile first
            Assembly scriptAssm = null;
            try {
                scriptAssm = CompileCLRScript(ref pyrvtScript);
            }
            catch (Exception compileEx) {
                string _clr_err_message = compileEx.ToString();
                _clr_err_message = _clr_err_message.Replace("\r\n", Environment.NewLine);
                pyrvtScript.CLRTraceBack = _clr_err_message;

                // TODO: change to script output for all script types
                if (pyrvtScript.InterfaceType == InterfaceType.ExternalCommand)
                    TaskDialog.Show(PyRevit.ProductName, pyrvtScript.CLRTraceBack);

                TaskDialog.Show(PyRevit.ProductName, pyrvtScript.CLRTraceBack);

                return ExecutionResultCodes.CompileException;
            }

            // scriptAssm must have value
            switch (pyrvtScript.InterfaceType) {
                // if is an external command
                case InterfaceType.ExternalCommand:
                    try {
                        var resultCode = ExecuteExternalCommand(scriptAssm, null, ref pyrvtScript);
                        if (resultCode == ExecutionResultCodes.ExternalInterfaceNotImplementedException)
                            TaskDialog.Show(PyRevit.ProductName,
                                string.Format(
                                    "Can not find any type implementing IExternalCommand in assembly \"{0}\"",
                                    scriptAssm.Location
                                    ));
                        return resultCode;
                    }
                    catch (Exception execEx) {
                        string _clr_err_message = execEx.ToString();
                        _clr_err_message = _clr_err_message.Replace("\r\n", Environment.NewLine);
                        pyrvtScript.CLRTraceBack = _clr_err_message;
                        // TODO: same outp
                        TaskDialog.Show(PyRevit.ProductName, _clr_err_message);

                        return ExecutionResultCodes.ExecutionException;
                    }

                // if is an event hook
                case InterfaceType.EventHandler:
                    try {
                        return ExecuteEventHandler(scriptAssm, ref pyrvtScript);
                    }
                    catch (Exception execEx) {
                        string _clr_err_message = execEx.ToString();
                        _clr_err_message = _clr_err_message.Replace("\r\n", Environment.NewLine);
                        pyrvtScript.CLRTraceBack = _clr_err_message;

                        TaskDialog.Show(PyRevit.ProductName, pyrvtScript.CLRTraceBack);
                        return ExecutionResultCodes.ExecutionException;
                    }

                default:
                    return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
            }
        }

        /// Run the script by directly invoking the IExternalCommand type from given dll
        private static int ExecuteInvokableDLL(ref ScriptRuntime pyrvtScript) {
            try {
                // first argument is the script name
                // script.py assmFile:className
                if (pyrvtScript.Arguments.Count == 2) {
                    // load the binary data from the DLL
                    // Direct invoke commands use the config script source file to point
                    // to the target dll assembly location
                    string argumentString = pyrvtScript.Arguments[1];
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
                    byte[] assmBin = File.ReadAllBytes(assmFile);
                    Assembly assmObj = Assembly.Load(assmBin);

                    var resultCode = ExecuteExternalCommand(assmObj, className, ref pyrvtScript);
                    if (resultCode == ExecutionResultCodes.ExternalInterfaceNotImplementedException)
                        TaskDialog.Show(PyRevit.ProductName,
                            string.Format(
                                "Can not find type \"{0}\" in assembly \"{1}\"",
                                className,
                                assmObj.Location
                                ));
                    return resultCode;
                }
                else {
                    TaskDialog.Show(PyRevit.ProductName, "Target assembly is not set correctly and can not be loaded.");
                    return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
                }
            }
            catch (Exception invokeEx) {
                TaskDialog.Show(PyRevit.ProductName, invokeEx.Message);
                return ExecutionResultCodes.ExecutionException;
            }
            finally {
                // whatever
            }
        }

        /// Run the script using ruby script engine
        private static int ExecuteRubyScript(ref ScriptRuntime pyrvtScript) {
            // TODO: ExecuteRubyScript
            TaskDialog.Show(PyRevit.ProductName, "Ruby-Script Execution Engine Not Yet Implemented.");
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
            //    _ruby_err_messages = _ruby_err_messages.Replace("\r\n", Environment.NewLine);
            //    pyrvtScript.IronLanguageTraceBack = _ruby_err_messages;

            //    _dotnet_err_message = _dotnet_err_message.Replace("\r\n", Environment.NewLine);
            //    pyrvtScript.ClrTraceBack = _dotnet_err_message;

            //    _ruby_err_messages = string.Join(Environment.NewLine, ExternalConfig.irubyerrtitle, _ruby_err_messages);
            //    _dotnet_err_message = string.Join(Environment.NewLine, ExternalConfig.dotneterrtitle, _dotnet_err_message);

            //    pyrvtScript.OutputStream.WriteError(_ruby_err_messages + "\n\n" + _dotnet_err_message);
            //    return ExecutionErrorCodes.ExecutionException;
            //}
            //finally {
            //    // whatever
            //}
        }

        /// Run the script using DynamoBIM
        private static int ExecuteDynamoDefinition(ref ScriptRuntime pyrvtScript) {
            var journalData = new Dictionary<string, string>() {
                // Specifies the path to the Dynamo workspace to execute.
                { "dynPath", pyrvtScript.ScriptSourceFile },

                // Specifies whether the Dynamo UI should be visible (set to false - Dynamo will run headless).
                { "dynShowUI", pyrvtScript.DebugMode.ToString() },

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
                execDynamo.Invoke(dynRevitApp, new object[] { journalData, pyrvtScript.UIApp });
                return ExecutionResultCodes.Succeeded;
            }
            catch (FileNotFoundException) {
                // if failed in finding DynamoRevitDS.dll, assume no dynamo
                TaskDialog.Show(PyRevit.ProductName,
                    "Can not find dynamo installation or determine which Dynamo version to Run.\n\n" +
                    "Run Dynamo once to select the active version.");
                return ExecutionResultCodes.ExecutionException;
            }
        }

        /// Run the script using Grasshopper
        private static int ExecuteGrasshopperDocument(ref ScriptRuntime pyrvtScript) {
            // TODO: ExecuteGrasshopperDocument
            TaskDialog.Show(PyRevit.ProductName, "Grasshopper Execution Engine Not Yet Implemented.");
            return ExecutionResultCodes.EngineNotImplementedException;
        }

        /// Run the content bundle and place in active document
        private static int ExecuteContentLoader(ref ScriptRuntime pyrvtScript) {
#if (REVIT2013 || REVIT2014)
            TaskDialog.Show(PyRevit.ProductName, NotSupportedFeatureException.NotSupportedMessage);
            return ExecutionResultCodes.NotSupportedFeatureException;
#else
            if (pyrvtScript.UIApp != null && pyrvtScript.UIApp.ActiveUIDocument != null) {
                string familySourceFile = pyrvtScript.ScriptSourceFile;
                UIDocument uidoc = pyrvtScript.UIApp.ActiveUIDocument;
                Document doc = uidoc.Document;

                // find or load family first
                Family contentFamily = null;

                // attempt to find previously loaded family
                Element existingFamily = null;
                string familyName = Path.GetFileNameWithoutExtension(familySourceFile);
                var currentFamilies = 
                    new FilteredElementCollector(doc).OfClass(typeof(Family)).Where(q => q.Name == familyName);
                if (currentFamilies.Count() > 0)
                    existingFamily = currentFamilies.First();

                if (existingFamily != null)
                    contentFamily = (Family)existingFamily;

                // if not found, attemt to load
                if (contentFamily == null) {
                    try {
                        var txn = new Transaction(doc, "Load pyRevit Content");
                        txn.Start();
                        doc.LoadFamily(
                            familySourceFile,
                            new ContentLoaderOptions(),
                            out contentFamily
                            );
                        txn.Commit();
                    }
                    catch (Exception loadEx) {
                        TaskDialog.Show(PyRevit.ProductName,
                            string.Format("Failed loading content.\n{0}\n{1}", loadEx.Message, loadEx.StackTrace));
                        return ExecutionResultCodes.FailedLoadingContent;
                    }
                }

                if (contentFamily == null) {
                    TaskDialog.Show(PyRevit.ProductName,
                        string.Format("Failed finding or loading bundle content at:\n{0}", familySourceFile));
                    return ExecutionResultCodes.FailedLoadingContent;
                }

                // now ask ui to place an instance
                ElementId firstSymbolId = contentFamily.GetFamilySymbolIds().First();
                if (firstSymbolId != null && firstSymbolId != ElementId.InvalidElementId) {
                    FamilySymbol firstSymbol = (FamilySymbol)doc.GetElement(firstSymbolId);
                    if (firstSymbol != null)
                        try {
                            var placeOps = new PromptForFamilyInstancePlacementOptions();
                            uidoc.PromptForFamilyInstancePlacement(firstSymbol, placeOps);
                            return ExecutionResultCodes.Succeeded;
                        }
                        catch (Autodesk.Revit.Exceptions.OperationCanceledException) {
                            // user cancelled placement
                            return ExecutionResultCodes.Succeeded;
                        }
                        catch (Exception promptEx) {
                            TaskDialog.Show(PyRevit.ProductName,
                                string.Format("Failed placing content.\n{0}\n{1}",
                                              promptEx.Message, promptEx.StackTrace));
                            return ExecutionResultCodes.FailedLoadingContent;
                        }
                }
            }

            TaskDialog.Show(PyRevit.ProductName, "Failed accessing Appication.");
            return ExecutionResultCodes.FailedLoadingContent;
#endif
        }

        // utility methods -------------------------------------------------------------------------------------------
        // clr scripts
        private static IEnumerable<Type> GetTypesSafely(Assembly assembly) {
            try {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException ex) {
                return ex.Types.Where(x => x != null);
            }
        }

        private static Assembly CompileCLRScript(ref ScriptRuntime pyrvtScript) {
            // https://stackoverflow.com/a/3188953
            // read the script
            var scriptContents = File.ReadAllText(pyrvtScript.ScriptSourceFile);

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
            compileParams.CompilerOptions = string.Format("/optimize /define:REVIT{0}", pyrvtScript.App.VersionNumber);
            compileParams.GenerateInMemory = true;
            compileParams.GenerateExecutable = false;
            compileParams.ReferencedAssemblies.Add(typeof(ScriptExecutor).Assembly.Location);

            // determine which code provider to use
            CodeDomProvider compiler;
            var compConfig = new Dictionary<string, string>() { { "CompilerVersion", "v4.0" } };
            switch (pyrvtScript.EngineType) {
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

            // now run
            return res.CompiledAssembly;
        }

        private static int ExecuteExternalCommand(Assembly assmObj, string className, ref ScriptRuntime pyrvtScript) {
            foreach (Type assmType in GetTypesSafely(assmObj)) {
                if (assmType.IsClass) {
                    // find the appropriate type and execute
                    if (className != null) {
                        if (assmType.Name == className)
                            return ExecuteExternalCommandType(assmType, ref pyrvtScript);
                        else
                            continue;
                    }
                    else if (assmType.GetInterfaces().Contains(typeof(IExternalCommand)))
                        return ExecuteExternalCommandType(assmType, ref pyrvtScript);
                }
            }

            return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
        }

        private static int ExecuteExternalCommandType(Type extCommandType, ref ScriptRuntime pyrvtScript) {
            // create instance
            object extCommandInstance = Activator.CreateInstance(extCommandType);

            // set properties if available
            // set script data
            foreach(var fieldInfo in extCommandType.GetFields()) {
                if (fieldInfo.FieldType == typeof(ScriptData))
                    fieldInfo.SetValue(
                        extCommandInstance,
                        new ScriptData {
                            ScriptPath = pyrvtScript.ScriptSourceFile,
                        });
            }

            // execute
            string commandMessage = string.Empty;
            extCommandType.InvokeMember(
                "Execute",
                BindingFlags.Default | BindingFlags.InvokeMethod,
                null,
                extCommandInstance,
                new object[] {
                pyrvtScript.CommandData,
                commandMessage,
                pyrvtScript.SelectedElements}
                );
            return ExecutionResultCodes.Succeeded;
        }

        private static int ExecuteEventHandler(Assembly assmObj, ref ScriptRuntime pyrvtScript) {
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
                                    pyrvtScript.EventSender,
                                    pyrvtScript.EventArgs
                                }
                            );
                        return ExecutionResultCodes.Succeeded;
                    }
                }

            return ExecutionResultCodes.ExternalInterfaceNotImplementedException;
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
