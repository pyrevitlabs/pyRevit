using System;
using System.Collections.Generic;
using System.IO;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;
using System.Windows;
using System.Windows.Input;
using System.Windows.Controls;
using System.Windows.Media.Imaging;

using Dynamo.Applications;


namespace PyRevitBaseClasses {
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public abstract class PyRevitCommandDynamoBIM : IExternalCommand {
        public string baked_scriptSource = null;
        public bool baked_showui = false;

        public PyRevitCommandDynamoBIM(string scriptSource, int showui) {
            baked_scriptSource = scriptSource;
            baked_showui = Convert.ToBoolean(showui);
        }

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements) {

            // 1: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Processing modifier keys
            // Processing modifier keys

            bool ALT = Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt);
            bool SHIFT = Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift);
            bool CTRL = Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl);
            bool WIN = Keyboard.IsKeyDown(Key.LWin) || Keyboard.IsKeyDown(Key.RWin);

            // If Alt clicking on button, open the script in explorer and return.
            if (ALT) {
                // combine the arguments together
                // it doesn't matter if there is a space after ','
                string argument = "/select, \"" + baked_scriptSource + "\"";

                System.Diagnostics.Process.Start("explorer.exe", argument);
                return Result.Succeeded;
            }
            #endregion

            // 2: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Execute and return results
            var journalData = new Dictionary<string, string>() {
                { "dynPath", baked_scriptSource },
                { "dynShowUI", baked_showui.ToString() },
                { "dynAutomation",  "True" },
                { "dynPathExecute",  "True" },
                { "dynModelShutDown",  "False" }
                };

            return new DynamoRevit().ExecuteCommand(new DynamoRevitCommandData() {
                JournalData = journalData,
                Application = commandData.Application
            });
            #endregion
        }
    }
}
