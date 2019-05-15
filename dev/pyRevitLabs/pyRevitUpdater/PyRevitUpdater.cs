using System;
using System.Diagnostics;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitUpdater {
    public class PyRevitUpdaterCLI {
        static void Main(string[] args) {
            if (args.Length >= 1) {
                // grab clone from args
                var clonePath = args[0];

                // request update
                RunUpdate(clonePath);
            }
        }

        public static void RunUpdate(string clonePath) {
            try {
                // find target clone
                var clone = PyRevit.GetRegisteredClone(clonePath);

                // run update
                PyRevit.Update(clone);

                // write success message to system logs
                using (EventLog eventLog = new EventLog("Application")) {
                    eventLog.Source = "Application";
                    eventLog.WriteEntry(
                        string.Format("Successfully Updated Clone \"{0}\"", clone.Name),
                        EventLogEntryType.Information
                        );
                }
            }
            catch (Exception ex){
                // write error message to system logs
                using (EventLog eventLog = new EventLog("Application")) {
                    eventLog.Source = "pyRevit Updater";
                    eventLog.WriteEntry(
                        string.Format("Update Error: {0}", ex.Message),
                        EventLogEntryType.Error
                        );
                }
            }
        }

    }
}
