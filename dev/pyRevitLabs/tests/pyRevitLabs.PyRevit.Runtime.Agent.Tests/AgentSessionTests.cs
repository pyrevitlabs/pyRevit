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

        private void Arrive() {
            tracker.CheckOnArrival();
        }

        private void Dequeue(Func<object, bool> isTarget, string targetTitle) {
            tracker.CheckOnDequeue(isTarget, targetTitle);
        }

        private static string CodeOf(Action action) {
            return Assert.Throws<AgentException>(action).Code;
        }

        private static string MessageOf(Action action) {
            return Assert.Throws<AgentException>(action).Message;
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
                Assert.True(tracker.EndInRevit(Now));
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
            Arrive();
            Dequeue(_ => throw new InvalidOperationException("No session, so no document to compare."), "Tower.rvt");

            tracker.SetRequired(true);

            Assert.Equal("session_inactive", CodeOf(Arrive));
            Assert.Equal("session_inactive", CodeOf(() => Dequeue(_ => true, "Tower.rvt")));
        }

        [Fact]
        public void APausedSessionRefusesModelRequestsEvenWhenSessionsAreOptional() {
            StartOnDocument();
            tracker.Pause();

            Assert.Equal("paused_by_user", CodeOf(Arrive));
            Assert.Equal("paused_by_user", CodeOf(() => Dequeue(_ => true, "Tower.rvt")));
        }

        [Fact]
        public void AnActiveSessionPassesOnlyRequestsForItsOwnDocument() {
            StartOnDocument();
            object compared = null;

            Dequeue(bound => { compared = bound; return true; }, "Tower.rvt");
            var other = Assert.Throws<AgentException>(() => Dequeue(_ => false, "Annex.rvt"));

            Assert.Same(document, compared);
            Assert.Equal("document_not_in_session", other.Code);
            Assert.Contains("on 'Tower.rvt'", other.Message);
            Assert.Contains("'Annex.rvt' isn't part of it", other.Message);
        }

        [Fact]
        public void ARequestThatNamesNoDocumentPassesAnActiveSession() {
            StartOnDocument();

            Dequeue(_ => throw new InvalidOperationException("A request that names no document compares nothing."), null);
        }

        [Fact]
        public void WithoutASessionARequestForAnyDocumentPassesWhileSessionsAreOptional() {
            Dequeue(_ => false, "Annex.rvt");
        }

        [Fact]
        public void TheRefusalAfterTheDocumentClosedSaysSo() {
            tracker.SetRequired(true);
            StartOnDocument();
            tracker.EndIfBoundTo(document, AgentSessionEndReasons.DocumentClosed, Now);

            var refused = Assert.Throws<AgentException>(Arrive);

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
        public void ADeclinedRequestTellsTheAgentTheUserSaidNo() {
            tracker.SetRequired(true);
            tracker.Request("Renumber the doors", Now);

            Assert.True(tracker.Decline(Now));

            var status = tracker.Describe();
            Assert.True(IsNull(status["pending_request"]));
            Assert.Equal("Renumber the doors", status["declined_request"].Value<string>("reason"));
            var refused = Assert.Throws<AgentException>(Arrive);
            Assert.Equal("session_inactive", refused.Code);
            Assert.Contains("declined", refused.Message);
            Assert.False(tracker.Decline(Now));
        }

        [Fact]
        public void ANewRequestOrSessionClearsTheDecline() {
            tracker.Request("First", Now);
            tracker.Decline(Now);
            tracker.Request("Second", Now);
            Assert.True(IsNull(tracker.Describe()["declined_request"]));

            tracker.Decline(Now);
            StartOnDocument();
            Assert.True(IsNull(tracker.Describe()["declined_request"]));
        }

        [Fact]
        public void ChangedIsRaisedForEveryChangeAndNotForNoOps() {
            var raised = 0;
            tracker.Changed += () => raised++;

            tracker.SetRequired(false);
            tracker.End(AgentSessionEndReasons.EndedInRevit, Now);
            tracker.Decline(Now);
            Assert.Equal(0, raised);

            tracker.SetRequired(true);
            StartOnDocument();
            tracker.Pause();
            tracker.Resume();
            tracker.End(AgentSessionEndReasons.HostStopped, Now);
            tracker.Request(null, Now);
            tracker.Decline(Now);
            Assert.Equal(7, raised);
        }

        [Fact]
        public void MovingKeepsTheSessionAndRecordsItsDocuments() {
            var id = StartOnDocument();
            var annex = new object();

            var from = tracker.Move(annex, "Annex.rvt", Now);

            var status = tracker.Describe();
            Assert.Equal("Tower.rvt", from);
            Assert.Equal(id, tracker.SessionId);
            Assert.Same(annex, tracker.BoundDocument);
            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.Equal("Annex.rvt", status.Value<string>("document"));
            Assert.Equal(new[] { "Tower.rvt", "Annex.rvt" }, status["documents"].Values<string>());
            Assert.Equal(Now.ToString("o"), status.Value<string>("started"));
        }

        [Fact]
        public void AfterAMoveRequestsForTheDocumentTheSessionLeftAreRefused() {
            StartOnDocument();
            var annex = new object();

            tracker.Move(annex, "Annex.rvt", Now);

            Arrive();
            Dequeue(candidate => ReferenceEquals(candidate, annex), "Annex.rvt");
            var refused = Assert.Throws<AgentException>(() => Dequeue(candidate => ReferenceEquals(candidate, document), "Tower.rvt"));
            Assert.Equal("document_not_in_session", refused.Code);
            Assert.Contains("on 'Annex.rvt'", refused.Message);
        }

        [Fact]
        public void AMovedPausedSessionStaysPausedUntilTheUserResumes() {
            StartOnDocument();
            tracker.Pause();

            tracker.Move(new object(), "Annex.rvt", Now);

            Assert.Equal(AgentSessionState.Paused, tracker.State);
            Assert.Equal("paused_by_user", CodeOf(Arrive));
            tracker.Resume();
            Arrive();
        }

        [Fact]
        public void EachMoveReturnsTheDocumentItLeft() {
            StartOnDocument();
            tracker.Move(new object(), "Annex.rvt", Now);

            var from = tracker.Move(new object(), "Site.rvt", Now);

            Assert.Equal("Annex.rvt", from);
            Assert.Equal(new[] { "Tower.rvt", "Annex.rvt", "Site.rvt" }, tracker.Describe()["documents"].Values<string>());
        }

        [Fact]
        public void MovingIsRefusedWithoutASessionOrWhileARunExecutes() {
            Assert.Equal("session_inactive", CodeOf(() => tracker.Move(new object(), "Annex.rvt", Now)));
            StartOnDocument();

            using (tracker.BeginRun())
                Assert.Equal("session_locked", CodeOf(() => tracker.Move(new object(), "Annex.rvt", Now)));

            Assert.Same(document, tracker.BoundDocument);
        }

        [Fact]
        public void ANewSessionForgetsTheLastOnesMoves() {
            StartOnDocument();
            tracker.Move(new object(), "Annex.rvt", Now);
            tracker.End(AgentSessionEndReasons.EndedInRevit, Now);

            StartOnDocument();

            Arrive();
            Assert.Equal(new[] { "Tower.rvt" }, tracker.Describe()["documents"].Values<string>());
        }

        [Fact]
        public void APauseAnAgentAskedForIsReportedAsTheAgents() {
            StartOnDocument();

            tracker.PauseForAgent();

            var refused = Assert.Throws<AgentException>(Arrive);
            Assert.Equal("paused_by_agent", refused.Code);
            Assert.Contains("an agent paused it", refused.Message);
            Assert.Equal(AgentSessionPauseCauses.Agent, tracker.Describe().Value<string>("paused_cause"));
            tracker.Resume();
            Arrive();
            Assert.Equal("session_inactive", CodeOf(new AgentSessionTracker().PauseForAgent));
        }

        [Fact]
        public void APauseByRunCodeIsTheAgentsAndOneOutsideARunIsTheUsers() {
            StartOnDocument();

            using (tracker.BeginRun())
                tracker.Pause();

            var refused = Assert.Throws<AgentException>(Arrive);
            Assert.Equal("paused_by_agent", refused.Code);
            Assert.Contains("code in an agent run", refused.Message);
            tracker.Resume();
            tracker.Pause();
            Assert.Equal("paused_by_user", CodeOf(Arrive));
        }

        [Fact]
        public void APauseKeepsWhoseItWasWhenAnotherPauseFollows() {
            StartOnDocument();
            tracker.Pause();
            tracker.PauseForAgent();
            Assert.Equal("paused_by_user", CodeOf(Arrive));

            tracker.Resume();
            tracker.PauseByHost(AgentSessionPauseCauses.PanelHidden, "the agent panel in Revit was closed or hidden.");
            tracker.PauseForAgent();
            Assert.Equal("paused_by_host", CodeOf(Arrive));

            tracker.Resume();
            tracker.PauseForAgent();
            Assert.False(tracker.PauseByHost(AgentSessionPauseCauses.PanelHidden, "the agent panel in Revit was closed or hidden."));
            Assert.Equal("paused_by_agent", CodeOf(Arrive));
        }

        [Fact]
        public void ResumingClearsADeclineTheUserMadeWhileTheSessionWasPaused() {
            tracker.SetRequired(true);
            StartOnDocument();
            tracker.Pause();
            tracker.Request("Carry on with the doors", Now);
            tracker.Decline(Now);

            tracker.Resume();

            Assert.True(IsNull(tracker.Describe()["declined_request"]));
            tracker.EndInRevit(Now);
            Assert.DoesNotContain("declined", MessageOf(Arrive));
        }

        [Fact]
        public void WhileSessionsAreOptionalAnAgentCanNotEndTheSession() {
            Assert.False(tracker.EndForAgent(Now));
            StartOnDocument();

            Assert.Equal("session_locked", CodeOf(() => tracker.EndForAgent(Now)));
            Assert.Equal(AgentSessionState.Active, tracker.State);

            tracker.SetRequired(true);
            Assert.True(tracker.EndForAgent(Now));
            Assert.Equal(AgentSessionEndReasons.EndedByClient, tracker.Describe()["last_ended"].Value<string>("reason"));
        }

        [Fact]
        public void WhileSessionsAreOptionalRunCodeCanNotEndTheSession() {
            StartOnDocument();

            using (tracker.BeginRun())
                Assert.Equal("session_locked", CodeOf(() => tracker.EndInRevit(Now)));

            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.True(tracker.EndInRevit(Now));
            Assert.Equal(AgentSessionEndReasons.EndedInRevit, tracker.Describe()["last_ended"].Value<string>("reason"));
        }

        [Fact]
        public void SavingTheDocumentUnderAnotherNameRetitlesTheSession() {
            StartOnDocument();
            tracker.Move(new object(), "Annex.rvt", Now);

            Assert.True(tracker.Retitle("Annex v2.rvt"));

            var status = tracker.Describe();
            Assert.Equal("Annex v2.rvt", status.Value<string>("document"));
            Assert.Equal(new[] { "Tower.rvt", "Annex v2.rvt" }, status["documents"].Values<string>());
            Assert.Contains("on 'Annex v2.rvt'", MessageOf(() => Dequeue(_ => false, "Site.rvt")));
            Assert.False(tracker.Retitle("Annex v2.rvt"));
            Assert.False(tracker.Retitle(null));
        }

        [Fact]
        public void RetitlingWithoutASessionDoesNothing() {
            Assert.False(tracker.Retitle("Annex.rvt"));
        }

        [Fact]
        public void AMoveRaisesChanged() {
            StartOnDocument();
            var raised = 0;
            tracker.Changed += () => raised++;

            tracker.Move(new object(), "Annex.rvt", Now);

            Assert.Equal(1, raised);
        }

        [Fact]
        public void AHostPauseRefusesWithItsOwnCodeAndReasonUntilTheUserResumes() {
            StartOnDocument();

            Assert.True(tracker.PauseByHost(AgentSessionPauseCauses.OtherDocument, "the last run changed another open document ('Annex.rvt')."));

            var refused = Assert.Throws<AgentException>(Arrive);
            Assert.Equal("paused_by_host", refused.Code);
            Assert.Contains("'Annex.rvt'", refused.Message);
            Assert.Contains("only they can resume", refused.Message);
            Assert.Contains("Annex.rvt", tracker.Describe().Value<string>("paused_reason"));
            Assert.Equal("other_document", tracker.Describe().Value<string>("paused_cause"));

            tracker.Resume();
            Arrive();
            Assert.Null(tracker.Describe().Value<string>("paused_reason"));
            Assert.Null(tracker.Describe().Value<string>("paused_cause"));
        }

        [Fact]
        public void PausingAgainKeepsTheHostsReason() {
            StartOnDocument();
            tracker.PauseByHost(AgentSessionPauseCauses.OtherDocument, "of something.");
            var raised = 0;
            tracker.Changed += () => raised++;

            tracker.Pause();

            Assert.Equal("paused_by_host", CodeOf(Arrive));
            Assert.Equal(0, raised);
        }

        [Fact]
        public void TheFirstHostPauseKeepsItsReasonAndReplacesAUserPause() {
            StartOnDocument();
            tracker.Pause();

            Assert.True(tracker.PauseByHost(AgentSessionPauseCauses.OtherDocument, "the run changed 'Annex.rvt'."));
            Assert.False(tracker.PauseByHost(AgentSessionPauseCauses.PanelHidden, "the panel was hidden."));

            Assert.Equal("paused_by_host", CodeOf(Arrive));
            Assert.Equal("other_document", tracker.Describe().Value<string>("paused_cause"));
        }

        [Fact]
        public void AHostPauseWithoutASessionDoesNothing() {
            Assert.False(tracker.PauseByHost(AgentSessionPauseCauses.PanelHidden, "of something."));
            Assert.Equal(AgentSessionState.Inactive, tracker.State);
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
