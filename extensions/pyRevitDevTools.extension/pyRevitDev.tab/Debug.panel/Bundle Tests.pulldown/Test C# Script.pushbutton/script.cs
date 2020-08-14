using System;
using System.Diagnostics;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using PyRevitLabs.PyRevit.Runtime;
using pyRevitLabs.NLog;

using HeyRed.MarkdownSharp;

namespace HelloWorld {
    public class Test2: IExternalCommand {
        public ExecParams execParams;

        private Logger logger = LogManager.GetCurrentClassLogger();

        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements) {
            logger.Info("Logger works...");
            logger.Debug("Logger works...");
            Console.WriteLine(execParams.ScriptPath);

            Debugger.Break();

            TaskDialog.Show(execParams.CommandName, "Hello World from C#!");

            // test access to bundle path
            TaskDialog.Show(execParams.CommandName, execParams.ScriptPath);

            if (execParams.ConfigMode) {
                // Create new markdown instance
                Markdown mark = new Markdown();
                // Run parser
                string text = mark.Transform("**Markdown**");
                TaskDialog.Show(execParams.CommandName, "Referenced Module Loaded Successfully!");
            }

            if (execParams.DebugMode) {
                TaskDialog.Show(execParams.CommandName, "Command is in Debug Mode!");
            }

            Console.WriteLine(execParams.UIButton.ToString());
            Console.WriteLine($"New C# Features Work: {true}");
            Console.WriteLine(":thumbs_up:");

            var read = Console.ReadLine();
            Console.WriteLine($"echo: {read}");

            Debugger.Log(0, "", "Testing debugger...\n");

            return Result.Succeeded;
        }
    }
}