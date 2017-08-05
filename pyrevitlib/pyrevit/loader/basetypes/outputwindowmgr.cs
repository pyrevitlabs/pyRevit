using System;
using System.IO;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Collections.Generic;
using System.Windows.Forms;


namespace PyRevitBaseClasses
{
    public class OutputWindowManager
    {
        private readonly UIApplication _revit;

        public OutputWindowManager(UIApplication revit)
        {
            _revit = revit;
        }
    }
}
