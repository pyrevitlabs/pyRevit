using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using HeyRed.MarkdownSharp;

namespace HelloWorld
{
   [Autodesk.Revit.Attributes.Transaction(Autodesk.Revit.Attributes.TransactionMode.Manual)]
   public class Test2 : IExternalCommand
   {
      public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
      {
         TaskDialog.Show("Revit", "Hello World from C#!!!");

         // Create new markdown instance
         Markdown mark = new Markdown();
         // Run parser
         string text = mark.Transform("**Markdown**");
         TaskDialog.Show("Revit", "Referenced Module Loaded Successfully!");

         return Result.Succeeded;
      }
   }
}