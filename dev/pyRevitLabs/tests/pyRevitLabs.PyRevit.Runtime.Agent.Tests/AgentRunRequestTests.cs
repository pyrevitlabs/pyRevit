using System;
using System.Diagnostics;
using System.IO;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentRunRequestTests {
        private static JObject Run(string title = null, string workspace = null) {
            var parameters = new JObject { ["script"] = "pass", ["engine"] = "ironpython" };
            if (title != null)
                parameters["title"] = title;
            if (workspace != null)
                parameters["workspace"] = workspace;
            return parameters;
        }

        [Theory]
        [InlineData(@"\\server\share")]
        [InlineData("//server/share")]
        [InlineData(@"\/server/share")]
        [InlineData(@"/\server\share")]
        [InlineData(@"\\?\C:\Windows")]
        public void NetworkAndDeviceWorkspacesAreRefused(string workspace) {
            var refused = Assert.Throws<AgentException>(() => AgentRunRequest.FromJson(Run(workspace: workspace)));

            Assert.Equal("invalid_params", refused.Code);
        }

        [Fact]
        public void ALocalFolderIsAcceptedAsTheWorkspace() {
            var folder = Path.GetTempPath();

            Assert.Equal(Path.GetFullPath(folder), AgentRunRequest.FromJson(Run(workspace: folder)).Workspace);
        }

        [Fact]
        public void AWorkspaceThatIsOrIsBehindAJunctionIsRefused() {
            var root = Path.Combine(Path.GetTempPath(), "agent-workspace-" + Guid.NewGuid().ToString("N"));
            var real = Path.Combine(root, "real");
            var link = Path.Combine(root, "link");
            Directory.CreateDirectory(Path.Combine(real, "inner"));
            try {
                Assert.True(TryCreateJunction(link, real, out var error), "mklink /J failed: " + error);

                var linked = Assert.Throws<AgentException>(() => AgentRunRequest.FromJson(Run(workspace: link)));
                var behind = Assert.Throws<AgentException>(() => AgentRunRequest.FromJson(Run(workspace: Path.Combine(link, "inner"))));

                Assert.Equal("invalid_params", linked.Code);
                Assert.Contains(link, linked.Message);
                Assert.Equal("invalid_params", behind.Code);
                Assert.Contains(link, behind.Message);
                if (!TempRootIsBehindALink())
                    Assert.Equal(real, AgentRunRequest.FromJson(Run(workspace: real)).Workspace);
            }
            finally {
                if (Directory.Exists(link))
                    Directory.Delete(link);
                Directory.Delete(root, true);
            }
        }

        private static bool TempRootIsBehindALink() {
            for (var folder = new DirectoryInfo(Path.GetFullPath(Path.GetTempPath())); folder != null; folder = folder.Parent)
                if (folder.Attributes.HasFlag(FileAttributes.ReparsePoint))
                    return true;
            return false;
        }

        private static bool TryCreateJunction(string link, string target, out string error) {
            var start = new ProcessStartInfo("cmd.exe", $"/c mklink /J \"{link}\" \"{target}\"") {
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            };
            using (var process = Process.Start(start)) {
                error = process.StandardError.ReadToEnd();
                process.WaitForExit();
                return process.ExitCode == 0;
            }
        }

        [Fact]
        public void TitlesLoseLineBreaksAndFormatCharactersButKeepEmoji() {
            var request = AgentRunRequest.FromJson(Run(title: "Door \U0001F6AA fix\r\nAdded: 0\t\u2028x\u200By\u202Ez"));

            Assert.Equal("Door \U0001F6AA fix Added: 0 x y z", request.Title);
        }

        [Fact]
        public void LongTitlesAreCutWithoutSplittingACharacter() {
            var request = AgentRunRequest.FromJson(Run(title: new string('a', 198) + "\U0001F6AA" + new string('b', 500)));

            Assert.Equal(new string('a', 198) + "…", request.Title);
        }
    }
}
