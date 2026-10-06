using System;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentRunGuardTests {
        [Fact]
        public void OpenedDocumentsAreProtectedEvenWithAnEmptyPath() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var opened = new Document();
                app.Application.Open(opened);
                Assert.False(app.Application.Save(opened));
                Assert.False(app.Application.SaveAs(opened));
                app.Application.Change(opened);
                Assert.True(guard.ChangedOtherOpenDocument);
            }
        }

        [Fact]
        public void CreatedDocumentsCannotBeSaved() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var created = new Document();
                app.Application.Create(created);
                app.Application.Change(created);
                Assert.False(app.Application.SaveAs(created));
                created.PathName = "created.rfa";
                Assert.False(app.Application.Save(created));
                Assert.False(guard.ChangedOtherOpenDocument);
            }
        }

        [Fact]
        public void ExportAndSynchronizeOperationsAreBlocked() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                Assert.False(app.Application.ExportFile());
                Assert.False(app.Application.ExportView());
                Assert.False(app.Application.Synchronize(document));
                Assert.Equal("file_export", guard.Blocked[0].Value<string>("operation"));
                Assert.Equal("view_export", guard.Blocked[1].Value<string>("operation"));
                Assert.Equal("synchronize_with_central", guard.Blocked[2].Value<string>("operation"));
            }
        }

        [Fact]
        public void DeletedElementsAreRecordedAndTransientElementsAreExcluded() {
            var app = new UIApplication();
            var document = new Document();
            var transient = new ElementId();
            var deleted = new ElementId();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                app.Application.Change(document, added: new[] { transient });
                app.Application.Change(document, added: Array.Empty<ElementId>(), deleted: new[] { transient, deleted });
                var changes = guard.Changes.Summarize();
                Assert.Equal(0, changes.Value<int>("added_count"));
                Assert.Equal(1, changes.Value<int>("deleted_count"));
                Assert.Equal(0, changes.Value<int>("modified_count"));
            }
        }

        [Fact]
        public void ExistingDocumentsCannotBeSavedAndRollbackIsConfirmedOnlyAfterSuccess() {
            var app = new UIApplication();
            var existing = new Document();
            app.Application.Documents.Add(existing);
            var guard = new AgentRunGuard(app, null);
            guard.Arm("Test");
            app.Application.Change(existing);
            Assert.False(app.Application.Save(existing));
            Assert.False(app.Application.SaveAs(existing));
            Assert.False(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            guard.RollBack();
            guard.Dispose();
            Assert.True(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            Assert.False(guard.HasUnrevertedOtherDocumentChanges);
        }

        [Theory]
        [InlineData(true, false)]
        [InlineData(false, false)]
        [InlineData(true, true)]
        public void DiskDocumentsAreDiscardedOnlyAfterTheyActuallyClose(bool closeSucceeds, bool hasView) {
            var app = new UIApplication();
            var before = AgentDocuments.Snapshot(app.Application);
            var guard = new AgentRunGuard(app, null);
            guard.Arm("Test");
            var opened = new Document { PathName = "existing.rvt", CloseSucceeds = closeSucceeds, HasView = hasView };
            app.Application.Open(opened);
            app.Application.Change(opened);
            guard.Dispose();
            AgentDocuments.CloseLeftovers(app.Application, before);
            var description = guard.DescribeOtherDocuments()[0];
            Assert.False(description.Value<bool>("rolled_back"));
            Assert.Equal(closeSucceeds && !hasView, description.Value<bool>("discarded_on_close"));
            Assert.Equal(!closeSucceeds || hasView, guard.HasUnrevertedOtherDocumentChanges);
        }

        [Fact]
        public void FailedRollbackDoesNotPreventOtherDocumentsFromRollingBack() {
            var app = new UIApplication();
            var failing = new Document { ThrowOnRollback = true, ThrowOnDispose = true };
            var healthy = new Document();
            app.Application.Documents.Add(failing);
            app.Application.Documents.Add(healthy);
            var guard = new AgentRunGuard(app, null);
            guard.Arm("Test");
            app.Application.Change(failing);
            app.Application.Change(healthy);
            Assert.Throws<AggregateException>(guard.RollBack);
            guard.Dispose();
            Assert.False(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            Assert.True(guard.DescribeOtherDocuments()[1].Value<bool>("rolled_back"));
            Assert.True(guard.HasUnrevertedOtherDocumentChanges);
            Assert.Single(guard.CleanupFailures);
            Assert.True(app.Application.Save(failing));
        }

        [Fact]
        public void UnstartedGroupDoesNotClaimRollback() {
            var app = new UIApplication();
            var existing = new Document { StartStatus = TransactionStatus.Uninitialized };
            app.Application.Documents.Add(existing);
            var guard = new AgentRunGuard(app, null);
            guard.Arm("Test");
            app.Application.Change(existing);
            guard.Dispose();
            Assert.False(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            Assert.True(guard.HasUnrevertedOtherDocumentChanges);
        }
    }
}
