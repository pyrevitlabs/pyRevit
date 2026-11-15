using System;
using Autodesk.Revit.DB;

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
            Assert.Equal("failed: Revit did not start the temporary capture group, so the view was not changed.", failure.Message);
            Assert.Equal(0, document.TransactionStarts);
            Assert.Equal(0, document.RollbackCalls);
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
            Assert.Equal(0, document.OpenTransactions);
        }

        /// <summary>
        /// A transaction Revit does not start fails the capture before the view is changed, and the
        /// group is rolled back.
        /// </summary>
        [Fact]
        public void ATransactionThatDoesNotStartFailsTheCaptureBeforePreparing() {
            var document = new Document { TransactionStartStatus = TransactionStatus.Uninitialized };
            var prepared = false;

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run(document, "t", () => { prepared = true; return 1; }, target => "png", Describe));

            Assert.Equal("capture_failed", failure.Code);
            Assert.Equal("failed: Revit did not start the temporary view change (status Uninitialized).", failure.Message);
            Assert.False(prepared);
            Assert.Equal(1, document.RollbackCalls);
        }

        /// <summary>
        /// A rollback Revit does not confirm is reported as rollback_incomplete, not as a success.
        /// </summary>
        [Fact]
        public void AnUnconfirmedRollbackFailsTheCapture() {
            var document = new Document { RollbackStatus = TransactionStatus.Started };

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run(document, "t", () => 1, target => "png", Describe));

            Assert.Equal("rollback_incomplete", failure.Code);
            Assert.Equal("failed: Revit did not confirm the rollback of the temporary capture group (status Started).", failure.Message);
        }

        /// <summary>
        /// A rollback that throws after a successful export is reported as rollback_incomplete.
        /// </summary>
        [Fact]
        public void ARollbackThatThrowsAfterAnExportFailsTheCapture() {
            var document = new Document { ThrowOnRollback = true };

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run(document, "t", () => 1, target => "png", Describe));

            Assert.Equal("rollback_incomplete", failure.Code);
            Assert.Equal("failed: Revit could not roll back the temporary capture group: Rollback failed.", failure.Message);
        }

        /// <summary>
        /// A rollback that throws never masks the capture failure: the original code and message are kept
        /// and the rollback failure is added to the error details sent to the client.
        /// </summary>
        [Fact]
        public void ARollbackThatThrowsDoesNotMaskTheCaptureFailure() {
            var document = new Document { ThrowOnRollback = true };

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run<int>(document, "t",
                    () => throw new AgentException("view_not_supported", "no"), target => "png", Describe));

            Assert.Equal("view_not_supported", failure.Code);
            Assert.Equal("no", failure.Message);
            Assert.Contains("Rollback failed.", failure.Details.Value<string>("rollback_failure"));
        }

        /// <summary>
        /// A rollback that throws after a non-agent failure keeps the original exception object and
        /// exposes the rollback problem to the request handler through RollbackFailureOf.
        /// </summary>
        [Fact]
        public void ARollbackThatThrowsAfterAnIoFailureKeepsTheExceptionAndExposesTheRollbackProblem() {
            var document = new Document { ThrowOnRollback = true };
            var original = new System.IO.IOException("disk full");

            var failure = Assert.Throws<System.IO.IOException>(() =>
                AgentCaptureGroup.Run<int>(document, "t", () => 1, target => throw original, Describe));

            Assert.Same(original, failure);
            Assert.Contains("Rollback failed.", AgentCaptureGroup.RollbackFailureOf(failure));
        }

        /// <summary>
        /// An exception without a rollback problem has no rollback failure to forward.
        /// </summary>
        [Fact]
        public void AnExceptionWithoutARollbackProblemHasNoRollbackFailure() {
            Assert.Null(AgentCaptureGroup.RollbackFailureOf(new System.IO.IOException("disk full")));
        }

        /// <summary>
        /// An unconfirmed rollback after a capture failure keeps the original code and message and adds
        /// the status to the error details.
        /// </summary>
        [Fact]
        public void AnUnconfirmedRollbackDoesNotMaskTheCaptureFailure() {
            var document = new Document { RollbackStatus = TransactionStatus.Started };

            var failure = Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run<int>(document, "t",
                    () => throw new AgentException("view_not_supported", "no"), target => "png", Describe));

            Assert.Equal("view_not_supported", failure.Code);
            Assert.Contains("Started", failure.Details.Value<string>("rollback_failure"));
        }

        /// <summary>
        /// A failed prepare leaves no open transaction: it rolls back when disposed, like in Revit.
        /// </summary>
        [Fact]
        public void AFailedPrepareLeavesNoTransactionBehind() {
            var document = new Document();

            Assert.Throws<AgentException>(() =>
                AgentCaptureGroup.Run<int>(document, "t",
                    () => throw new AgentException("view_not_supported", "no"), target => "png", Describe));

            Assert.Equal(0, document.OpenTransactions);
            Assert.Equal(1, document.TransactionsRolledBackOnDispose);
        }

        /// <summary>
        /// An exception that is not a Revit one still rolls the group back and passes through.
        /// </summary>
        [Theory]
        [InlineData(typeof(InvalidOperationException))]
        [InlineData(typeof(System.IO.IOException))]
        public void AnUnexpectedExportExceptionStillRollsTheGroupBack(Type exceptionType) {
            var document = new Document();

            var failure = Assert.Throws(exceptionType, () =>
                AgentCaptureGroup.Run<int>(document, "t", () => 1,
                    target => throw (Exception)Activator.CreateInstance(exceptionType, "boom"), Describe));

            Assert.Equal("boom", failure.Message);
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
