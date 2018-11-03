using System;
using System.Collections.Generic;
using Microsoft.Scripting;
using Microsoft.Scripting.Hosting;
using IronPython.Runtime.Exceptions;
using IronPython.Compiler;

namespace PyRevitBaseClasses
{
    /// Executes a script
    public class ScriptExecutor
    {
        public ScriptExecutor() {}


        /// Run the script and print the output to a new output window.
        public int ExecuteScript(ref PyRevitCommandRuntime pyrvtCmd)
        {
            // 1: ---------------------------------------------------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            var engineMgr = new EngineManager();
            var engine = engineMgr.GetEngine(ref pyrvtCmd);

            // 2: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Setup the command scope in this engine with proper builtin and scope parameters
            var scope = CreateScope(engine, ref pyrvtCmd);

            // 3: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Create the script from source file
            var script = engine.CreateScriptSourceFromFile(pyrvtCmd.ScriptSourceFile, System.Text.Encoding.UTF8, SourceCodeKind.File);

            // 4: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Setting up error reporter and compile the script
            // setting module to be the main module so __name__ == __main__ is True
            var compiler_options = (PythonCompilerOptions) engine.GetCompilerOptions(scope);
            compiler_options.ModuleName = "__main__";
            compiler_options.Module |= IronPython.Runtime.ModuleOptions.Initialize;

            var errors = new ErrorReporter();
            var command = script.Compile(compiler_options, errors);

            // Process compile errors if any
            if (command == null) {
                // compilation failed, print errors and return
                pyrvtCmd.OutputStream.WriteError(string.Join("\n", ExternalConfig.ipyerrtitle, string.Join("\n", errors.Errors.ToArray())));
                return ExecutionErrorCodes.CompileException;
            }

            // 6: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Finally let's execute
            try
            {
                command.Execute(scope);
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

                pyrvtCmd.OutputStream.WriteError(_ipy_err_messages + "\n\n" + _dotnet_err_message);
                return ExecutionErrorCodes.ExecutionException;
            }
            finally
            {
                // clean the scope unless the script is requesting clean engine
                // this is a temporary convention to allow users to keep global references in the scope
                if(!pyrvtCmd.NeedsCleanEngine)
                    CleanupScope(engine, scope);

                engineMgr.CleanupEngine(engine);
            }
        }


        public ScriptScope CreateScope(ScriptEngine engine, ref PyRevitCommandRuntime pyrvtCmd)
        {
            return engine.CreateScope();
        }


        public void CleanupScope(ScriptEngine engine, ScriptScope scope)
        {
            var script = engine.CreateScriptSourceFromString("for __deref in dir():\n" +
                                                             "    if not __deref.startswith('__'):\n" +
                                                             "        del globals()[__deref]");
            script.Compile();
            script.Execute(scope);
        }
    }

    public class ErrorReporter : ErrorListener
    {
        public List<string> Errors = new List<string>();

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
