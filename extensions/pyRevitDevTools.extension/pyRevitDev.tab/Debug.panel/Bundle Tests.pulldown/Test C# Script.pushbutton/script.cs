using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using PyRevitLabs.PyRevit.Runtime;

using HeyRed.MarkdownSharp;

namespace HelloWorld
{
   public class Test2 : IExternalCommand
   {
      public ExecParams execParams;

      public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
      {
         Console.WriteLine(execParams.ScriptPath); 

         TaskDialog.Show(execParams.CommandName, "Hello World from C#!!!");

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

         Console.WriteLine(":thumbs_up:"); 

         return Result.Succeeded;
      }
   }
}