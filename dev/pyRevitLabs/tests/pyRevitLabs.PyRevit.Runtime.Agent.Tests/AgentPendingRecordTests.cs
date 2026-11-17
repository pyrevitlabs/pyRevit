using System;
using System.IO;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    /// <summary>
    /// Covers the provisional record written while a run waits for approval.
    /// </summary>
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

        /// <summary>
        /// The provisional record names the run and request and marks it as awaiting approval.
        /// </summary>
        [Fact]
        public void TheRecordSaysTheRunAwaitsApprovalAndNamesTheRequest() {
            var record = AgentPendingRecord.Build(Request(), "abc123", "C:\\runs\\abc123");

            Assert.Equal("pending", record.Value<string>("status"));
            Assert.Equal("awaiting_approval", record.Value<string>("decision"));
            Assert.Equal("abc123", record.Value<string>("run_id"));
            Assert.Equal("req-0123456789ab", record.Value<string>("request_id"));
            Assert.Equal("Rename template", record.Value<string>("title"));
        }

        /// <summary>
        /// Writing leaves a readable response.json in the run folder.
        /// </summary>
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

        /// <summary>
        /// A missing run folder is tolerated because the record is best effort.
        /// </summary>
        [Fact]
        public void AMissingRunFolderDoesNotThrow() {
            var missing = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));

            AgentPendingRecord.Write(Request(), "abc123", missing);
        }

        /// <summary>
        /// A read-only response.json is tolerated and left unchanged because the record is best effort.
        /// </summary>
        [Fact]
        public void AReadOnlyExistingRecordDoesNotThrow() {
            var runDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(runDir);
            var path = Path.Combine(runDir, "response.json");
            File.WriteAllText(path, "{}");
            File.SetAttributes(path, FileAttributes.ReadOnly);
            try {
                AgentPendingRecord.Write(Request(), "abc123", runDir);

                Assert.Equal("{}", File.ReadAllText(path));
            }
            finally {
                File.SetAttributes(path, FileAttributes.Normal);
                Directory.Delete(runDir, true);
            }
        }
    }
}
