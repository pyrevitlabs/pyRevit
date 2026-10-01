using System;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace AgentRuntime.Tests {
    [TestClass]
    public sealed class AgentRunGuardTests {
        [TestMethod]
        public void OpenedDocumentsAreProtectedEvenWithAnEmptyPath() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var opened = new Document();
                app.Application.Open(opened);
                Assert.IsFalse(app.Application.Save(opened));
                Assert.IsFalse(app.Application.SaveAs(opened));
                app.Application.Change(opened);
                Assert.IsTrue(guard.ChangedOtherOpenDocument);
            }
        }

        [TestMethod]
        public void CreatedDocumentsCannotBeSaved() {
            var app = new UIApplication();
            using (var guard = new AgentRunGuard(app, null)) {
                guard.Arm("Test");
                var created = new Document();
                app.Application.Create(created);
                app.Application.Change(created);
                Assert.IsFalse(app.Application.SaveAs(created));
                created.PathName = "created.rfa";
                Assert.IsFalse(app.Application.Save(created));
                Assert.IsFalse(guard.ChangedOtherOpenDocument);
            }
        }

        [TestMethod]
        public void ExportAndSynchronizeOperationsAreBlocked() {
            var app = new UIApplication();
            var document = new Document();
            using (var guard = new AgentRunGuard(app, document)) {
                guard.Arm("Test");
                Assert.IsFalse(app.Application.ExportFile());
                Assert.IsFalse(app.Application.ExportView());
                Assert.IsFalse(app.Application.Synchronize(document));
                Assert.AreEqual("file_export", guard.Blocked[0].Value<string>("operation"));
                Assert.AreEqual("view_export", guard.Blocked[1].Value<string>("operation"));
                Assert.AreEqual("synchronize_with_central", guard.Blocked[2].Value<string>("operation"));
            }
        }

        [TestMethod]
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
                Assert.AreEqual(0, changes.Value<int>("added_count"));
                Assert.AreEqual(1, changes.Value<int>("deleted_count"));
                Assert.AreEqual(0, changes.Value<int>("modified_count"));
            }
        }

        [TestMethod]
        public void ExistingDocumentsCannotBeSavedAndRollbackIsConfirmedOnlyAfterSuccess() {
            var app = new UIApplication();
            var existing = new Document();
            app.Application.Documents.Add(existing);
            var guard = new AgentRunGuard(app, null);
            guard.Arm("Test");
            app.Application.Change(existing);
            Assert.IsFalse(app.Application.Save(existing));
            Assert.IsFalse(app.Application.SaveAs(existing));
            Assert.IsFalse(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            guard.RollBack();
            guard.Dispose();
            Assert.IsTrue(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            Assert.IsFalse(guard.HasUnrevertedOtherDocumentChanges);
        }

        [TestMethod]
        [DataRow(true, false)]
        [DataRow(false, false)]
        [DataRow(true, true)]
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
            Assert.IsFalse(description.Value<bool>("rolled_back"));
            Assert.AreEqual(closeSucceeds && !hasView, description.Value<bool>("discarded_on_close"));
            Assert.AreEqual(!closeSucceeds || hasView, guard.HasUnrevertedOtherDocumentChanges);
        }

        [TestMethod]
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
            Assert.ThrowsExactly<AggregateException>(guard.RollBack);
            guard.Dispose();
            Assert.IsFalse(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            Assert.IsTrue(guard.DescribeOtherDocuments()[1].Value<bool>("rolled_back"));
            Assert.IsTrue(guard.HasUnrevertedOtherDocumentChanges);
            Assert.AreEqual(1, guard.CleanupFailures.Count);
            Assert.IsTrue(app.Application.Save(failing));
        }

        [TestMethod]
        public void UnstartedGroupDoesNotClaimRollback() {
            var app = new UIApplication();
            var existing = new Document { StartStatus = TransactionStatus.Uninitialized };
            app.Application.Documents.Add(existing);
            var guard = new AgentRunGuard(app, null);
            guard.Arm("Test");
            app.Application.Change(existing);
            guard.Dispose();
            Assert.IsFalse(guard.DescribeOtherDocuments()[0].Value<bool>("rolled_back"));
            Assert.IsTrue(guard.HasUnrevertedOtherDocumentChanges);
        }
    }
}
