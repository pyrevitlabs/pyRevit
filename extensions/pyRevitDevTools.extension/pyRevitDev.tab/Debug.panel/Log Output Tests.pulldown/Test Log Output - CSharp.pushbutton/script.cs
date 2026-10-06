using System;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace LogOutputTest {
    // Verifies buffered Console output reaches the output window before the
    // command returns. CLR command exceptions surface through a Revit dialog
    // rather than the output window, so this engine has no traceback check.
    public class LogOutputTest : IExternalCommand {
        public ExecParams execParams;

        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements) {
            const int lineCount = 12;

            // Rapid, un-delayed writes exercise the batched output path.
            for (int num = 1; num <= lineCount; num++)
                Console.WriteLine(string.Format("flush-test line {0} of {1}", num, lineCount));

            Console.WriteLine(string.Format(
                "PASS if lines 1..{0} above are all visible.", lineCount));

            return Result.Succeeded;
        }
    }
}
