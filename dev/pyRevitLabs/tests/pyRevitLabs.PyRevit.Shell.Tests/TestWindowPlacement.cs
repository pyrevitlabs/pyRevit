using System.Runtime.CompilerServices;
using PyRevitLabs.PyRevit.Forms.Testing;

namespace pyRevitLabs.PyRevit.Shell.Tests {
    /// <summary>Opens the Stop window and completion popups these tests create off-screen instead of on the developer's desktop.</summary>
    static class TestWindowPlacement {
        [ModuleInitializer]
        internal static void KeepWindowsOffscreen() {
            OffscreenWindows.Install();
        }
    }
}
