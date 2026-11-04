using System.IO;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
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
        [InlineData(@"\server\share")]
        [InlineData("//server/share")]
        [InlineData(@"\/server/share")]
        [InlineData(@"/\server\share")]
        [InlineData(@"\?\C:\Windows")]
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
        public void TitlesLoseLineBreaksAndFormatCharactersButKeepEmoji() {
            var request = AgentRunRequest.FromJson(Run(title: "Door \U0001F6AA fix\r\nAdded: 0\t\u2028x\u200By\u202Ez"));

            Assert.Equal("Door \U0001F6AA fix Added: 0 x y z", request.Title);
        }
    }
}
