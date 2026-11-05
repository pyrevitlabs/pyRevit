using System;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
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
            }
        }
    }
}
