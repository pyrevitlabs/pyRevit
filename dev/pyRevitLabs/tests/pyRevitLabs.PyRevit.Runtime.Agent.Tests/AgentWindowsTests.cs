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

        private static IntPtr CreateVisibleWindow(string title) {
            var window = CreateWindowEx(0, "STATIC", title, WsPopup | WsVisible, 0, 0, 100, 100, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero);
            Assert.NotEqual(IntPtr.Zero, window);
            return window;
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
