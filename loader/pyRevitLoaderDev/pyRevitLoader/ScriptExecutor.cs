using System;
using System.IO;
using System.Reflection;
using System.Linq;
using System.Text;
using Autodesk.Revit;
using IronPython.Runtime.Exceptions;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Collections.Generic;

namespace PyRevitLoader
{
    /// <summary>
    /// Executes a script scripts
    /// </summary>
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

            // note, if this constructor is used, then this stuff is all null
            // (I'm just setting it here to be explete - this constructor is
            // only used for the startupscript)
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

        /// <summary>
        /// Run the script and print the output to a new output window.
        /// </summary>
        public int ExecuteScript(string source,
                                 string sourcePath, string syspaths,
                                 string cmdName, string cmdOptions,
                                 bool forcedDebugMode, bool altScriptMode)
        {
            try
            {
                var engine = CreateEngine();
                var scope = SetupEnvironment(engine);

                var scriptOutput = new ScriptOutput();
                var hndl = scriptOutput.Handle;         // Forces creation of handle before showing the window
                scriptOutput.Text = cmdName;
                //scriptOutput.Show();
                var outputStream = new ScriptOutputStream(scriptOutput, engine);

                //get the sys.path object and get ready to add more search paths
                //var path = engine.GetSearchPaths();

                // At least the main library path is added to sys.path
                var importLibPath = PyRevitLoaderApplication.GetImportLibraryPath();

                // if syspaths is empty use the baseSysPaths
                if (syspaths.Length == 0)
                    syspaths = importLibPath;
                // otherwise prepend the base paths
                else
                    syspaths = importLibPath + ';' + syspaths;

                //syspath is a string of paths separated by ';'
                //Split syspath and aupdate the search paths with new list
                engine.SetSearchPaths(syspaths.Split(';'));

                //scope.SetVariable("__window__", scriptOutput);
                scope.SetVariable("__file__", sourcePath);
                scope.SetVariable("__libpath__", importLibPath);

                // add __forceddebugmode__ to builtins
                var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);
                builtin.SetVariable("__forceddebugmode__", forcedDebugMode);
                builtin.SetVariable("__shiftclick__", altScriptMode);

                builtin.SetVariable("__window__", scriptOutput);

                // add command name to builtins
                builtin.SetVariable("__commandname__", cmdName);

                engine.Runtime.IO.SetOutput(outputStream, Encoding.UTF8);
                engine.Runtime.IO.SetErrorOutput(outputStream, Encoding.UTF8);
                engine.Runtime.IO.SetInput(outputStream, Encoding.UTF8);

                var script = engine.CreateScriptSourceFromString(source, SourceCodeKind.Statements);
                var errors = new ErrorReporter();
                var command = script.Compile(errors);
                if (command == null)
                {
                    // compilation failed
                    _message = string.Join("\n", errors.Errors);
                    return (int)Result.Failed;
                }


                try
                {
                    script.Execute(scope);

                    _message = (scope.GetVariable("__message__") ?? "").ToString();
                    return (int)(scope.GetVariable("__result__") ?? Result.Succeeded);
                }
                catch (SystemExitException)
                {
                    // ok, so the system exited. That was bound to happen...
                    return (int)Result.Succeeded;
                }
                catch (Exception exception)
                {
                    // show (power) user everything!
                    _message = exception.ToString();

                    // Print all errors to stdout and return cancelled to Revit.
                    // This is to avoid getting window prompts from revit. Those pop ups are small and errors are hard to read.
                    _message = string.Join("\r\n", new String('-', 100), _message, " ");
                    outputStream.Write(Encoding.ASCII.GetBytes(_message), 0, _message.Length);
                    _message = "";
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
            var engine = IronPython.Hosting.Python.CreateEngine(new Dictionary<string, object>() { { "Frames", true }, { "FullFrames", true } });
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


        /// <summary>
        /// Set up an IronPython environment - for interactive shell or for canned scripts
        /// </summary>
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
            AddEmbeddedLib(engine);

            // reference RevitAPI and RevitAPIUI
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // also, allow access to the RPL internals
            engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);

        }

        /// <summary>
        /// Be nasty and reach into the ScriptScope to get at its private '_scope' member,
        /// since the accessor 'ScriptScope.Scope' was defined 'internal'.
        /// </summary>
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
}