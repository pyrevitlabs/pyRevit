using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace MyTools {
   public class AutoJoinFunction : IExternalCommand {
      public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements) {

            var uiapp = revit.Application;
            var doc = uiapp.ActiveUIDocument.Document;
            var uidoc = uiapp.ActiveUIDocument;

            var allWalls = new FilteredElementCollector(doc)
                               .OfCategory(BuiltInCategory.OST_Walls)
                               .WhereElementIsNotElementType();
            var allColumns = new FilteredElementCollector(doc)
                                 .OfCategory(BuiltInCategory.OST_Columns)
                                 .WhereElementIsNotElementType();

            // collect the wall ids
            var columnIds = allColumns.ToElementIds();

            // place all your actions in a single transaction for easy undo
            var trans = new Transaction(doc, "AutoJoinFunction");
            trans.Start();

            foreach (Element wall in allWalls) {
                var wbb = wall.get_BoundingBox(doc.ActiveView);

                // see https://apidocs.co/apps/revit/2020/901f78a0-1f6c-217b-ea48-8b404324e88b.htm
                var bboxChecker = new FilteredElementCollector(doc, columnIds)
                                      .WherePasses(
                                           new BoundingBoxIntersectsFilter(
                                               new Outline(wbb.Min, wbb.Max)
                                           )
                                      );

                foreach (Element column in bboxChecker)
                    JoinGeometryUtils.JoinGeometry(doc, column, wall);
            }

            trans.Commit();
            return Result.Succeeded;
      }
   }
}