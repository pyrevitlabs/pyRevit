using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace HelloWorld
{
   [Autodesk.Revit.Attributes.Transaction(Autodesk.Revit.Attributes.TransactionMode.Manual)]
   public class Test2 : IExternalCommand
   {
      public const string __tooltip__ = "HelloWorld Testing tooltip";
      public const string __author__ = "{{author}}";
      public const string __helpurl__ = "{{docpath}}";

      public Autodesk.Revit.UI.Result Execute(ExternalCommandData revit,
         ref string message, ElementSet elements)
      {
         TaskDialog.Show("Revit", "Hello World!!!");
         return Autodesk.Revit.UI.Result.Succeeded;
      }
   }

   public class Test2CommandSelectionAvail : IExternalCommandAvailability
   {
       public Test2CommandSelectionAvail()
       {
       }

       public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories)
       {
           if (selectedCategories.IsEmpty) return false;
           return true;
       }
   }
}
