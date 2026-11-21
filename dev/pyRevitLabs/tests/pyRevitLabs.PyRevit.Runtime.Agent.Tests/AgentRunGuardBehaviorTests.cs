using System;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public class AgentRunGuardFailureTests {
        [Fact]
        public void WarningsAreRecordedDeletedAndDoNotRollBack() {
            var app = new UIApplication();
            var document = new Document { Title = "Model" };
            var warning = new FailureMessage(FailureSeverity.Warning, "Walls overlap");
            var accessor = new FailuresAccessor(document, warning);
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                var result = app.Application.ProcessFailures(accessor);

                Assert.Equal(FailureProcessingResult.Continue, result);
                Assert.Equal(0, guard.ErrorRollbacks);
                Assert.Same(warning, Assert.Single(accessor.DeletedWarnings));
                var failure = Assert.Single(guard.Failures);
                Assert.Equal("Warning", failure.Value<string>("severity"));
                Assert.Equal("Walls overlap", failure.Value<string>("description"));
                Assert.Equal("Model", failure.Value<string>("document"));
                Assert.Equal("Test transaction", failure.Value<string>("transaction"));
            }
        }

        [Fact]
        public void ErrorsAreRecordedAndRollTheTransactionBack() {
            var app = new UIApplication();
            var document = new Document();
            var accessor = new FailuresAccessor(document, new FailureMessage(FailureSeverity.Error, "Opening is wider than its wall"));
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                var result = app.Application.ProcessFailures(accessor);

                Assert.Equal(FailureProcessingResult.ProceedWithRollBack, result);
                Assert.Equal(1, guard.ErrorRollbacks);
                Assert.Equal("Opening is wider than its wall", guard.FirstErrorDescription);
                Assert.Empty(accessor.DeletedWarnings);
                Assert.Equal("Error", Assert.Single(guard.Failures).Value<string>("severity"));
            }
        }

        [Fact]
        public void EachFailedTransactionCountsOnceAndOnlyTheFirstErrorIsKept() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.ProcessFailures(new FailuresAccessor(
                    document,
                    new FailureMessage(FailureSeverity.Error, "first"),
                    new FailureMessage(FailureSeverity.Error, "second")));
                app.Application.ProcessFailures(new FailuresAccessor(document, new FailureMessage(FailureSeverity.Error, "third")));

                Assert.Equal(2, guard.ErrorRollbacks);
                Assert.Equal("first", guard.FirstErrorDescription);
                Assert.Equal(3, guard.Failures.Count);
            }
        }

        [Fact]
        public void WarningsAreStillDeletedWhenAnErrorRollsTheTransactionBack() {
            var app = new UIApplication();
            var document = new Document();
            var warning = new FailureMessage(FailureSeverity.Warning, "minor");
            var accessor = new FailuresAccessor(document, warning, new FailureMessage(FailureSeverity.Error, "major"));
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                var result = app.Application.ProcessFailures(accessor);

                Assert.Equal(FailureProcessingResult.ProceedWithRollBack, result);
                Assert.Same(warning, Assert.Single(accessor.DeletedWarnings));
            }
        }

        [Fact]
        public void FailuresInLinkedDocumentsAndWithoutADocumentAreIgnored() {
            var app = new UIApplication();
            var document = new Document();
            var linked = new Document { IsLinked = true };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                var forLinked = app.Application.ProcessFailures(new FailuresAccessor(linked, new FailureMessage(FailureSeverity.Error)));
                var withoutDocument = app.Application.ProcessFailures(new FailuresAccessor(null, new FailureMessage(FailureSeverity.Error)));

                Assert.Null(forLinked);
                Assert.Null(withoutDocument);
                Assert.Empty(guard.Failures);
                Assert.Equal(0, guard.ErrorRollbacks);
            }
        }

        [Fact]
        public void RecordedFailuresAreCappedButAnErrorAfterTheCapStillRollsBack() {
            var app = new UIApplication();
            var document = new Document();
            var messages = Enumerable.Range(0, 200).Select(index => new FailureMessage(FailureSeverity.Warning, "w" + index)).ToList();
            messages.Add(new FailureMessage(FailureSeverity.Error, "late error"));
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                var result = app.Application.ProcessFailures(new FailuresAccessor(document, messages.ToArray()));

                Assert.Equal(200, guard.Failures.Count);
                Assert.Equal(FailureProcessingResult.ProceedWithRollBack, result);
                Assert.Equal("late error", guard.FirstErrorDescription);
            }
        }
    }

    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public class AgentRunGuardBlockTests {
        [Fact]
        public void NonCancellableEventsAreNeitherCancelledNorReported() {
            var app = new UIApplication();
            var document = new Document();
            app.Application.Documents.Add(document);
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                var cancellableAllowed = app.Application.Save(document);
                var nonCancellableAllowed = app.Application.Save(document, cancellable: false);

                Assert.False(cancellableAllowed);
                Assert.True(nonCancellableAllowed);
                Assert.Single(guard.Blocked);
            }
        }

        [Fact]
        public void ClosingADocumentThatWasOpenAtStartIsBlockedButOneTheRunOpenedIsNot() {
            var app = new UIApplication();
            var existing = new Document { Title = "Existing" };
            app.Application.Documents.Add(existing);
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var opened = new Document { Title = "Opened by the run" };
                app.Application.Open(opened);

                var closedExisting = app.Application.CloseDocument(existing);
                var closedOpened = app.Application.CloseDocument(opened);

                Assert.False(closedExisting);
                Assert.True(closedOpened);
                var blocked = Assert.Single(guard.Blocked);
                Assert.Equal("close", blocked.Value<string>("operation"));
                Assert.Equal("Existing", blocked.Value<string>("document"));
            }
        }

        [Fact]
        public void BlockedOperationsAreExplainedAndNothingIsReportedWhenNoneWereBlocked() {
            var app = new UIApplication();
            var document = new Document { Title = "Family23" };
            app.Application.Documents.Add(document);
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                Assert.Null(guard.DescribeBlockedOperations());

                app.Application.SaveAs(document);

                Assert.Equal(
                    "operation_blocked: save_as of 'Family23' not allowed in agent runs; the user must do it in Revit.",
                    guard.DescribeBlockedOperations());
            }
        }

        [Fact]
        public void BlockedOperationsWithoutADocumentOmitItAndRepeatsCollapse() {
            var app = new UIApplication();
            var document = new Document { Title = "Model" };
            app.Application.Documents.Add(document);
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.ExportFile();
                app.Application.ExportFile();
                app.Application.Save(document);

                Assert.Equal(
                    "operation_blocked: file_export, save of 'Model' not allowed in agent runs; the user must do it in Revit. "
                    + "Revit exports may only write into the run's export_dir.",
                    guard.DescribeBlockedOperations());
            }
        }

        [Fact]
        public void DocumentsOpenedFromDiskStillReportRolledBackWithoutAScope() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var opened = new Document { Title = "Disk", PathName = "existing.rvt" };
                app.Application.Open(opened);
                app.Application.Change(opened);

                var description = guard.DescribeOtherDocuments()[0];

                Assert.NotNull(description["rolled_back"]);
                Assert.Null(description["scope"]);
            }
        }

        [Fact]
        public void DocumentsCreatedDuringTheRunStateTheirScopeInsteadOfARollbackFlag() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var created = new Document { Title = "Family23" };
                app.Application.Create(created);
                app.Application.Change(created);

                var description = guard.DescribeOtherDocuments()[0];

                Assert.True(description.Value<bool>("opened_during_run"));
                Assert.Null(description["rolled_back"]);
                Assert.Contains("not rolled back", description.Value<string>("scope"));
            }
        }

        [Fact]
        public void ABlockedSaveNamesTheDocument() {
            var app = new UIApplication();
            var document = new Document { Title = "Tower" };
            app.Application.Documents.Add(document);
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Save(document);

                var blocked = Assert.Single(guard.Blocked);
                Assert.Equal("save", blocked.Value<string>("operation"));
                Assert.Equal("Tower", blocked.Value<string>("document"));
            }
        }

        [Fact]
        public void EventsAfterDisposeAreNeitherBlockedNorRecorded() {
            var app = new UIApplication();
            var document = new Document();
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");
            guard.Dispose();

            var saved = app.Application.Save(document);
            var exported = app.Application.ExportFile();
            app.Application.Change(document);

            Assert.True(saved);
            Assert.True(exported);
            Assert.Empty(guard.Blocked);
            Assert.True(guard.Changes.IsEmpty);
        }
    }

    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public class AgentRunGuardGroupTests {
        [Fact]
        public void TheActiveDocumentGetsAGroupThatRollBackCloses() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                Assert.True(guard.HasOpenGroup);

                guard.RollBack();

                Assert.False(guard.HasOpenGroup);
                Assert.Equal(1, document.RollbackCalls);
            }
        }

        [Fact]
        public void AssimilateKeepsTheActiveDocumentChangesAndRollsBackTheOthers() {
            var app = new UIApplication();
            var active = new Document();
            var other = new Document();
            app.Application.Documents.Add(active);
            app.Application.Documents.Add(other);
            using (var guard = new AgentRunGuard(app, active)) {
                guard.Arm("Test");

                guard.Assimilate();

                Assert.False(guard.HasOpenGroup);
                Assert.Equal(0, active.RollbackCalls);
                Assert.Equal(1, other.RollbackCalls);
            }
        }

        [Fact]
        public void ReadOnlyOrMissingActiveDocumentsOpenNoGroup() {
            var app = new UIApplication();
            using (var readOnly = new AgentRunGuard(app, new Document { IsReadOnly = true })) {
                readOnly.Arm("Test");
                Assert.False(readOnly.HasOpenGroup);
            }
            using (var none = new AgentRunGuard(app, null)) {
                none.Arm("Test");
                Assert.False(none.HasOpenGroup);
            }
        }

        [Fact]
        public void DisposeRollsBackAGroupTheRunLeftOpen() {
            var app = new UIApplication();
            var document = new Document();
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");

            guard.Dispose();

            Assert.Equal(1, document.RollbackCalls);
            Assert.False(guard.HasOpenGroup);
        }

        [Fact]
        public void DisposeSurvivesAFailingRollbackAndStillStopsWatching() {
            var app = new UIApplication();
            var document = new Document { ThrowOnRollback = true };
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");

            guard.Dispose();

            Assert.True(app.Application.Save(document));
            Assert.True(guard.RollbackFailed);
            Assert.False(guard.Committed);
            Assert.Contains(guard.CleanupFailures, failure => failure.Contains("Rollback failed."));
        }

        [Fact]
        public void ArmFailsWhenTheActiveGroupDoesNotStart() {
            var document = new Document { StartStatus = TransactionStatus.Uninitialized };
            using (var guard = new AgentRunGuard(new UIApplication(), document)) {
                Assert.Throws<InvalidOperationException>(() => guard.Arm("Test"));
                Assert.False(guard.HasOpenGroup);
            }
        }

        [Fact]
        public void OnlyAnAssimilatedRunCountsAsCommitted() {
            var document = new Document();
            var guard = new AgentRunGuard(new UIApplication(), document);
            guard.Arm("Test");
            guard.Assimilate();
            guard.Dispose();

            Assert.True(guard.Committed);
            Assert.False(guard.RollbackFailed);
            Assert.Equal(0, document.RollbackCalls);
        }

        /// <summary>
        /// An assimilation Revit does not confirm throws and leaves Committed false, so the guard-level
        /// host-error decision is rolled_back. That is not a confirmed rollback: when cleanup finds the
        /// model still shows changes, the run service reports rollback_incomplete instead, which
        /// AnAssimilationRevitRolledBackStillReportsTracesTheModelShows covers.
        /// </summary>
        [Fact]
        public void AnAssimilationRevitDoesNotConfirmIsNotCommitted() {
            var document = new Document { AssimilateStatus = TransactionStatus.RolledBack };
            using (var guard = new AgentRunGuard(new UIApplication(), document)) {
                guard.Arm("Test");

                Assert.Throws<InvalidOperationException>(() => guard.Assimilate());

                Assert.False(guard.Committed);
            }
        }

        [Fact]
        public void LinkedDocumentsAreNotTrackedAsChangedOtherDocuments() {
            var app = new UIApplication();
            var active = new Document();
            var linked = new Document { IsLinked = true };
            app.Application.Documents.Add(active);
            app.Application.Documents.Add(linked);
            using (var guard = new AgentRunGuard(app, active)) {
                guard.Arm("Test");

                app.Application.Create(new Document { IsLinked = true });

                Assert.False(guard.ChangedOtherOpenDocument);
                Assert.Empty(guard.DescribeOtherDocuments());
            }
        }
    }

    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public class AgentRunGuardRollbackVerificationTests {
        [Fact]
        public void ARollbackThatLeavesADeletedElementMissingFailsTheRun() {
            var app = new UIApplication();
            var document = new Document();
            var deleted = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
                document.Deleted.Add(deleted);

                guard.RollBack();

                Assert.True(guard.RollbackFailed);
            }
        }

        [Fact]
        public void ARollbackThatLeavesAnAddedElementInTheModelFailsTheRun() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { new ElementId() });

                guard.RollBack();

                Assert.True(guard.RollbackFailed);
            }
        }

        [Fact]
        public void ARollbackRevitRefusesKeepsItsReason() {
            var document = new Document { ThrowOnRollback = true };
            using (var guard = new AgentRunGuard(new UIApplication(), document)) {
                guard.Arm("Test");

                Assert.Throws<InvalidOperationException>(guard.RollBack);

                Assert.True(guard.RollbackFailed);
                Assert.Contains("Rollback failed.", guard.RollbackFailureReason);
            }
        }

        [Fact]
        public void ARollbackRevitLeavesPendingKeepsTheStatusAsItsReason() {
            var document = new Document { RollbackStatus = TransactionStatus.Pending };
            using (var guard = new AgentRunGuard(new UIApplication(), document)) {
                guard.Arm("Test");

                guard.RollBack();

                Assert.True(guard.RollbackFailed);
                Assert.Contains("Pending", guard.RollbackFailureReason);
            }
        }

        [Fact]
        public void ARollbackThatLeavesTracesSaysSo() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { new ElementId() });

                guard.RollBack();

                Assert.Contains("still shows the run's changes", guard.RollbackFailureReason);
            }
        }

        [Fact]
        public void TheFirstRollbackFailureReasonIsKept() {
            var document = new Document { ThrowOnRollback = true };
            var guard = new AgentRunGuard(new UIApplication(), document);
            guard.Arm("Test");
            Assert.Throws<InvalidOperationException>(guard.RollBack);
            var first = guard.RollbackFailureReason;

            guard.Dispose();

            Assert.Equal(first, guard.RollbackFailureReason);
        }

        [Fact]
        public void ACompletedRollbackHasNoFailureReason() {
            using (var guard = new AgentRunGuard(new UIApplication(), new Document())) {
                guard.Arm("Test");

                guard.RollBack();

                Assert.Null(guard.RollbackFailureReason);
            }
        }

        [Fact]
        public void ARollbackThatRestoresTheModelDoesNotFailTheRun() {
            var app = new UIApplication();
            var document = new Document();
            var deleted = new ElementId();
            var added = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { added }, deleted: new[] { deleted });
                document.Deleted.Add(added);

                guard.RollBack();

                Assert.False(guard.RollbackFailed);
            }
        }

        /// <summary>
        /// Loading a family creates elements Revit never reports as added, and overwriting the
        /// family deletes them again. They are missing after every rollback and must not count
        /// as a lost element.
        /// </summary>
        [Fact]
        public void AnElementTheRunCreatedAndDeletedIsNotATraceAfterTheRollback() {
            var app = new UIApplication();
            var document = new Document { HighestElementValue = 100 };
            var loadedFamily = new ElementId { Value = 102 };
            var createdByRun = new ElementId { Value = 101 };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { loadedFamily }, deleted: new[] { createdByRun });
                document.Deleted.Add(loadedFamily);
                document.Deleted.Add(createdByRun);

                guard.RollBack();

                Assert.False(guard.RollbackFailed);
            }
        }

        /// <summary>
        /// An element added and deleted again leaves the change set's added elements, but the
        /// run still created things, so elements Revit never reported are not a lost element.
        /// </summary>
        [Fact]
        public void AnAdditionThatTheRunDeletedAgainStillMarksTheRunAsHavingCreatedElements() {
            var app = new UIApplication();
            var document = new Document { HighestElementValue = 100 };
            var loadedFamily = new ElementId { Value = 102 };
            var createdByRun = new ElementId { Value = 101 };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { loadedFamily }, deleted: Array.Empty<ElementId>());
                app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { loadedFamily, createdByRun });
                document.Deleted.Add(loadedFamily);
                document.Deleted.Add(createdByRun);

                guard.RollBack();

                Assert.False(guard.RollbackFailed);
            }
        }

        [Fact]
        public void AnElementThatExistedBeforeTheRunAndIsStillMissingIsATraceAfterTheRollback() {
            var app = new UIApplication();
            var document = new Document { HighestElementValue = 100 };
            var loadedFamily = new ElementId { Value = 102 };
            var existedBefore = new ElementId { Value = 99 };
            var createdByRun = new ElementId { Value = 101 };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { loadedFamily }, deleted: new[] { existedBefore, createdByRun });
                document.Deleted.Add(loadedFamily);
                document.Deleted.Add(existedBefore);
                document.Deleted.Add(createdByRun);

                guard.RollBack();

                Assert.True(guard.RollbackFailed);
            }
        }

        /// <summary>
        /// Without a recorded addition the run created nothing, so a missing deleted element
        /// existed before the run whatever its id, even above every element left in the model.
        /// </summary>
        [Fact]
        public void ARunThatAddedNothingCountsEveryMissingDeletedElementAfterTheRollback() {
            var app = new UIApplication();
            var document = new Document { HighestElementValue = 100 };
            var newestElement = new ElementId { Value = 101 };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { newestElement });
                document.Deleted.Add(newestElement);

                guard.RollBack();

                Assert.True(guard.RollbackFailed);
            }
        }

        [Fact]
        public void AnAssimilatedRunIsNotCheckedAgainstTheModel() {
            var app = new UIApplication();
            var document = new Document();
            var guard = new AgentRunGuard(app, document);
            var deleted = new ElementId();
            guard.Arm("Test");
            app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
            document.Deleted.Add(deleted);
            guard.Assimilate();

            guard.Dispose();

            Assert.False(guard.RollbackFailed);
            Assert.True(guard.Committed);
        }

        [Fact]
        public void ARollbackRequestedAfterTheGroupEndedStillChecksTheModel() {
            var app = new UIApplication();
            var document = new Document();
            var deleted = new ElementId();
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");
            app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
            guard.RollBack();
            Assert.False(guard.HasOpenGroup);
            Assert.False(guard.RollbackFailed);
            document.Deleted.Add(deleted);

            guard.Dispose();

            Assert.True(guard.RollbackFailed);
        }

        [Fact]
        public void ARunThatAskedToKeepItsChangesIsNotCheckedAgainstTheModelAfterTheGroupEnded() {
            var app = new UIApplication();
            var document = new Document();
            var deleted = new ElementId();
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");
            guard.RollBack();
            app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
            document.Deleted.Add(deleted);
            guard.Assimilate();

            guard.Dispose();

            Assert.False(guard.RollbackFailed);
            Assert.False(guard.Committed);
        }

        [Fact]
        public void AnAssimilationThatFailsPartwayDoesNotExemptTheRunFromTheModelCheck() {
            var app = new UIApplication();
            var active = new Document();
            var other = new Document { ThrowOnRollback = true, ThrowOnDispose = true };
            var deleted = new ElementId();
            app.Application.Documents.Add(active);
            app.Application.Documents.Add(other);
            var guard = new AgentRunGuard(app, active);
            guard.Arm("Test");
            app.Application.Change(other);
            Assert.Throws<AggregateException>(guard.RollBack);
            Assert.False(guard.HasOpenGroup);
            app.Application.Change(active, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
            active.Deleted.Add(deleted);
            Assert.Throws<AggregateException>(guard.Assimilate);

            guard.Dispose();

            Assert.True(guard.RollbackFailed);
        }

        [Fact]
        public void AnAssimilationRevitRolledBackIsNeitherCommittedNorIncompleteWhenTheModelIsClean() {
            var app = new UIApplication();
            var document = new Document { AssimilateStatus = TransactionStatus.RolledBack };
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");
            Assert.Throws<InvalidOperationException>(() => guard.Assimilate());

            guard.Dispose();

            Assert.False(guard.Committed);
            Assert.False(guard.RollbackFailed);
            Assert.Equal(0, document.RollbackCalls);
        }

        [Fact]
        public void AnAssimilationRevitRolledBackStillReportsTracesTheModelShows() {
            var app = new UIApplication();
            var document = new Document { AssimilateStatus = TransactionStatus.RolledBack };
            var deleted = new ElementId();
            var guard = new AgentRunGuard(app, document);
            guard.Arm("Test");
            app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
            document.Deleted.Add(deleted);
            Assert.Throws<InvalidOperationException>(() => guard.Assimilate());

            guard.Dispose();

            Assert.False(guard.Committed);
            Assert.True(guard.RollbackFailed);
        }

        [Fact]
        public void AGuardWithoutAnActiveGroupDoesNotCheckTheModel() {
            var app = new UIApplication();
            var document = new Document { IsReadOnly = true };
            var deleted = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
                document.Deleted.Add(deleted);

                guard.RollBack();

                Assert.False(guard.RollbackFailed);
            }
        }

        [Fact]
        public void AnotherDocumentWhoseDeletionSurvivesTheRollbackIsReportedAsNotReverted() {
            var app = new UIApplication();
            var active = new Document();
            var other = new Document();
            var deleted = new ElementId();
            app.Application.Documents.Add(active);
            app.Application.Documents.Add(other);
            using (var guard = new AgentRunGuard(app, active)) {
                guard.Arm("Test");
                app.Application.Change(other, added: Array.Empty<ElementId>(), deleted: new[] { deleted });
                other.Deleted.Add(deleted);

                guard.RollBack();

                Assert.True(guard.HasUnrevertedOtherDocumentChanges);
            }
        }

        [Fact]
        public void AnotherDocumentWhoseRollbackRestoresItIsReportedAsReverted() {
            var app = new UIApplication();
            var active = new Document();
            var other = new Document();
            app.Application.Documents.Add(active);
            app.Application.Documents.Add(other);
            using (var guard = new AgentRunGuard(app, active)) {
                guard.Arm("Test");
                app.Application.Change(other, added: Array.Empty<ElementId>(), deleted: new[] { new ElementId() });

                guard.RollBack();

                Assert.False(guard.HasUnrevertedOtherDocumentChanges);
            }
        }
    }

    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public class AgentChangeSetTests {
        [Fact]
        public void ModifyingAnElementTheRunAddedCountsItOnlyAsAdded() {
            var app = new UIApplication();
            var document = new Document();
            var element = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: new[] { element });
                app.Application.Change(document, added: Array.Empty<ElementId>(), modified: new[] { element });

                var summary = guard.Changes.Summarize();
                Assert.Equal(1, summary.Value<int>("added_count"));
                Assert.Equal(0, summary.Value<int>("modified_count"));
            }
        }

        [Fact]
        public void DeletingAModifiedElementCountsItOnlyAsDeleted() {
            var app = new UIApplication();
            var document = new Document();
            var element = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: Array.Empty<ElementId>(), modified: new[] { element });
                app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { element });

                var summary = guard.Changes.Summarize();
                Assert.Equal(0, summary.Value<int>("modified_count"));
                Assert.Equal(1, summary.Value<int>("deleted_count"));
            }
        }

        [Fact]
        public void FamiliesAndTypesAreListedFromEveryAddedElement() {
            var app = new UIApplication();
            var document = new Document();
            var others = Enumerable.Range(0, 60).Select(_ => new ElementId()).ToList();
            var family = new ElementId();
            var type = new ElementId();
            document.Elements[family] = new Family { Name = "People" };
            document.Elements[type] = new FamilySymbol { Name = "Adult" };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: others.Concat(new[] { family, type }).ToArray());

                var description = guard.Changes.Describe(document, 50);
                Assert.Equal(50, ((JArray)description["added"]).Count);
                Assert.Equal(
                    new[] { "Family:People", "FamilySymbol:Adult" },
                    description["added_families"].Select(element => element.Value<string>("class") + ":" + element.Value<string>("name")).OrderBy(text => text));
            }
        }

        [Fact]
        public void SystemTypesAreListedWithFamilies() {
            var app = new UIApplication();
            var document = new Document();
            var wallType = new ElementId();
            var wall = new ElementId();
            document.Elements[wallType] = new WallType { Name = "Generic - 300" };
            document.Elements[wall] = new Element { Name = "Wall" };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: new[] { wallType, wall });

                var description = guard.Changes.Describe(document, 50);
                Assert.Equal(
                    new[] { "WallType:Generic - 300" },
                    description["added_families"].Select(element => element.Value<string>("class") + ":" + element.Value<string>("name")));
            }
        }

        [Fact]
        public void FamiliesComeBeforeSystemTypesWhenTheListIsCut() {
            var app = new UIApplication();
            var document = new Document();
            var wallTypes = Enumerable.Range(0, 5).Select(_ => new ElementId()).ToList();
            foreach (var id in wallTypes)
                document.Elements[id] = new WallType { Name = "Copy" };
            var family = new ElementId();
            var symbol = new ElementId();
            document.Elements[family] = new Family { Name = "Desk" };
            document.Elements[symbol] = new FamilySymbol { Name = "1200x600" };
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: wallTypes.Concat(new[] { symbol, family }).ToArray());

                var description = guard.Changes.Describe(document, 2);
                Assert.Equal(
                    new[] { "Family:Desk", "FamilySymbol:1200x600" },
                    description["added_families"].Select(element => element.Value<string>("class") + ":" + element.Value<string>("name")));
            }
        }

        [Fact]
        public void TransactionNamesAreListedOnce() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document);
                app.Application.Change(document);

                Assert.Single(guard.Changes.Summarize()["transactions"]);
            }
        }

        [Fact]
        public void NothingChangedMeansAnEmptyChangeSet() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, new Document())) {
                guard.Arm("Test");

                Assert.True(guard.Changes.IsEmpty);
                Assert.Equal(0, guard.Changes.Summarize().Value<int>("added_count"));
                Assert.Equal("no changes", guard.Changes.Summarize().Value<string>("summary"));
            }
        }

        [Fact]
        public void TheSummaryNamesLoadedFamiliesTheirTypesAndTheChangedCategories() {
            var app = new UIApplication();
            var document = new Document();
            var family = Add(document, new Family { Name = "Door" });
            var types = Enumerable.Range(0, 3).Select(_ => Add(document, new FamilySymbol { Name = "Type" })).ToList();
            var legend = Add(document, new Element { Category = new Category { Name = "Legend Components" } });
            var walls = Enumerable.Range(0, 2).Select(_ => Add(document, new Element { Category = new Category { Name = "Walls" } })).ToList();
            var gone = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: types.Concat(new[] { family, legend }).ToArray(), deleted: new[] { gone }, modified: walls);

                Assert.Equal(
                    "added 1 family (Door) with 3 types and 1 other element (Legend Components), modified 2 elements (Walls), deleted 1 element",
                    guard.Changes.Describe(document, 50).Value<string>("summary"));
            }
        }

        [Fact]
        public void TheSummaryCountsModifiedElementsWithoutACategoryApartAndKeepsThemInTheSamples() {
            var app = new UIApplication();
            var document = new Document();
            var tracker = Add(document, new Element { Name = "AutoJoin Tracker Element" });
            var wall = Add(document, new Element { Category = new Category { Name = "Walls" } });
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: new ElementId[0], modified: new[] { tracker, wall });

                var description = guard.Changes.Describe(document, 50);
                Assert.Equal("modified 1 element (Walls) and 1 without a category", description.Value<string>("summary"));
                Assert.Equal(2, description.Value<int>("modified_count"));
                Assert.Equal(2, description["modified"].Count());
            }
        }

        [Fact]
        public void TheSummaryStillStatesModifiedElementsWhenNoneHasACategory() {
            var app = new UIApplication();
            var document = new Document();
            var tracker = Add(document, new Element { Name = "AutoJoin Tracker Element" });
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: new ElementId[0], modified: new[] { tracker });

                Assert.Equal("modified 1 element without a category", guard.Changes.Describe(document, 50).Value<string>("summary"));
            }
        }

        [Fact]
        public void TheSummaryCountsEveryChangeAndCutsLongNameLists() {
            var app = new UIApplication();
            var document = new Document();
            var families = Enumerable.Range(1, 5).Select(i => Add(document, new Family { Name = "F" + i })).ToList();
            var systemTypes = Enumerable.Range(0, 2).Select(_ => Add(document, new WallType { Name = "Copy" })).ToList();
            var categories = new[] { "Walls", "Walls", "Doors", "Floors", "Roofs", "Roofs", "Roofs" };
            var modified = categories.Select(name => Add(document, new Element { Category = new Category { Name = name } }))
                .Concat(Enumerable.Range(0, 60).Select(_ => Add(document, new Element { Category = new Category { Name = "Grids" } })))
                .ToList();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: families.Concat(systemTypes).ToArray(), modified: modified);

                Assert.Equal(
                    "added 5 families (F1, F2, F3, +2 more) and 2 system types, modified 67 elements (Grids, Roofs, Walls, +2 more)",
                    guard.Changes.Describe(document, 2).Value<string>("summary"));
            }
        }

        [Fact]
        public void TheSummaryWithoutTheDocumentGivesCountsOnly() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: new[] { new ElementId(), new ElementId() }, modified: new[] { new ElementId() });

                Assert.Equal("added 2 elements, modified 1 element", guard.Changes.Summarize().Value<string>("summary"));
            }
        }

        [Fact]
        public void TypesAddedToAFamilyThatWasAlreadyLoadedAreNamedFamilyTypes() {
            var app = new UIApplication();
            var document = new Document();
            var symbol = Add(document, new FamilySymbol { Name = "900x2100" });
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");

                app.Application.Change(document, added: new[] { symbol });

                Assert.Equal("added 1 family type", guard.Changes.Describe(document, 50).Value<string>("summary"));
            }
        }

        private static ElementId Add(Document document, Element element) {
            var id = new ElementId();
            document.Elements[id] = element;
            return id;
        }
    }
}
