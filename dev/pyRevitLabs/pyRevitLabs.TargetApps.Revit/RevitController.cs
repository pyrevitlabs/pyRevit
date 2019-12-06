using System;
using System.Collections.Generic;
using System.Diagnostics;

using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public class RevitController {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static List<RevitProcess> ListRunningRevits() {
            var runningRevits = new List<RevitProcess>();
            foreach (Process ps in Process.GetProcesses()) {
                if (RevitProcess.IsRevitProcess(ps))
                    runningRevits.Add(new RevitProcess(ps));
            }
            return runningRevits;
        }

        public static List<RevitProcess> ListRunningRevits(Version revitVersion) {
            var runningRevits = new List<RevitProcess>();
            foreach (RevitProcess revit in ListRunningRevits()) {
                if (revit.RevitProduct.Version == revitVersion)
                    runningRevits.Add(revit);
            }
            return runningRevits;
        }

        public static List<RevitProcess> ListRunningRevits(int revitYear) {
            var runningRevits = new List<RevitProcess>();
            foreach (RevitProcess revit in ListRunningRevits()) {
                if (revit.RevitProduct.ProductYear == revitYear)
                    runningRevits.Add(revit);
            }
            return runningRevits;
        }

        public static void KillRunningRevits(Version revitVersion) {
            foreach (RevitProcess revit in ListRunningRevits(revitVersion))
                revit.Kill();
        }

        public static void KillRunningRevits(int revitYear) {
            foreach (RevitProcess revit in ListRunningRevits(revitYear))
                revit.Kill();
        }

        public static void KillAllRunningRevits() {
            foreach (RevitProcess revit in ListRunningRevits())
                revit.Kill();
        }
    }
}