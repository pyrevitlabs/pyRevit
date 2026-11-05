using System;

using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Closes Revit dialogs shown while an agent request runs on the main thread, and records
    /// what each one said.
    /// </summary>
    /// <remarks>
    /// A modal dialog opened during a request blocks the main thread until someone answers it,
    /// so the agent's call hangs and every later request returns <c>revit_busy</c>. Dismissing
    /// the dialog and reporting its message turns that hang into a response the agent can act on.
    /// Invariant: <see cref="Dispose"/> always unsubscribes, so dialogs outside agent requests
    /// are never touched.
    /// </remarks>
    internal sealed class AgentDialogCapture : IDisposable {
        private const int MaxRecordedDialogs = 200;

        private readonly UIApplication uiApp;
        private bool armed;

        public AgentDialogCapture(UIApplication uiApp) {
            this.uiApp = uiApp;
            uiApp.DialogBoxShowing += OnDialogBoxShowing;
            armed = true;
        }

        public JArray Dialogs { get; } = new JArray();

        /// <summary>
        /// Stops closing dialogs, so a prompt the host itself shows stays visible.
        /// </summary>
        public void Disarm() {
            if (!armed)
                return;
            uiApp.DialogBoxShowing -= OnDialogBoxShowing;
            armed = false;
        }

        public void Dispose() {
            Disarm();
        }

        private void OnDialogBoxShowing(object sender, DialogBoxShowingEventArgs e) {
            var entry = new JObject { ["dialog_id"] = e.DialogId };
            if (e is TaskDialogShowingEventArgs taskDialog)
                entry["message"] = taskDialog.Message;
            else if (e is MessageBoxShowingEventArgs messageBox)
                entry["message"] = messageBox.Message;

            entry["dismissed"] = TryDismiss(e);
            if (Dialogs.Count < MaxRecordedDialogs)
                Dialogs.Add(entry);
        }

        private static bool TryDismiss(DialogBoxShowingEventArgs e) {
            foreach (var result in new[] { TaskDialogResult.Cancel, TaskDialogResult.Close, TaskDialogResult.Ok }) {
                try {
                    if (e.OverrideResult((int)result))
                        return true;
                }
                catch (Exception) {
                }
            }
            return false;
        }
    }
}
