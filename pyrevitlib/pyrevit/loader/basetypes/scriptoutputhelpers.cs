using System;
using System.Collections.Generic;
using System.Windows;
using System.Web;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;


namespace PyRevitBaseClasses
{
    public class ScriptOutputHelpers
    {
        public static void ProcessUrl(UIApplication uiApp, string inputUrl)
        {
            var parsedQuery = HttpUtility.ParseQueryString(inputUrl.Split('?')[1]);

            var idList = new List<ElementId>();
            foreach(string strId in parsedQuery["element[]"].Split(','))
            {
                idList.Add(new ElementId(Convert.ToInt32(strId)));
            }

            SelectElements(uiApp, idList);
        }

        public static void SelectElements(UIApplication uiApp, List<ElementId> elementIds)
        {
            var activeDoc = uiApp.ActiveUIDocument;
            if (activeDoc != null)
            {
                activeDoc.Selection.SetElementIds(elementIds);
            }
        }
    }
}