using System;
using System.Collections.Generic;
using System.Diagnostics;

using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public class RevitController {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static List<RevitProcess> ListRunningRevits() {
            var runningRevits = new List<RevitProcess>();

            // lets handle exceptions just in case user can not read processes
            try {
                foreach (Process ps in Process.GetProcesses()) {
                    if (RevitProcess.IsRevitProcess(ps))
                        runningRevits.Add(new RevitProcess(ps));
                }
            }
            catch (Exception ex) {
                logger.Debug($"Error getting Revit processes. | {ex}");
            }

            return runningRevits;
        }

        public static List<RevitProcess> ListRunningRevits(Version revitVersion) {
            var runningRevits = new List<RevitProcess>();
            foreach (RevitProcess revit in ListRunningRevits()) {
                try {
                    if (revit.RevitProduct?.Version == revitVersion)
                        runningRevits.Add(revit);
                }
                catch (Exception ex) {
                    logger.Debug($"Error getting Revit process by Version: \"{revitVersion}\" | {ex}");
                }
            }
            return runningRevits;
        }

        public static List<RevitProcess> ListRunningRevits(int revitYear) {
            var runningRevits = new List<RevitProcess>();
            foreach (RevitProcess revit in ListRunningRevits()) {
                try {
                    if (revit.RevitProduct?.ProductYear == revitYear)
                        runningRevits.Add(revit);
                }
                catch (Exception ex) {
                    logger.Debug($"Error getting Revit process by Year: \"{revitYear}\" | {ex}");
                }
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