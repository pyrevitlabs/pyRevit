using System;
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

        private void Edit(long[] added = null, long[] modified = null, long[] deleted = null, string name = "Move", string operation = "commit") {
            awareness.RecordEdit(added ?? new long[0], modified ?? new long[0], deleted ?? new long[0], new[] { name }, operation);
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

            var edits = Peek()["edits"];

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
        public void UndoAndRedoAreCounted() {
            Edit(modified: new long[] { 1 }, name: "Move", operation: "undo");
            Edit(modified: new long[] { 1 }, name: "Move", operation: "redo");

            var edits = Peek()["edits"];

            Assert.Equal(1, edits.Value<int>("undone"));
            Assert.Equal(1, edits.Value<int>("redone"));
            Assert.Equal(new[] { "Move" }, edits["operations"].Values<string>());
        }

        [Fact]
        public void SampleIdsAndOperationsAreCapped() {
            Edit(added: Enumerable.Range(1, AgentAwareness.MaxSampleIds + 10).Select(id => (long)id).ToArray());
            for (var index = 0; index < AgentAwareness.MaxOperations + 5; index++)
                Edit(name: "Operation " + index);

            var edits = Peek()["edits"];

            Assert.Equal(AgentAwareness.MaxSampleIds + 10, edits.Value<int>("added"));
            Assert.Equal(AgentAwareness.MaxSampleIds, ((JArray)edits["added_ids"]).Count);
            Assert.Equal(AgentAwareness.MaxOperations, ((JArray)edits["operations"]).Count);
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
        public void AMoveIsReportedUntilCleared() {
            awareness.RecordMove("Tower.rvt", "Annex.rvt");

            var moved = Peek()["session_moved"];

            Assert.Equal("Tower.rvt", moved.Value<string>("from"));
            Assert.Equal("Annex.rvt", moved.Value<string>("to"));
            awareness.Clear();
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
