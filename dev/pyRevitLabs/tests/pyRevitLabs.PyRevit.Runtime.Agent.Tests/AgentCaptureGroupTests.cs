using System;
using Autodesk.Revit.DB;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    /// <summary>
    /// Covers the status checks of the capture group that always rolls back.
    /// </summary>
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentCaptureGroupTests {
        private static string Describe(string message) => "failed: " + message;

        /// <summary>
        /// A group left uninitialized by Start fails the capture before any transaction opens.
        /// </summary>
        [Fact]
        public void AnUninitializedGroupFailsTheCaptureWithoutOpeningATransaction() {
            AssertCaptureFailsWithoutTransaction(TransactionStatus.Uninitialized);
        }

        /// <summary>
        /// A group that Start reports as rolled back fails the capture before any transaction opens.
        /// </summary>
        [Fact]
        public void ARolledBackGroupFailsTheCaptureWithoutOpeningATransaction() {
            AssertCaptureFailsWithoutTransaction(TransactionStatus.RolledBack);
        }

        private static void AssertCaptureFailsWithoutTransaction(TransactionStatus start) {
            var document = new Document { StartStatus = start };
            var prepared = false;

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run(document, "t", () => { prepared = true; return 1; }, target => "png", Describe));

            Assert.Equal("capture_failed", failure.Code);
            Assert.False(prepared);
            Assert.Equal(0, document.TransactionStarts);
        }

        /// <summary>
        /// A transaction Revit does not commit fails the capture and the started group is rolled back.
        /// </summary>
        [Fact]
        public void ATransactionThatDoesNotCommitFailsTheCaptureAndRollsTheGroupBack() {
            var document = new Document { CommitStatus = TransactionStatus.RolledBack };
            var exported = false;

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run(document, "t", () => 1, target => { exported = true; return "png"; }, Describe));

            Assert.Equal("capture_failed", failure.Code);
            Assert.Contains("RolledBack", failure.Message);
            Assert.False(exported);
            Assert.Equal(1, document.TransactionStarts);
            Assert.Equal(1, document.RollbackCalls);
        }

        /// <summary>
        /// A started and committed capture exports the prepared target and still rolls the group back.
        /// </summary>
        [Fact]
        public void ASuccessfulCaptureExportsThePreparedTargetAndRollsTheGroupBack() {
            var document = new Document();

            var result = AgentCaptureGroup.Run(document, "t", () => 7, target => "png" + target, Describe);

            Assert.Equal("png7", result);
            Assert.Equal(1, document.TransactionStarts);
            Assert.Equal(1, document.RollbackCalls);
        }

        /// <summary>
        /// The group is rolled back when the export itself throws, so the temporary view never stays.
        /// </summary>
        [Fact]
        public void AFailingExportStillRollsTheGroupBack() {
            var document = new Document();

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run<int>(document, "t", () => 1,
                    target => throw new Autodesk.Revit.Exceptions.ApplicationException("boom"), Describe));

            Assert.Equal("capture_failed", failure.Code);
            Assert.Equal("failed: boom", failure.Message);
            Assert.Equal(1, document.RollbackCalls);
        }

        /// <summary>
        /// A Revit exception raised while preparing the view becomes capture_failed and rolls back.
        /// </summary>
        [Fact]
        public void ARevitExceptionWhilePreparingFailsTheCaptureAndRollsTheGroupBack() {
            var document = new Document();

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run<int>(document, "t",
                    () => throw new Autodesk.Revit.Exceptions.ApplicationException("bad view"),
                    target => "png", Describe));

            Assert.Equal("failed: bad view", failure.Message);
            Assert.Equal(1, document.RollbackCalls);
        }

        /// <summary>
        /// An AgentException from preparing passes through unchanged and still rolls back.
        /// </summary>
        [Fact]
        public void AnAgentExceptionWhilePreparingPassesThroughAndRollsTheGroupBack() {
            var document = new Document();

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run<int>(document, "t",
                    () => throw new AgentException("view_not_supported", "no"), target => "png", Describe));

            Assert.Equal("view_not_supported", failure.Code);
            Assert.Equal(1, document.RollbackCalls);
        }
    }
}
