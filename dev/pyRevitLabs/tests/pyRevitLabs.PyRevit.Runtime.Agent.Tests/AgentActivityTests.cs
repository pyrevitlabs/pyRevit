using System;
using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentActivityTests {
        private static readonly DateTime Now = new DateTime(2026, 10, 5, 12, 0, 0, DateTimeKind.Utc);
        private static readonly (string, string) NoSession = (null, null);
        private readonly AgentActivity activity = new AgentActivity();

        private AgentRequestRecord Arrive(string kind, string title = null) {
            return activity.Arrive(kind, title, null, NoSession, Now);
        }

        [Fact]
        public void ARequestWaitsRunsAndBecomesTheLastOne() {
            var record = activity.Arrive("modify", "Renumber doors", "Marks skip", ("s1", "Tower.rvt"), Now);
            Assert.False(activity.Current.Started);

            activity.Start(record, Now.AddSeconds(1));
            Assert.True(activity.Current.Started);

            var details = new JObject { ["run_id"] = "abc" };
            activity.Finish(record, "committed", Now.AddSeconds(3), details);
            var last = activity.Last;
            Assert.Null(activity.Current);
            Assert.Equal("modify", last.Kind);
            Assert.Equal("Renumber doors", last.Title);
            Assert.Equal("Marks skip", last.Reason);
            Assert.Equal("s1", last.SessionId);
            Assert.Equal("Tower.rvt", last.SessionDocument);
            Assert.Equal("committed", last.Outcome);
            Assert.Equal(Now.AddSeconds(1), last.StartedUtc);
            Assert.Equal(Now.AddSeconds(3), last.FinishedUtc);
            Assert.Same(details, last.Details);
        }

        [Fact]
        public void FinishingAnOlderRequestKeepsTheNewerOneCurrent() {
            var older = Arrive("query");
            var newer = Arrive("context");

            activity.Start(older, Now);
            activity.Finish(older, "ok", Now);

            Assert.Equal(newer.Id, activity.Current.Id);
            Assert.False(activity.Current.Started);
        }

        [Fact]
        public void ARefusedRequestThatNeverStartedFinishesAtOnce() {
            var record = Arrive("query");

            activity.Finish(record, "session_inactive", Now.AddSeconds(2));

            Assert.Equal(Now.AddSeconds(2), activity.Last.StartedUtc);
            Assert.Equal("session_inactive", activity.Last.Outcome);
        }

        [Fact]
        public void FinishingClosesTheApprovalPrompt() {
            var record = Arrive("modify", "Add walls");
            activity.Start(record, Now);
            activity.SetAwaitingApproval(true);

            activity.Finish(record, "rejected", Now);

            Assert.False(activity.AwaitingApproval);
        }

        [Fact]
        public void ARequestInsideAnotherLeavesTheOuterRecordAndPromptAlone() {
            var outer = Arrive("modify", "Outer");
            activity.Start(outer, Now.AddSeconds(1));
            activity.SetAwaitingApproval(true);

            var refused = Arrive("query", "Refused");
            activity.Finish(refused, "revit_busy", Now.AddSeconds(2));
            Assert.True(activity.AwaitingApproval);

            var inner = Arrive("query", "Inner");
            activity.Start(inner, Now.AddSeconds(3));
            Assert.Equal(inner.Id, activity.Current.Id);
            activity.Finish(inner, "ok", Now.AddSeconds(4));

            Assert.Equal(outer.Id, activity.Current.Id);
            Assert.True(activity.Current.Started);
            activity.Finish(outer, "committed", Now.AddSeconds(9));
            Assert.Null(activity.Current);
            Assert.Equal(Now.AddSeconds(1), activity.Last.StartedUtc);
        }

        [Fact]
        public void TheHistoryKeepsFinishedRequestsOldestFirst() {
            var first = Arrive("query", "First");
            activity.Finish(first, "ok", Now);
            var second = Arrive("modify", "Second");
            activity.Finish(second, "committed", Now);

            Assert.Equal(new[] { "First", "Second" }, activity.History.Select(record => record.Title));
        }

        [Fact]
        public void TheHistoryDropsTheOldestRequestsPastItsLimit() {
            for (var index = 0; index < AgentActivity.MaxHistory + 5; index++)
                activity.Finish(Arrive("query", "Run " + index), "ok", Now);

            var history = activity.History;
            Assert.Equal(AgentActivity.MaxHistory, history.Count);
            Assert.Equal("Run 5", history.First().Title);
        }

        [Fact]
        public void ALookupGoesIntoTheHistoryButIsNeverTheLastRequest() {
            activity.Finish(Arrive("modify", "Add walls"), "committed", Now);

            activity.RecordLookup("lookup", "Wall.Create", ("s1", "Tower.rvt"), "ok", Now);

            var lookup = activity.History.Last();
            Assert.True(lookup.IsLookup);
            Assert.Equal("Wall.Create", lookup.Title);
            Assert.Equal("s1", lookup.SessionId);
            Assert.Equal("Add walls", activity.Last.Title);
            Assert.Null(activity.Current);
        }

        [Fact]
        public void AMoveGoesIntoTheHistoryAsAMarkerButIsNeverTheLastRequest() {
            var record = Arrive("query", "Before");
            activity.Finish(record, "ok", Now);

            activity.RecordMove("Tower.rvt", ("s1", "Annex.rvt"), Now.AddSeconds(1));

            var move = activity.History.Last();
            Assert.Equal("move", move.Kind);
            Assert.Equal("Tower.rvt", move.Title);
            Assert.Equal("Annex.rvt", move.SessionDocument);
            Assert.Equal("moved", move.Outcome);
            Assert.False(move.IsLookup);
            Assert.Equal("Before", activity.Last.Title);
        }

        [Fact]
        public void ContextAndLookupRequestsAreLookups() {
            Assert.True(Arrive("context").IsLookup);
            Assert.True(Arrive("lookup").IsLookup);
            Assert.False(Arrive("query").IsLookup);
            Assert.False(Arrive("show").IsLookup);
        }

        [Fact]
        public void TheClientNameIsTrimmedCutAndNeverBlanked() {
            activity.NoteClient("  Claude Code  ");
            activity.NoteClient("   ");
            activity.NoteClient(null);
            Assert.Equal("Claude Code", activity.Client);

            activity.NoteClient(new string('x', AgentActivity.MaxClientLength + 20));
            Assert.Equal(AgentActivity.MaxClientLength, activity.Client.Length);
        }

        [Fact]
        public void ChangedIsRaisedForChangesOnly() {
            var raised = 0;
            activity.Changed += () => raised++;

            activity.NoteClient("Codex");
            activity.NoteClient("Codex");
            activity.SetAwaitingApproval(false);
            var record = Arrive("query");
            activity.Start(record, Now);
            activity.Finish(record, "ok", Now);
            activity.RecordLookup("lookup", "Wall", NoSession, "ok", Now);

            Assert.Equal(5, raised);
        }
    }
}
