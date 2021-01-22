using System;
using System.Linq;
using System.Text;
using System.IO;
using IronPython.Runtime.Exceptions;
using IronPython.Compiler;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using System.Collections.Generic;
using System.Reflection;

namespace PyRevitLoader {
    // Executes a script
    public class ScriptExecutor {
        private bool _fullframe = false;
        private readonly UIApplication _revit = null;

        public ScriptExecutor() {
        }

        public ScriptExecutor(UIApplication uiApplication, bool fullFrame = false) {
            _revit = uiApplication;
            _fullframe = fullFrame;
        }

        public string Message { get; private set; } = null;

        public static string EngineVersion {
            get {
                var assmVersion = Assembly.GetAssembly(typeof(ScriptExecutor)).GetName().Version;
                return string.Format("{0}{1}{2}", assmVersion.Minor, assmVersion.Build, assmVersion.Revision);
            }
        }

        public Result ExecuteScript(string sourcePath,
                                    IEnumerable<string> sysPaths = null,
                                    string logFilePath = null,
                                    IDictionary <string, object> variables = null) {
            try {
                var engine = CreateEngine();
                var scope = SetupEnvironment(engine);

                // Add script directory address to sys search paths
                if (sysPaths != null) {
                    var path = engine.GetSearchPaths();
                    foreach (var sysPath in sysPaths)
                        path.Add(sysPath);

                    engine.SetSearchPaths(path);
                }


                // set globals
                scope.SetVariable("__file__", sourcePath);

                if (variables != null)
                    foreach(var keyPair in variables)
                        scope.SetVariable(keyPair.Key, keyPair.Value);

                //var script = engine.CreateScriptSourceFromString(source, SourceCodeKind.Statements);
                var script = engine.CreateScriptSourceFromFile(sourcePath, Encoding.UTF8, SourceCodeKind.Statements);

                // setting module to be the main module so __name__ == __main__ is True
                var compiler_options = (PythonCompilerOptions)engine.GetCompilerOptions(scope);
                compiler_options.ModuleName = "__main__";
                compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;

                // Setting up error reporter and compile the script
                var errors = new ErrorReporter();
                var command = script.Compile(compiler_options, errors);
                if (command == null) {
                    // compilation failed, print errors and return
                    Message =
                        string.Join("\r\n", "IronPython Traceback:", string.Join("\r\n", errors.Errors.ToArray()));
                    if (logFilePath != null)
                        File.WriteAllText(logFilePath, Message);

                    return Result.Cancelled;
                }


                try {
                    script.Execute(scope);
                    return Result.Succeeded;
                }
                catch (SystemExitException) {
                    // ok, so the system exited. That was bound to happen...
                    return Result.Succeeded;
                }
                catch (Exception exception) {
                    string _dotnet_err_message = exception.ToString();
                    string _ipy_err_messages = engine.GetService<ExceptionOperations>().FormatException(exception);

                    _ipy_err_messages =
                        string.Join("\n", "IronPython Traceback:", _ipy_err_messages.Replace("\r\n", "\n"));
                    _dotnet_err_message =
                        string.Join("\n", "Script Executor Traceback:", _dotnet_err_message.Replace("\r\n", "\n"));

                    Message = _ipy_err_messages + "\n\n" + _dotnet_err_message;

                    // execution failed, log errors and return
                    if (logFilePath != null)
                        File.WriteAllText(logFilePath, Message);

                    return Result.Failed;
                }
                finally {
                    engine.Runtime.Shutdown();
                    engine = null;
                }

            }
            catch (Exception ex) {
                Message = ex.ToString();
                return Result.Failed;
            }
        }

        public ScriptEngine CreateEngine() {
            var flags = new Dictionary<string, object>();

            // default flags
            flags["LightweightScopes"] = true;

            if (_fullframe) {
                flags["Frames"] = true;
                flags["FullFrames"] = true;
            }

            var engine = IronPython.Hosting.Python.CreateEngine(flags);

            return engine;
        }

        public void AddEmbeddedLib(ScriptEngine engine) {
            // use embedded python lib
            var asm = this.GetType().Assembly;
#if DEFAULTENGINE
            var resQuery = from name in asm.GetManifestResourceNames()
                           where name.ToLowerInvariant().EndsWith("python_default_lib.zip")
                           select name;
#else
            var resQuery = from name in asm.GetManifestResourceNames()
                           where name.ToLowerInvariant().EndsWith(string.Format("python_{0}_lib.zip", EngineVersion))
                           select name;
#endif
            var resName = resQuery.Single();
            var importer = new IronPython.Modules.ResourceMetaPathImporter(asm, resName);
            dynamic sys = IronPython.Hosting.Python.GetSysModule(engine);
            sys.meta_path.append(importer);
        }

        // Set up an IronPython environment
        public ScriptScope SetupEnvironment(ScriptEngine engine) {
            var scope = IronPython.Hosting.Python.CreateModule(engine, "__main__");

            SetupEnvironment(engine, scope);

            return scope;
        }

        public void SetupEnvironment(ScriptEngine engine, ScriptScope scope) {
            // add two special variables: __revit__ and __vars__ to be globally visible everywhere:            
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);
            builtin.SetVariable("__revit__", _revit);

            // add the search paths
            AddEmbeddedLib(engine);

            // reference RevitAPI and RevitAPIUI
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // also, allow access to the RPL internals
            engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);
        }
    }

    public class ErrorReporter : ErrorListener {
        public List<String> Errors = new List<string>();

        public override void ErrorReported(ScriptSource source, string message, SourceSpan span, int errorCode, Severity severity) {
            Errors.Add(string.Format("{0} (line {1})", message, span.Start.Line));
        }

        public int Count {
            get { return Errors.Count; }
        }
    }
}