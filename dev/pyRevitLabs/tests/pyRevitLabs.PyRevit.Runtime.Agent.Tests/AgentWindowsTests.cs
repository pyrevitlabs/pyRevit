using System;
using System.Runtime.InteropServices;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Integration")]
    public sealed class AgentWindowsTests {
        private const uint WsVisible = 0x10000000;
        private const uint WsPopup = 0x80000000;

        [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern IntPtr CreateWindowEx(
            uint exStyle, string className, string windowName, uint style,
            int x, int y, int width, int height, IntPtr parent, IntPtr menu, IntPtr instance, IntPtr param);

        [DllImport("user32.dll")]
        private static extern bool EnableWindow(IntPtr window, bool enable);

        [DllImport("user32.dll")]
        private static extern bool DestroyWindow(IntPtr window);

        private const string NativeDialogClass = "#32770";

        private static IntPtr CreateVisibleWindow(string title, string className = "STATIC") {
            var window = CreateWindowEx(0, className, title, WsPopup | WsVisible, 0, 0, 100, 100, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
            Assert.NotEqual(IntPtr.Zero, window);
            return window;
        }

        /// <summary>
        /// The approval prompt and the floating agent panel share a title. Only the prompt is a
        /// native dialog, so it is listed as blocking Revit and the panel is not.
        /// </summary>
        [Fact]
        public void TheApprovalPromptIsListedAndTheFloatingPanelWithTheSameTitleIsNot() {
            var mainWindow = CreateVisibleWindow("Revit main");
            var panel = CreateVisibleWindow(AgentWindows.AgentPanelTitle);
            var prompt = CreateVisibleWindow(AgentWindows.AgentPanelTitle, NativeDialogClass);
            try {
                AgentWindows.RememberMainWindow(mainWindow);

                Assert.True(AgentWindows.IsDialog(prompt));
                Assert.False(AgentWindows.IsDialog(panel));
                var listed = Assert.Single(AgentWindows.OpenDialogs(), dialog => dialog.Contains(AgentWindows.AgentPanelTitle));
                Assert.Contains(NativeDialogClass, listed);
            }
            finally {
                AgentWindows.RememberMainWindow(IntPtr.Zero);
                DestroyWindow(prompt);
                DestroyWindow(panel);
                DestroyWindow(mainWindow);
            }
        }

        [Fact]
        public void DisabledMainWindowWithAnOwnerlessDialogCountsAsModalAndNamesTheDialog() {
            var mainWindow = CreateVisibleWindow("Revit main");
            var ownerlessDialog = CreateVisibleWindow("Ownerless dialog");
            try {
                AgentWindows.RememberMainWindow(mainWindow);
                EnableWindow(mainWindow, false);

                Assert.True(AgentWindows.IsModalDialogOpen());
                var dialogs = AgentWindows.OpenDialogs();
                Assert.Contains(dialogs, dialog => dialog.Contains("Ownerless dialog"));
                Assert.DoesNotContain(dialogs, dialog => dialog.Contains("Revit main"));
            }
            finally {
                AgentWindows.RememberMainWindow(IntPtr.Zero);
                DestroyWindow(ownerlessDialog);
                DestroyWindow(mainWindow);
            }
        }

        [Fact]
        public void EnabledMainWindowIsNotModal() {
            var mainWindow = CreateVisibleWindow("Revit main");
            try {
                AgentWindows.RememberMainWindow(mainWindow);

                Assert.False(AgentWindows.IsModalDialogOpen());
            }
            finally {
                AgentWindows.RememberMainWindow(IntPtr.Zero);
                DestroyWindow(mainWindow);
            }
        }
    }
}
