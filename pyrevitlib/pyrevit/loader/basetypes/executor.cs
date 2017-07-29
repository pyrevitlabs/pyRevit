using System;
using System.IO;
using System.Text;
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
        private readonly UIApplication _revit;

        public ScriptExecutor(ExternalCommandData commandData)
        {
            _revit = commandData.Application;
        }


        /// Run the script and print the output to a new output window.
        public int ExecuteScript(PyRevitCommand pyrvtCmd)
        {
            // 1: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Stating a new output window
            var scriptOutput = new ScriptOutput();
            var outputStream = new ScriptOutputStream(scriptOutput);
            var hndl = scriptOutput.Handle;             // Forces creation of handle before showing the window
            scriptOutput.Text = pyrvtCmd.CommandName;                // Set output window title to command name
            scriptOutput.OutputId = pyrvtCmd.CommandUniqueId;        // Set window identity to the command unique identifier

            // 2: ---------------------------------------------------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            var engineMgr = new EngineManager(_revit);
            var engine = engineMgr.GetEngine();
            // Process search paths provided to executor
            // syspaths variable is a string of paths separated by ';'. Split syspath and update the search paths
            engine.SetSearchPaths(pyrvtCmd.ModuleSearchPaths);
            // Setup IO streams
            engine.Runtime.IO.SetOutput(outputStream, Encoding.UTF8);
            engine.Runtime.IO.SetErrorOutput(outputStream, Encoding.UTF8);

            // 3: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Setup the command scope in this engine with proper builtin and scope parameters
            var scope = CreateCommandScope(engine, scriptOutput, pyrvtCmd);

            // 4: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Create the script from source file
            var script = engine.CreateScriptSourceFromFile(pyrvtCmd.ScriptSourceFile, Encoding.UTF8, SourceCodeKind.Statements);

            // 5: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Setting up error reporter and compile the script
            // setting module to be the main module so __name__ == __main__ is True
            var compiler_options = (PythonCompilerOptions)engine.GetCompilerOptions(scope);
            compiler_options.ModuleName = "__main__";
            compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;

            var errors = new ErrorReporter();
            var command = script.Compile(compiler_options, errors);

            // Process compile errors if any
            if (command == null) {
                // compilation failed, print errors and return
                outputStream.WriteError(string.Join("\n", ExternalConfig.ipyerrtitle, string.Join("\n", errors.Errors.ToArray())));
                return ExecutionErrorCodes.CompileException;
            }

            // 6: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Finally let's execute
            try
            {
                script.Execute(scope);
                return ExecutionErrorCodes.Succeeded;
            }
            catch (SystemExitException)
            {
                // ok, so the system exited. That was bound to happen...
                return ExecutionErrorCodes.SysExited;
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
                return ExecutionErrorCodes.ExecutionException;
            }
        }


        public ScriptScope CreateCommandScope(ScriptEngine engine, ScriptOutput outputWindow, PyRevitCommand pyrvtCmd)
        {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);

            // Add host application handle to the builtin to be globally visible everywhere
            builtin.SetVariable("__revit__", _revit);

            // add engine to builtins
            builtin.SetVariable("__ipyengine__", engine);

            // Add this script executor to the the builtin to be globally visible everywhere
            // This support pyrevit functionality to ask information about the current executing command
            builtin.SetVariable("__externalcommand__", pyrvtCmd);


            // SCOPE --------------------------------------------------------------------------------------------------
            // Get script scope to add custom variables
            var scope = IronPython.Hosting.Python.CreateModule(engine, pyrvtCmd.CommandUniqueId);

            // Adding data provided by IExternalCommand.Execute
            scope.SetVariable("__commanddata__", pyrvtCmd.CommandData);
            scope.SetVariable("__elements__", pyrvtCmd.SelectedElements);

            // Add command info to builtins
            scope.SetVariable("__file__", pyrvtCmd.ScriptSourceFile);
            scope.SetVariable("__commandpath__", Path.GetDirectoryName(pyrvtCmd.OriginalScriptSourceFile));
            scope.SetVariable("__alternatecommandpath__", Path.GetDirectoryName(pyrvtCmd.AlternateScriptSourceFile));
            scope.SetVariable("__commandname__", pyrvtCmd.CommandName);
            scope.SetVariable("__commandbundle__", pyrvtCmd.CommandBundle);
            scope.SetVariable("__commandextension__", pyrvtCmd.CommandExtension);
            scope.SetVariable("__commanduniqueid__", pyrvtCmd.CommandUniqueId);
            scope.SetVariable("__forceddebugmode__", pyrvtCmd.DebugMode);
            scope.SetVariable("__shiftclick__", pyrvtCmd.AlternateMode);
            scope.SetVariable("__result__", pyrvtCmd.GetResultsDictionary());

            // Adding output window handle
            scope.SetVariable("__window__", outputWindow);

            return scope;
        }

    }


    public class ErrorReporter : ErrorListener
    {
        public List<String> Errors = new List<string>();

        public override void ErrorReported(ScriptSource source, string message,
                                           SourceSpan span, int errorCode, Severity severity)
        {
            Errors.Add(string.Format("{0} (line {1})", message, span.Start.Line));
        }

        public int Count
        {
            get { return Errors.Count; }
        }
    }

}
