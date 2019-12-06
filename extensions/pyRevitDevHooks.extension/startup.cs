using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using PyRevitLabs.PyRevit.Runtime;
using pyRevitLabs.NLog;

using HeyRed.MarkdownSharp;

namespace ExtensionCSScript
{
   public class ExtensionCSScript : IExternalCommand
   {
      public ExecParams execParams;

      private Logger logger = LogManager.GetCurrentClassLogger();

      public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
      {
         logger.Info("Logger works...");
         Console.WriteLine(execParams.ScriptPath); 
         Console.WriteLine(":thumbs_up:"); 
         return Result.Succeeded;
      }
   }
}