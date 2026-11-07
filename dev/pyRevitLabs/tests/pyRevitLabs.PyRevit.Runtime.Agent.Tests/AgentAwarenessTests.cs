using System;
using System.Collections.Generic;
using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentAwarenessTests {
        private readonly AgentAwareness awareness = new AgentAwareness();
        private int viewsDescribed;
        private int selectionsDescribed;

        private JObject Peek() {
            return awareness.Peek(
                () => { viewsDescribed++; return new JObject { ["name"] = "Level 2" }; },
                () => { selectionsDescribed++; return new JObject { ["count"] = 1 }; });
        }

        private void Edit(
            long[] added = null, long[] modified = null, long[] deleted = null, string name = "Move", string operation = "commit",
            string document = "doc-1", string title = "Tower.rvt") {
            awareness.RecordEdit(document, title, added ?? new long[0], modified ?? new long[0], deleted ?? new long[0], new[] { name }, operation);
        }

        private JToken Edits() {
            return Assert.Single(Peek()["edits"]);
        }

        private static HashSet<long> Ids(params long[] ids) {
            return new HashSet<long>(ids);
        }

        [Fact]
        public void NothingChangedMeansNoSummary() {
            Assert.Null(Peek());
            Assert.Equal(0, viewsDescribed + selectionsDescribed);
        }

        [Fact]
        public void EditsAreCountedWithSampleIdsAndOperationNames() {
            Edit(added: new long[] { 1, 2 }, name: "Wall");
            Edit(modified: new long[] { 3 }, name: "Move");

            var edits = Edits();

            Assert.Equal("doc-1", edits.Value<string>("document"));
            Assert.Equal("Tower.rvt", edits.Value<string>("document_title"));
            Assert.Equal(2, edits.Value<int>("added"));
            Assert.Equal(1, edits.Value<int>("modified"));
            Assert.Equal(0, edits.Value<int>("deleted"));
            Assert.Equal(new long[] { 1, 2 }, edits["added_ids"].Values<long>());
            Assert.Equal(new[] { "Wall", "Move" }, edits["operations"].Values<string>());
            Assert.Null(edits["undone"]);
        }

        [Fact]
        public void AnElementAddedThenDeletedLeavesNoTrace() {
            Edit(added: new long[] { 7 });
            Edit(modified: new long[] { 7 });
            Edit(deleted: new long[] { 7 });

            Assert.Null(Peek());
        }

        [Fact]
        public void AnElementThatComesBackAfterADeletionIsModifiedNotAddedAndDeleted() {
            Edit(deleted: new long[] { 7 }, name: "Delete");
            Edit(added: new long[] { 7 }, name: "Delete", operation: "undo");

            var edits = Edits();

            Assert.Equal(0, edits.Value<int>("added"));
            Assert.Equal(0, edits.Value<int>("deleted"));
            Assert.Equal(new long[] { 7 }, edits["modified_ids"].Values<long>());
        }

        [Fact]
        public void ARolledBackGroupCancelsTheEditsItsTransactionsMadeAndAddsNoNames() {
            Edit(added: new long[] { 7 }, name: "Step 1");
            Edit(deleted: new long[] { 7 }, name: "Tool group", operation: "rollback");

            Assert.Null(Peek());

            Edit(added: new long[] { 8 }, name: "Step 2");
            Edit(deleted: new long[] { 9 }, name: "Tool group", operation: "rollback");

            var edits = Edits();
            Assert.Equal(new long[] { 8 }, edits["added_ids"].Values<long>());
            Assert.Equal(new long[] { 9 }, edits["deleted_ids"].Values<long>());
            Assert.DoesNotContain("Tool group", edits["operations"].Values<string>());
            Assert.Null(edits["undone"]);
        }

        [Fact]
        public void UndoAndRedoAreCounted() {
            Edit(modified: new long[] { 1 }, name: "Move", operation: "undo");
            Edit(modified: new long[] { 1 }, name: "Move", operation: "redo");

            var edits = Edits();

            Assert.Equal(1, edits.Value<int>("undone"));
            Assert.Equal(1, edits.Value<int>("redone"));
            Assert.Equal(new[] { "Move" }, edits["operations"].Values<string>());
        }

        [Fact]
        public void SampleIdsAndOperationsAreCapped() {
            Edit(added: Enumerable.Range(1, AgentAwareness.MaxSampleIds + 10).Select(id => (long)id).ToArray());
            for (var index = 0; index < AgentAwareness.MaxOperations + 5; index++)
                Edit(name: "Operation " + index);

            var edits = Edits();

            Assert.Equal(AgentAwareness.MaxSampleIds + 10, edits.Value<int>("added"));
            Assert.Equal(AgentAwareness.MaxSampleIds, ((JArray)edits["added_ids"]).Count);
            Assert.Equal(AgentAwareness.MaxOperations, ((JArray)edits["operations"]).Count);
        }

        [Fact]
        public void EachDocumentsEditsAreReportedApartUnderItsKey() {
            Edit(added: new long[] { 5 }, name: "Wall");
            Edit(modified: new long[] { 5 }, name: "Move", document: "doc-2", title: "Annex.rvt");

            var edits = (JArray)Peek()["edits"];

            Assert.Equal(new[] { "doc-1", "doc-2" }, edits.Select(entry => entry.Value<string>("document")));
            Assert.Equal(new long[] { 5 }, edits[0]["added_ids"].Values<long>());
            Assert.Equal(0, edits[0].Value<int>("modified"));
            Assert.Equal(new long[] { 5 }, edits[1]["modified_ids"].Values<long>());
            Assert.Equal(new[] { "Move" }, edits[1]["operations"].Values<string>());
        }

        [Fact]
        public void ADocumentIsNamedByItsLatestTitle() {
            Edit(added: new long[] { 1 }, title: "Project1");
            Edit(added: new long[] { 2 }, title: "Tower.rvt");

            Assert.Equal("Tower.rvt", Edits().Value<string>("document_title"));
        }

        [Fact]
        public void ADocumentWhoseEditsCancelledOutIsLeftOut() {
            Edit(added: new long[] { 7 });
            Edit(deleted: new long[] { 7 });
            Edit(added: new long[] { 3 }, document: "doc-2", title: "Annex.rvt");

            Assert.Equal("doc-2", Edits().Value<string>("document"));
        }

        [Fact]
        public void ADocumentThatLeftTakesItsEditsWithIt() {
            Edit(added: new long[] { 1 });
            Edit(added: new long[] { 2 }, document: "doc-2", title: "Annex.rvt");
            Edit(added: new long[] { 3 }, document: "doc-3", title: "Site.rvt");

            awareness.RecordLeft("doc-2", "Annex.rvt");
            using (awareness.Suppress())
                awareness.RecordLeft("doc-3", "Site.rvt");

            Assert.Equal("doc-1", Edits().Value<string>("document"));
        }

        [Fact]
        public void AViewOfAnotherDocumentDiffersEvenWithTheSameId() {
            Assert.False(AgentAwareness.ViewDiffers("doc-1", 42, "doc-1", 42));
            Assert.True(AgentAwareness.ViewDiffers("doc-1", 42, "doc-1", 43));
            Assert.True(AgentAwareness.ViewDiffers("doc-1", 42, "doc-2", 42));
            Assert.True(AgentAwareness.ViewDiffers(null, null, "doc-1", 42));
        }

        [Fact]
        public void ASelectionInAnotherDocumentDiffersUnlessBothAreEmpty() {
            Assert.False(AgentAwareness.SelectionDiffers("doc-1", Ids(1, 2), "doc-1", Ids(2, 1)));
            Assert.True(AgentAwareness.SelectionDiffers("doc-1", Ids(1, 2), "doc-1", Ids(1)));
            Assert.True(AgentAwareness.SelectionDiffers("doc-1", Ids(1, 2), "doc-2", Ids(1, 2)));
            Assert.True(AgentAwareness.SelectionDiffers("doc-1", Ids(), "doc-2", Ids(5)));
            Assert.True(AgentAwareness.SelectionDiffers("doc-1", Ids(5), "doc-2", Ids()));
            Assert.False(AgentAwareness.SelectionDiffers("doc-1", Ids(), "doc-2", Ids()));
        }

        [Fact]
        public void ViewAndSelectionAreDescribedOnlyWhenTheyChanged() {
            awareness.RecordViewChange();

            var summary = Peek();

            Assert.Equal("Level 2", summary["active_view"].Value<string>("name"));
            Assert.Null(summary["selection"]);
            Assert.Null(summary["edits"]);
            Assert.Equal(1, viewsDescribed);
            Assert.Equal(0, selectionsDescribed);

            awareness.RecordSelectionChange();
            Assert.Equal(1, Peek()["selection"].Value<int>("count"));
        }

        [Fact]
        public void DocumentsThatJoinedOrLeftAreReportedUntilCleared() {
            awareness.RecordJoined("doc-2", "Annex.rvt");
            awareness.RecordLeft("doc-3", "Site.rvt");

            var documents = Peek()["documents"];

            Assert.Equal("doc-2", documents["joined"][0].Value<string>("key"));
            Assert.Equal("Annex.rvt", documents["joined"][0].Value<string>("title"));
            Assert.Equal("Site.rvt", documents["left"][0].Value<string>("title"));
            awareness.Clear();
            Assert.Null(Peek());
        }

        [Fact]
        public void ADocumentThatJoinedAndLeftBetweenCallsLeavesNoTrace() {
            awareness.RecordJoined("doc-2", "Annex.rvt");
            awareness.RecordLeft("doc-2", "Annex.rvt");

            Assert.Null(Peek());
        }

        [Fact]
        public void ADocumentThatLeftAndCameBackCountsAsJoined() {
            awareness.RecordLeft("doc-2", "Annex.rvt");
            awareness.RecordJoined("doc-2", "Annex.rvt");

            var documents = Peek()["documents"];

            Assert.Equal("doc-2", documents["joined"][0].Value<string>("key"));
            Assert.Null(documents["left"]);
        }

        [Fact]
        public void DocumentsJoiningWhileTheHostWorksAreNotReported() {
            using (awareness.Suppress()) {
                awareness.RecordJoined("doc-2", "Annex.rvt");
                awareness.RecordLeft("doc-3", "Site.rvt");
            }

            Assert.Null(Peek());
        }

        [Fact]
        public void PeekingKeepsTheSummaryUntilItIsCleared() {
            awareness.RecordSelectionChange();

            Assert.NotNull(Peek());
            Assert.NotNull(Peek());
            awareness.Clear();
            Assert.Null(Peek());
        }

        [Fact]
        public void NothingIsRecordedWhileSuppressed() {
            using (awareness.Suppress()) {
                Assert.True(awareness.IsSuppressed);
                Edit(added: new long[] { 1 });
                awareness.RecordViewChange();
                awareness.RecordSelectionChange();
            }

            Assert.False(awareness.IsSuppressed);
            Assert.Null(Peek());
        }

        [Fact]
        public void DisposingASuppressionTwiceEndsItOnce() {
            var outer = awareness.Suppress();
            var inner = awareness.Suppress();
            inner.Dispose();
            inner.Dispose();

            Assert.True(awareness.IsSuppressed);
            outer.Dispose();
            Assert.False(awareness.IsSuppressed);
        }
    }
}
