using System;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentSessionTests {
        private static readonly DateTime Now = new DateTime(2026, 10, 5, 12, 0, 0, DateTimeKind.Utc);
        private readonly object document = new object();
        private readonly AgentSessionTracker tracker = new AgentSessionTracker();

        private string StartOnDocument() {
            return tracker.Start(document, "Tower.rvt", Now);
        }

        private static string CodeOf(Action action) {
            return Assert.Throws<AgentException>(action).Code;
        }

        private static bool IsNull(JToken token) {
            return token == null || token.Type == JTokenType.Null;
        }

        [Fact]
        public void StartingBindsAnActiveSessionToTheDocument() {
            var id = StartOnDocument();

            var status = tracker.Describe();
            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.Same(document, tracker.BoundDocument);
            Assert.Equal("active", status.Value<string>("state"));
            Assert.Equal(id, status.Value<string>("id"));
            Assert.Equal("Tower.rvt", status.Value<string>("document"));
            Assert.Equal(Now.ToString("o"), status.Value<string>("started"));
        }

        [Fact]
        public void AnInactiveSessionDescribesNoDocument() {
            var status = tracker.Describe();

            Assert.Equal("inactive", status.Value<string>("state"));
            Assert.Null(status.Value<string>("id"));
            Assert.Null(status.Value<string>("document"));
            Assert.Null(status.Value<string>("started"));
            Assert.False(status.Value<bool>("required"));
        }

        [Fact]
        public void ASecondSessionCanNotStartWhileOneIsActiveOrPaused() {
            StartOnDocument();
            Assert.Equal("session_active", CodeOf(() => tracker.Start(new object(), "Other.rvt", Now)));

            tracker.Pause();
            Assert.Equal("session_active", CodeOf(() => tracker.Start(new object(), "Other.rvt", Now)));
        }

        [Fact]
        public void PauseAndResumeMoveBetweenActiveAndPaused() {
            StartOnDocument();

            tracker.Pause();
            Assert.Equal(AgentSessionState.Paused, tracker.State);
            tracker.Resume();
            Assert.Equal(AgentSessionState.Active, tracker.State);
        }

        [Fact]
        public void PausingOrResumingWithoutASessionIsRefused() {
            Assert.Equal("session_inactive", CodeOf(tracker.Pause));
            Assert.Equal("session_inactive", CodeOf(tracker.Resume));
        }

        [Fact]
        public void EndingRemembersWhyAndReturnsToInactive() {
            var id = StartOnDocument();

            Assert.True(tracker.End(AgentSessionEndReasons.EndedByClient, Now));

            var ended = tracker.Describe()["last_ended"];
            Assert.Equal(AgentSessionState.Inactive, tracker.State);
            Assert.Null(tracker.BoundDocument);
            Assert.Equal(id, ended.Value<string>("id"));
            Assert.Equal("Tower.rvt", ended.Value<string>("document"));
            Assert.Equal(AgentSessionEndReasons.EndedByClient, ended.Value<string>("reason"));
            Assert.False(tracker.End(AgentSessionEndReasons.EndedByClient, Now));
        }

        [Fact]
        public void ALateCloseNoticeCanNotEndANewerSession() {
            StartOnDocument();
            tracker.End(AgentSessionEndReasons.EndedInRevit, Now);
            var newer = new object();
            tracker.Start(newer, "Newer.rvt", Now);

            Assert.False(tracker.EndIfBoundTo(document, AgentSessionEndReasons.DocumentClosed, Now));
            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.True(tracker.EndIfBoundTo(newer, AgentSessionEndReasons.DocumentClosed, Now));
        }

        [Fact]
        public void NothingLoosensTheGateWhileARunExecutes() {
            tracker.SetRequired(true);
            StartOnDocument();
            tracker.Pause();

            using (tracker.BeginRun()) {
                Assert.Equal("session_locked", CodeOf(tracker.Resume));
                Assert.Equal("session_locked", CodeOf(() => tracker.SetRequired(false)));
                tracker.End(AgentSessionEndReasons.EndedInRevit, Now);
                Assert.Equal("session_locked", CodeOf(() => tracker.Start(document, "Tower.rvt", Now)));
            }

            Assert.True(tracker.Required);
            Assert.Equal(AgentSessionState.Inactive, tracker.State);
            StartOnDocument();
            tracker.SetRequired(false);
        }

        [Fact]
        public void PausingAndRequiringASessionStillWorkWhileARunExecutes() {
            StartOnDocument();

            using (tracker.BeginRun()) {
                tracker.Pause();
                tracker.SetRequired(true);
            }

            Assert.Equal(AgentSessionState.Paused, tracker.State);
            Assert.True(tracker.Required);
        }

        [Fact]
        public void DisposingARunScopeTwiceCountsTheRunOnce() {
            var outer = tracker.BeginRun();
            var inner = tracker.BeginRun();
            inner.Dispose();
            inner.Dispose();

            Assert.Equal("session_locked", CodeOf(() => StartOnDocument()));
            outer.Dispose();
            StartOnDocument();
        }

        [Fact]
        public void WithoutASessionModelRequestsPassOnlyWhileSessionsAreOptional() {
            tracker.CheckOnArrival();
            tracker.CheckOnDequeue(_ => throw new InvalidOperationException("No session, so no document to compare."), "Tower.rvt");

            tracker.SetRequired(true);

            Assert.Equal("session_inactive", CodeOf(tracker.CheckOnArrival));
            Assert.Equal("session_inactive", CodeOf(() => tracker.CheckOnDequeue(_ => true, "Tower.rvt")));
        }

        [Fact]
        public void APausedSessionRefusesModelRequestsEvenWhenSessionsAreOptional() {
            StartOnDocument();
            tracker.Pause();

            Assert.Equal("paused_by_user", CodeOf(tracker.CheckOnArrival));
            Assert.Equal("paused_by_user", CodeOf(() => tracker.CheckOnDequeue(_ => true, "Tower.rvt")));
        }

        [Fact]
        public void AnActiveSessionPassesOnlyWhileItsDocumentIsActive() {
            StartOnDocument();
            object compared = null;

            tracker.CheckOnDequeue(bound => { compared = bound; return true; }, "Tower.rvt");
            var otherActive = Assert.Throws<AgentException>(() => tracker.CheckOnDequeue(_ => false, "Annex.rvt"));
            var noneActive = Assert.Throws<AgentException>(() => tracker.CheckOnDequeue(_ => false, null));

            Assert.Same(document, compared);
            Assert.Equal("wrong_document", otherActive.Code);
            Assert.Contains("'Tower.rvt'", otherActive.Message);
            Assert.Contains("'Annex.rvt' is the active document", otherActive.Message);
            Assert.Contains("no document is active", noneActive.Message);
        }

        [Fact]
        public void TheRefusalAfterTheDocumentClosedSaysSo() {
            tracker.SetRequired(true);
            StartOnDocument();
            tracker.EndIfBoundTo(document, AgentSessionEndReasons.DocumentClosed, Now);

            var refused = Assert.Throws<AgentException>(tracker.CheckOnArrival);

            Assert.Equal("session_inactive", refused.Code);
            Assert.Contains("'Tower.rvt' was closed", refused.Message);
            Assert.Contains("request_session", refused.Message);
        }

        [Fact]
        public void ARequestIsRecordedUntilASessionStarts() {
            Assert.True(tracker.Request("  Renumber the doors on Level 2  ", Now));

            var pending = tracker.Describe()["pending_request"];
            Assert.Equal("Renumber the doors on Level 2", pending.Value<string>("reason"));
            Assert.Equal(Now.ToString("o"), pending.Value<string>("requested"));

            StartOnDocument();
            Assert.True(IsNull(tracker.Describe()["pending_request"]));
            Assert.False(tracker.Request("Again", Now));
        }

        [Fact]
        public void ARequestWhilePausedIsClearedByResuming() {
            StartOnDocument();
            tracker.Pause();

            Assert.True(tracker.Request("   ", Now));
            Assert.True(IsNull(tracker.Describe()["pending_request"]["reason"]));
            tracker.Resume();
            Assert.True(IsNull(tracker.Describe()["pending_request"]));
        }

        [Fact]
        public void ARequestReasonOverTheLimitIsRefused() {
            var reason = new string('x', AgentSessionTracker.MaxReasonLength + 1);

            Assert.Equal("invalid_params", CodeOf(() => tracker.Request(reason, Now)));
            Assert.True(tracker.Request(new string('x', AgentSessionTracker.MaxReasonLength), Now));
        }

        [Fact]
        public void RunsTheConfigPolicyAllowsPassThePermissionCheck() {
            AgentPermissions.CheckRun(AgentRunMode.Modify, AgentPolicy.Ask);
            AgentPermissions.CheckRun(AgentRunMode.Modify, AgentPolicy.Auto);
            AgentPermissions.CheckRun(AgentRunMode.Query, AgentPolicy.ReadOnly);
            AgentPermissions.CheckRun(AgentRunMode.DryRun, AgentPolicy.ReadOnly);
        }

        [Fact]
        public void AModifyRunUnderReadOnlyFailsThePermissionCheck() {
            Assert.Equal("policy_readonly", CodeOf(() => AgentPermissions.CheckRun(AgentRunMode.Modify, AgentPolicy.ReadOnly)));
        }
    }
}
