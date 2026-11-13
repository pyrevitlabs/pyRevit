using System;
using System.IO;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentPendingRecordTests {
        private static AgentRunRequest Request() {
            var request = AgentRunRequest.FromJson(new JObject {
                ["script"] = "pass",
                ["engine"] = "ironpython",
                ["title"] = "Rename template",
            });
            request.RequestId = "req-0123456789ab";
            return request;
        }

        [Fact]
        public void TheRecordSaysTheRunAwaitsApprovalAndNamesTheRequest() {
            var record = AgentPendingRecord.Build(Request(), "abc123", "C:\\runs\\abc123");

            Assert.Equal("pending", record.Value<string>("status"));
            Assert.Equal("awaiting_approval", record.Value<string>("decision"));
            Assert.Equal("abc123", record.Value<string>("run_id"));
            Assert.Equal("req-0123456789ab", record.Value<string>("request_id"));
            Assert.Equal("Rename template", record.Value<string>("title"));
        }

        [Fact]
        public void WritingLeavesResponseJsonInTheRunFolder() {
            var runDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(runDir);
            try {
                AgentPendingRecord.Write(Request(), "abc123", runDir);

                var written = JObject.Parse(File.ReadAllText(Path.Combine(runDir, "response.json")));
                Assert.Equal("awaiting_approval", written.Value<string>("decision"));
            }
            finally {
                Directory.Delete(runDir, true);
            }
        }

        [Fact]
        public void AMissingRunFolderDoesNotThrow() {
            var missing = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));

            AgentPendingRecord.Write(Request(), "abc123", missing);
        }
    }
}
