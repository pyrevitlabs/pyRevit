using System;
using System.IO;
using System.Reflection;
using System.Linq;
using System.Text;
using Autodesk.Revit;
using IronPython.Runtime.Exceptions;
using IronPython.Compiler;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Collections.Generic;

namespace PyRevitBaseClasses
{
    /// Executes a script
    public class ScriptExecutor
    {
        private readonly ExternalCommandData _commandData;
        private string _message;
        private readonly ElementSet _elements;
        private readonly UIApplication _revit;
        private readonly UIControlledApplication _uiControlledApplication;

        public ScriptExecutor(UIApplication uiApplication, UIControlledApplication uiControlledApplication)
        {
            _revit = uiApplication;
            _uiControlledApplication = uiControlledApplication;

            _commandData = null;
            _elements = null;
            _message = null;

        }

        public ScriptExecutor(ExternalCommandData commandData, string message, ElementSet elements)
        {
            _revit = commandData.Application;
            _commandData = commandData;
            _elements = elements;
            _message = message;

            _uiControlledApplication = null;
        }


        public string Message
        {
            get
            {
                return _message;
            }
        }


        /// Run the script and print the output to a new output window.
        public int ExecuteScript(string sourcePath, string syspaths, string cmdName,
                                 bool forcedDebugMode, bool altScriptMode)
        {
            try
            {
                // Setup engine and set __file__
                var engine = CreateEngine();
                var scope = SetupEnvironment(engine);

                // Get builtin scope to add custom variables
                var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);
                // add engine to builtins
                builtin.SetVariable("__ipyengine__", engine);
                // add command path to builtins
                builtin.SetVariable("__commandpath__", Path.GetDirectoryName(sourcePath));
                builtin.SetVariable("__commandname__", cmdName);                    // add command name to builtins
                builtin.SetVariable("__forceddebugmode__", forcedDebugMode);        // add forced debug mode to builtins
                builtin.SetVariable("__shiftclick__", altScriptMode);               // set to true of alt script mode

                // Add assembly's custom attributes
                builtin.SetVariable("__assmcustomattrs__", typeof(ScriptExecutor).Assembly.CustomAttributes);

                var scriptOutput = new ScriptOutput();  // New output window
                var hndl = scriptOutput.Handle;         // Forces creation of handle before showing the window
                scriptOutput.Text = cmdName;            // Set output window title to command name
                builtin.SetVariable("__window__", scriptOutput);

                // Create output stream
                var outputStream = new ScriptOutputStream(scriptOutput);

                // Process search paths provided to constructor
                // syspaths variable is a string of paths separated by ';'
                // Split syspath and update the search paths with new list
                engine.SetSearchPaths(syspaths.Split(';'));

                // Setup IO streams
                engine.Runtime.IO.SetOutput(outputStream, Encoding.UTF8);
                engine.Runtime.IO.SetErrorOutput(outputStream, Encoding.UTF8);
                engine.Runtime.IO.SetInput(outputStream, Encoding.UTF8);

                scope.SetVariable("__file__", sourcePath);

                var script = engine.CreateScriptSourceFromFile(sourcePath, Encoding.UTF8, SourceCodeKind.Statements);

                // setting module to be the main module so __name__ == __main__ is True
                var compiler_options = (PythonCompilerOptions)engine.GetCompilerOptions(scope);
                compiler_options.ModuleName = "__main__";
                compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;


                // Setting up error reporter and compile the script
                var errors = new ErrorReporter();
                var command = script.Compile(compiler_options, errors);

                // Process compile errors if any
                if (command == null)
                {
                    // compilation failed, print errors and return
                    outputStream.WriteError(string.Join("\n",
                                                        ExternalConfig.ipyerrtitle,
                                                        string.Join("\n", errors.Errors.ToArray())));
                    _message = "";
                    engine.Runtime.Shutdown();
                    return (int)Result.Cancelled;
                }


                // Finally let's execute
                try
                {
                    script.Execute(scope);

                    _message = (scope.GetVariable("__message__") ?? "").ToString();
                    engine.Runtime.Shutdown();
                    return (int)(scope.GetVariable("__result__") ?? Result.Succeeded);
                }
                catch (SystemExitException)
                {
                    // ok, so the system exited. That was bound to happen...
                    engine.Runtime.Shutdown();
                    return (int)Result.Succeeded;
                }
                catch (Exception exception)
                {
                    // show (power) user everything!
                    string _dotnet_err_message = exception.ToString();
                    string _ipy_err_messages = engine.GetService<ExceptionOperations>().FormatException(exception);

                    // Print all errors to stdout and return cancelled to Revit.
                    // This is to avoid getting window prompts from Revit.
                    // Those pop ups are small and errors are hard to read.
                    _ipy_err_messages = _ipy_err_messages.Replace("\r\n", "\n");
                    _dotnet_err_message = _dotnet_err_message.Replace("\r\n", "\n");
                    _ipy_err_messages = string.Join("\n", ExternalConfig.ipyerrtitle, _ipy_err_messages);
                    _dotnet_err_message = string.Join("\n", ExternalConfig.dotneterrtitle, _dotnet_err_message);

                    outputStream.WriteError(_ipy_err_messages + "\n\n" + _dotnet_err_message);
                    _message = "";
                    engine.Runtime.Shutdown();
                    return (int)Result.Cancelled;
                }

            }
            catch (Exception ex)
            {
                _message = ex.ToString();
                return (int)Result.Failed;
            }
        }

        private ScriptEngine CreateEngine()
        {
            var engine = IronPython.Hosting.Python.CreateEngine(new Dictionary<string, object>()
            {
                { "Frames", true }, { "FullFrames", true }, {"LightweightScopes", true} 
            });
            return engine;
        }

        private void AddEmbeddedLib(ScriptEngine engine)
        {
            // use embedded python lib
            var asm = this.GetType().Assembly;
            var resQuery = from name in asm.GetManifestResourceNames()
                           where name.ToLowerInvariant().EndsWith("python_27_lib.zip")
                           select name;
            var resName = resQuery.Single();
            var importer = new IronPython.Modules.ResourceMetaPathImporter(asm, resName);
            dynamic sys = IronPython.Hosting.Python.GetSysModule(engine);
            sys.meta_path.append(importer);
        }


        /// Set up an IronPython environment - for interactive shell or for canned scripts
        public ScriptScope SetupEnvironment(ScriptEngine engine)
        {
            var scope = IronPython.Hosting.Python.CreateModule(engine, "__main__");

            SetupEnvironment(engine, scope);

            return scope;
        }

        public void SetupEnvironment(ScriptEngine engine, ScriptScope scope)
        {
            // these variables refer to the signature of the IExternalCommand.Execute method
            scope.SetVariable("__commandData__", _commandData);
            scope.SetVariable("__message__", _message);
            scope.SetVariable("__elements__", _elements);
            scope.SetVariable("__result__", (int)Result.Succeeded);

            // add two special variables: __revit__ and __vars__ to be globally visible everywhere:
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);
            builtin.SetVariable("__revit__", _revit);

            // allow access to the UIControlledApplication in the startup script...
            if (_uiControlledApplication != null)
            {
                builtin.SetVariable("__uiControlledApplication__", _uiControlledApplication);
            }

            // add the search paths
            //AddEmbeddedLib(engine);

            // reference RevitAPI and RevitAPIUI
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // also, allow access to the RPL internals
            engine.Runtime.LoadAssembly(typeof(PyRevitBaseClasses.ScriptExecutor).Assembly);

        }

        /// Be nasty and reach into the ScriptScope to get at its private '_scope' member,
        /// since the accessor 'ScriptScope.Scope' was defined 'internal'.
        private Microsoft.Scripting.Runtime.Scope GetScope(ScriptScope scriptScope)
        {
            var field = scriptScope.GetType().GetField(
                "_scope",
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            return (Microsoft.Scripting.Runtime.Scope)field.GetValue(scriptScope);
        }
    }


    public class ErrorReporter : ErrorListener
    {
        public List<String> Errors = new List<string>();

        public override void ErrorReported(ScriptSource source, string message, SourceSpan span, int errorCode, Severity severity)
        {
            Errors.Add(string.Format("{0} (line {1})", message, span.Start.Line));
        }

        public int Count
        {
            get { return Errors.Count; }
        }
    }

    // Custom attribute to carry the pyrevit version that compiles this assembly
    [AttributeUsage(AttributeTargets.Assembly)]
    public class AssemblyPyRevitVersion : Attribute {
        string pyrevit_ver;
        public AssemblyPyRevitVersion() : this(string.Empty) {}
        public AssemblyPyRevitVersion(string txt) { pyrevit_ver = txt; }
    }
}
