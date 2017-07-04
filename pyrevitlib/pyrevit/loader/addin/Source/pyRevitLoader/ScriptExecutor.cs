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

namespace PyRevitLoader
{
    // Executes a script
    public class ScriptExecutor
    {
        private string _message;
        private readonly UIApplication _revit;
        //private readonly UIControlledApplication _uiControlledApplication;

        public ScriptExecutor(UIApplication uiApplication) // UIControlledApplication uiControlledApplication)
        {
            _revit = uiApplication;
            //_uiControlledApplication = uiControlledApplication;

            // note, if this constructor is used, then this stuff is all null
            // (I'm just setting it here to be explete - this constructor is
            // only used for the startupscript)
            _message = null;

        }


        public string Message
        {
            get
            {
                return _message;
            }
        }

        public int ExecuteScript(string sourcePath)
        {
            try
            {
                var engine = CreateEngine();
                var scope = SetupEnvironment(engine);

                scope.SetVariable("__file__", sourcePath);

                var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);
                builtin.SetVariable("__window__", 0);

                //var script = engine.CreateScriptSourceFromString(source, SourceCodeKind.Statements);
                var script = engine.CreateScriptSourceFromFile(sourcePath, Encoding.UTF8, SourceCodeKind.Statements);

                // setting module to be the main module so __name__ == __main__ is True
                var compiler_options = (PythonCompilerOptions)engine.GetCompilerOptions(scope);
                compiler_options.ModuleName = "__main__";
                compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;

                // Setting up error reporter and compile the script
                var errors = new ErrorReporter();
                var command = script.Compile(compiler_options, errors);
                if (command == null)
                    return (int)Result.Cancelled;


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
                    _message = exception.ToString();
                    return (int)Result.Failed;
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


        // Set up an IronPython environment
        public ScriptScope SetupEnvironment(ScriptEngine engine)
        {
            var scope = IronPython.Hosting.Python.CreateModule(engine, "__main__");

            SetupEnvironment(engine, scope);

            return scope;
        }

        public void SetupEnvironment(ScriptEngine engine, ScriptScope scope)
        {
            // these variables refer to the signature of the IExternalCommand.Execute method
            scope.SetVariable("__message__", _message);
            scope.SetVariable("__result__", (int)Result.Succeeded);

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