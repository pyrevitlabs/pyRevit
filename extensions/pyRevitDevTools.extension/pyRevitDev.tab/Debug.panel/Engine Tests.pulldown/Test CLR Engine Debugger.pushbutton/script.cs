using System;
using System.Diagnostics;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using PyRevitLabs.PyRevit.Runtime;
using pyRevitLabs.NLog;

namespace HelloWorld {
    public class Test2: IExternalCommand {
        public ExecParams execParams;

        private Logger logger = LogManager.GetCurrentClassLogger();

        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements) {

            int first = 11;
            int second = 31;

            Debugger.Break();


            Debugger.Log(0, "", "Testing debugger...\n");
            Debugger.Log(0, "", $"{first + second}\n");

            return Result.Succeeded;
        }
    }
}