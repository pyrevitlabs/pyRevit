using System;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentActivityTests {
        private static readonly DateTime Now = new DateTime(2026, 10, 5, 12, 0, 0, DateTimeKind.Utc);
        private readonly AgentActivity activity = new AgentActivity();

        [Fact]
        public void ARequestWaitsRunsAndBecomesTheLastOne() {
            var record = activity.Arrive("modify", "Renumber doors", Now);
            Assert.False(activity.Current.Started);

            activity.Start(record);
            Assert.True(activity.Current.Started);

            activity.Finish(record, "committed", Now.AddSeconds(3));
            Assert.Null(activity.Current);
            Assert.Equal("modify", activity.Last.Kind);
            Assert.Equal("Renumber doors", activity.Last.Title);
            Assert.Equal("committed", activity.Last.Outcome);
            Assert.Equal(Now.AddSeconds(3), activity.Last.FinishedUtc);
        }

        [Fact]
        public void FinishingAnOlderRequestKeepsTheNewerOneCurrent() {
            var older = activity.Arrive("query", null, Now);
            var newer = activity.Arrive("context", null, Now);

            activity.Start(older);
            activity.Finish(older, "ok", Now);

            Assert.Equal(newer.Id, activity.Current.Id);
            Assert.False(activity.Current.Started);
        }

        [Fact]
        public void FinishingClosesTheApprovalPrompt() {
            var record = activity.Arrive("modify", "Add walls", Now);
            activity.SetAwaitingApproval(true);

            activity.Finish(record, "rejected", Now);

            Assert.False(activity.AwaitingApproval);
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
            var record = activity.Arrive("query", null, Now);
            activity.Start(record);
            activity.Finish(record, "ok", Now);

            Assert.Equal(4, raised);
        }
    }
}
