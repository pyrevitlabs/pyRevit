using System;
using System.Collections.Generic;
using System.IO;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Integration")]
    public sealed class AgentRecordPrunerTests : IDisposable {
        private static readonly DateTime Cutoff = DateTime.Now.AddDays(-14);
        private static readonly DateTime Expired = DateTime.Now.AddDays(-40);

        private readonly string root;
        private readonly string runs;
        private readonly string captures;

        public AgentRecordPrunerTests() {
            root = Path.Combine(Path.GetTempPath(), "agent-prune-" + Guid.NewGuid().ToString("N"));
            runs = Path.Combine(root, "runs");
            captures = Path.Combine(root, "captures");
            Directory.CreateDirectory(runs);
            Directory.CreateDirectory(captures);
        }

        public void Dispose() {
            if (Directory.Exists(root))
                Directory.Delete(root, recursive: true);
        }

        [Fact]
        public void ExpiredRunsAndCapturesAreRemovedAndRecentOnesKept() {
            var expiredRun = Run("old", Expired);
            var recentRun = Run("new", DateTime.Now);
            var expiredCapture = Capture("old.png", Expired);
            var recentCapture = Capture("new.png", DateTime.Now);
            var failures = new List<string>();

            var removed = AgentRecordPruner.Prune(runs, captures, Cutoff, failures);

            Assert.Equal(2, removed);
            Assert.Empty(failures);
            Assert.False(Directory.Exists(expiredRun));
            Assert.True(Directory.Exists(recentRun));
            Assert.False(File.Exists(expiredCapture));
            Assert.True(File.Exists(recentCapture));
        }

        [Fact]
        public void AFileInUseKeepsOnlyItsOwnRunAndTheRestIsStillPruned() {
            var lockedRun = Run("locked", Expired);
            var lockedFile = Path.Combine(lockedRun, "exports", "A101.pdf");
            var otherRun = Run("other", Expired);
            var expiredCapture = Capture("old.png", Expired);
            var failures = new List<string>();

            using (new FileStream(lockedFile, FileMode.Open, FileAccess.Read, FileShare.None)) {
                AgentRecordPruner.Prune(runs, captures, Cutoff, failures);

                Assert.True(File.Exists(lockedFile));
                Assert.False(Directory.Exists(otherRun));
                Assert.False(File.Exists(expiredCapture));
                Assert.Contains(failures, failure => failure.Contains(Path.GetFileName(lockedRun)));
            }

            Directory.SetLastWriteTime(lockedRun, Expired);
            failures.Clear();
            AgentRecordPruner.Prune(runs, captures, Cutoff, failures);

            Assert.False(Directory.Exists(lockedRun));
            Assert.Empty(failures);
        }

        [Fact]
        public void ACaptureInUseDoesNotStopTheOtherCaptures() {
            var lockedCapture = Capture("locked.png", Expired);
            var otherCapture = Capture("other.png", Expired);
            var failures = new List<string>();

            using (new FileStream(lockedCapture, FileMode.Open, FileAccess.Read, FileShare.None))
                AgentRecordPruner.Prune(runs, captures, Cutoff, failures);

            Assert.True(File.Exists(lockedCapture));
            Assert.False(File.Exists(otherCapture));
            Assert.Single(failures);
        }

        [Fact]
        public void MissingFoldersPruneNothing() {
            var failures = new List<string>();

            var removed = AgentRecordPruner.Prune(
                Path.Combine(root, "no-runs"), Path.Combine(root, "no-captures"), Cutoff, failures);

            Assert.Equal(0, removed);
            Assert.Empty(failures);
        }

        private string Run(string name, DateTime lastWrite) {
            var run = Path.Combine(runs, name);
            var exports = Path.Combine(run, "exports");
            Directory.CreateDirectory(exports);
            File.WriteAllText(Path.Combine(run, "script.py"), "");
            File.WriteAllText(Path.Combine(exports, "A101.pdf"), "");
            Directory.SetLastWriteTime(run, lastWrite);
            return run;
        }

        private string Capture(string name, DateTime lastWrite) {
            var capture = Path.Combine(captures, name);
            File.WriteAllText(capture, "");
            File.SetLastWriteTime(capture, lastWrite);
            return capture;
        }
    }
}
