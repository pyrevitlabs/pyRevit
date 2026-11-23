using System;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    /// <summary>Exercises the Revit-free taskbar flash request layout.</summary>
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentUser32FlashTests {
        [Fact]
        public void BuildFlashInfo_Start_FlashesTaskbarAndCaptionUntilForeground() {
            var window = new IntPtr(1234);

            var info = AgentUser32.BuildFlashInfo(window, false);

            Assert.Equal(IntPtr.Size == 8 ? 32u : 20u, info.Size);
            Assert.Equal(window, info.Window);
            Assert.Equal(3u | 12u, info.Flags);
            Assert.Equal(uint.MaxValue, info.Count);
            Assert.Equal(0u, info.TimeoutMilliseconds);
        }

        [Fact]
        public void BuildFlashInfo_Stop_ClearsTheFlash() {
            var window = new IntPtr(1234);

            var info = AgentUser32.BuildFlashInfo(window, true);

            Assert.Equal(window, info.Window);
            Assert.Equal(0u, info.Flags);
            Assert.Equal(0u, info.Count);
        }
    }
}
