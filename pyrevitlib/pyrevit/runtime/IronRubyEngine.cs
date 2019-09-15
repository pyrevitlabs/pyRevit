using Autodesk.Revit.UI;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class IronRubyEngine : ScriptEngine {
        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            UseNewEngine = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            // TODO: ExecuteRubyScript
            TaskDialog.Show(PyRevitLabsConsts.ProductName, "Ruby-Script Execution Engine Not Yet Implemented.");
            return ScriptExecutorResultCodes.EngineNotImplementedException;
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
            //    _ruby_err_messages = _ruby_err_messages.NormalizeNewLine();
            //    pyrvtScript.IronLanguageTraceBack = _ruby_err_messages;

            //    _dotnet_err_message = _dotnet_err_message.NormalizeNewLine();
            //    pyrvtScript.TraceMessage = _dotnet_err_message;

            //    _ruby_err_messages = string.Join(Environment.NewLine, ExternalConfig.irubyerrtitle, _ruby_err_messages);
            //    _dotnet_err_message = string.Join(Environment.NewLine, ExternalConfig.dotneterrtitle, _dotnet_err_message);

            //    pyrvtScript.OutputStream.WriteError(_ruby_err_messages + "\n\n" + _dotnet_err_message);
            //    return ExecutionErrorCodes.ExecutionException;
            //}
            //finally {
            //    // whatever
            //}
        }
    }
}
