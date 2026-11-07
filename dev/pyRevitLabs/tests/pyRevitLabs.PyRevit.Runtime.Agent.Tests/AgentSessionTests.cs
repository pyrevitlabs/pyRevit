using System;
using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentSessionTests {
        private static readonly DateTime Now = new DateTime(2026, 10, 5, 12, 0, 0, DateTimeKind.Utc);
        private readonly object document = new object();
        private readonly object annex = new object();
        private readonly AgentSessionTracker tracker = new AgentSessionTracker();

        private static AgentSessionDocument Doc(object reference, string key, string title) {
            return new AgentSessionDocument(reference, key, title);
        }

        private AgentSessionDocument Tower => Doc(document, "doc-1", "Tower.rvt");
        private AgentSessionDocument Annex => Doc(annex, "doc-2", "Annex.rvt");

        private string StartOnDocument() {
            return tracker.Start(new[] { Tower }, Now);
        }

        private bool StartAutomatically() {
            tracker.SetStartMode(AgentSessionStart.Auto);
            return tracker.StartAutomatically(new[] { Tower, Annex }, Now);
        }

        private void Arrive() {
            tracker.CheckOnArrival();
        }

        private void Dequeue(Func<object, bool> isTarget, string targetTitle) {
            tracker.CheckOnDequeue(isTarget, targetTitle);
        }

        private static Func<object, bool> Is(object reference) {
            return candidate => ReferenceEquals(candidate, reference);
        }

        private static string[] Titles(JObject status) {
            return status["documents"].Select(entry => entry.Value<string>("title")).ToArray();
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
        public void StartingOpensAnActiveSessionOnTheChosenDocuments() {
            var id = tracker.Start(new[] { Tower, Annex }, Now);

            var status = tracker.Describe();
            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.Equal("active", status.Value<string>("state"));
            Assert.Equal("user", status.Value<string>("start"));
            Assert.False(status.Value<bool>("automatic"));
            Assert.Equal(id, status.Value<string>("id"));
            Assert.Equal(new[] { "doc-1", "doc-2" }, status["documents"].Select(entry => entry.Value<string>("key")));
            Assert.Equal(new[] { "Tower.rvt", "Annex.rvt" }, Titles(status));
            Assert.Equal(Now.ToString("o"), status.Value<string>("started"));
            Assert.Equal((id, "Tower.rvt, Annex.rvt"), tracker.CurrentSession);
        }

        [Fact]
        public void ASessionNeedsADocument() {
            Assert.Throws<ArgumentException>(() => tracker.Start(new AgentSessionDocument[0], Now));
            Assert.Equal(AgentSessionState.Inactive, tracker.State);
        }

        [Fact]
        public void AnInactiveSessionDescribesNoDocument() {
            var status = tracker.Describe();

            Assert.Equal("inactive", status.Value<string>("state"));
            Assert.Equal("user", status.Value<string>("start"));
            Assert.False(status.Value<bool>("automatic"));
            Assert.Null(status.Value<string>("id"));
            Assert.True(IsNull(status["documents"]));
            Assert.Null(status.Value<string>("started"));
            Assert.Empty(tracker.Documents);
        }

        [Fact]
        public void ASecondSessionCanNotStartWhileOneIsActiveOrPaused() {
            StartOnDocument();
            Assert.Equal("session_active", CodeOf(() => tracker.Start(new[] { Annex }, Now)));

            tracker.Pause();
            Assert.Equal("session_active", CodeOf(() => tracker.Start(new[] { Annex }, Now)));
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
            Assert.Empty(tracker.Documents);
            Assert.Equal(id, ended.Value<string>("id"));
            Assert.Equal("Tower.rvt", ended.Value<string>("document"));
            Assert.Equal(AgentSessionEndReasons.EndedByClient, ended.Value<string>("reason"));
            Assert.False(tracker.End(AgentSessionEndReasons.EndedByClient, Now));
        }

        [Fact]
        public void NothingLoosensTheGateWhileARunExecutes() {
            StartOnDocument();
            tracker.Pause();

            using (tracker.BeginRun()) {
                Assert.Equal("session_locked", CodeOf(tracker.Resume));
                Assert.Equal("session_locked", CodeOf(() => tracker.SetStartMode(AgentSessionStart.Auto)));
                Assert.Equal("session_locked", CodeOf(() => tracker.AddDocument(Annex, byUser: true)));
                Assert.True(tracker.EndInRevit(Now));
                Assert.Equal("session_locked", CodeOf(() => StartOnDocument()));
            }

            Assert.Equal(AgentSessionStart.User, tracker.StartMode);
            Assert.Equal(AgentSessionState.Inactive, tracker.State);
        }

        [Fact]
        public void PausingAndTighteningStillWorkWhileARunExecutes() {
            tracker.SetStartMode(AgentSessionStart.Auto);
            StartOnDocument();

            using (tracker.BeginRun()) {
                Assert.True(tracker.AddDocument(Annex, byUser: false));
                tracker.Pause();
                tracker.SetStartMode(AgentSessionStart.User);
            }

            Assert.Equal(AgentSessionState.Paused, tracker.State);
            Assert.Equal(AgentSessionStart.User, tracker.StartMode);
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
        public void WithoutASessionModelRequestsPassOnlyWhileSessionsStartAutomatically() {
            Assert.Equal("session_inactive", CodeOf(Arrive));
            Assert.Equal("session_inactive", CodeOf(() => Dequeue(_ => true, "Tower.rvt")));

            tracker.SetStartMode(AgentSessionStart.Auto);

            Arrive();
            Dequeue(_ => throw new InvalidOperationException("No session, so no document to compare."), "Tower.rvt");
        }

        [Fact]
        public void APausedSessionRefusesModelRequests() {
            StartOnDocument();
            tracker.Pause();

            Assert.Equal("paused_by_user", CodeOf(Arrive));
            Assert.Equal("paused_by_user", CodeOf(() => Dequeue(_ => true, "Tower.rvt")));
        }

        [Fact]
        public void AnActiveSessionPassesOnlyRequestsForItsDocuments() {
            tracker.Start(new[] { Tower, Annex }, Now);

            Dequeue(Is(annex), "Annex.rvt");
            var other = Assert.Throws<AgentException>(() => Dequeue(_ => false, "Site.rvt"));

            Assert.Equal("document_not_in_session", other.Code);
            Assert.Contains("covers 'Tower.rvt', 'Annex.rvt'", other.Message);
            Assert.Contains("'Site.rvt' isn't part of it", other.Message);
            Assert.Contains("add 'Site.rvt'", other.Message);
        }

        [Fact]
        public void ARequestThatNamesNoDocumentPassesAnActiveSession() {
            StartOnDocument();

            Dequeue(_ => throw new InvalidOperationException("A request that names no document compares nothing."), null);
        }

        [Fact]
        public void TheSessionContainsOnlyItsDocumentsUnlessItStartedAutomatically() {
            Assert.False(tracker.Contains(_ => true));
            StartOnDocument();
            Assert.True(tracker.Contains(Is(document)));
            Assert.False(tracker.Contains(Is(annex)));

            tracker.End(AgentSessionEndReasons.EndedInRevit, Now);
            StartAutomatically();
            Assert.True(tracker.Contains(_ => false));
        }

        [Fact]
        public void AnAutomaticSessionCoversEveryOpenDocumentAndPassesAnyOfThem() {
            Assert.True(StartAutomatically());

            var status = tracker.Describe();
            Assert.Equal("auto", status.Value<string>("start"));
            Assert.True(status.Value<bool>("automatic"));
            Assert.True(tracker.StartedAutomatically);
            Assert.Equal(new[] { "Tower.rvt", "Annex.rvt" }, Titles(status));
            Dequeue(_ => false, "Site.rvt");
        }

        [Fact]
        public void SessionsStartAutomaticallyOnlyWhenSetToAndNoneIsOpen() {
            Assert.False(tracker.StartAutomatically(new[] { Tower }, Now));
            Assert.Equal(AgentSessionState.Inactive, tracker.State);

            Assert.True(StartAutomatically());
            var id = tracker.SessionId;
            Assert.False(tracker.StartAutomatically(new[] { Tower }, Now));
            Assert.Equal(id, tracker.SessionId);
        }

        [Fact]
        public void AnAutomaticSessionStartsWithNoDocumentOpenAndEndsWithTheLastOneThatJoined() {
            tracker.SetStartMode(AgentSessionStart.Auto);
            Assert.True(tracker.StartAutomatically(new AgentSessionDocument[0], Now));
            Dequeue(_ => false, null);

            Assert.True(tracker.AddDocument(Tower, byUser: false));
            Assert.NotNull(tracker.RemoveDocument(Is(document), AgentSessionEndReasons.DocumentClosed, Now));

            Assert.Equal(AgentSessionState.Inactive, tracker.State);
            Assert.Equal("document_closed", tracker.Describe()["last_ended"].Value<string>("reason"));
        }

        [Fact]
        public void APausedAutomaticSessionCanNotBeBypassedByStartingAnother() {
            StartAutomatically();
            tracker.Pause();

            Assert.False(tracker.StartAutomatically(new[] { Tower }, Now));
            Assert.Equal("session_locked", CodeOf(() => tracker.EndForAgent(Now)));
            Assert.Equal("session_locked", CodeOf(() => tracker.EndInRevit(Now)));
            Assert.Equal(AgentSessionState.Paused, tracker.State);
            Assert.Equal("paused_by_user", CodeOf(Arrive));
        }

        [Fact]
        public void WhileSessionsStartAutomaticallyOnlyTheHostEndsOne() {
            StartAutomatically();

            Assert.Contains("Pause it", MessageOf(() => tracker.EndInRevit(Now)));
            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.True(tracker.End(AgentSessionEndReasons.HostStopped, Now));
        }

        [Fact]
        public void AnAgentCanEndASessionTheUserStarted() {
            Assert.False(tracker.EndForAgent(Now));
            StartOnDocument();

            Assert.True(tracker.EndForAgent(Now));
            Assert.Equal(AgentSessionEndReasons.EndedByClient, tracker.Describe()["last_ended"].Value<string>("reason"));
        }

        [Fact]
        public void AddingADocumentJoinsTheOpenSession() {
            StartOnDocument();

            Assert.True(tracker.AddDocument(Annex, byUser: true));

            Assert.Equal(new[] { "Tower.rvt", "Annex.rvt" }, Titles(tracker.Describe()));
            Dequeue(Is(annex), "Annex.rvt");
            Assert.False(tracker.AddDocument(Doc(new object(), "doc-2", "Annex copy.rvt"), byUser: true));
            Assert.Equal(2, tracker.Documents.Count);
        }

        [Fact]
        public void AddingADocumentWithoutASessionIsRefused() {
            Assert.Equal("session_inactive", CodeOf(() => tracker.AddDocument(Annex, byUser: false)));
        }

        [Fact]
        public void RemovingADocumentKeepsTheSessionUntilItsLastOne() {
            tracker.Start(new[] { Tower, Annex }, Now);

            var removed = tracker.RemoveDocument(Is(annex), AgentSessionEndReasons.DocumentClosed, Now);

            Assert.Equal("doc-2", removed.Key);
            Assert.Equal(AgentSessionState.Active, tracker.State);
            Assert.Equal(new[] { "Tower.rvt" }, Titles(tracker.Describe()));
            Assert.Null(tracker.RemoveDocument(Is(annex), AgentSessionEndReasons.DocumentClosed, Now));

            Assert.NotNull(tracker.RemoveDocument(Is(document), AgentSessionEndReasons.DocumentClosed, Now));
            Assert.Equal(AgentSessionState.Inactive, tracker.State);
            Assert.Equal(AgentSessionEndReasons.DocumentClosed, tracker.Describe()["last_ended"].Value<string>("reason"));
        }

        [Fact]
        public void ALateCloseNoticeCanNotEndANewerSession() {
            StartOnDocument();
            tracker.End(AgentSessionEndReasons.EndedInRevit, Now);
            tracker.Start(new[] { Annex }, Now);

            Assert.Null(tracker.RemoveDocument(Is(document), AgentSessionEndReasons.DocumentClosed, Now));
            Assert.Equal(AgentSessionState.Active, tracker.State);
        }

        [Fact]
        public void TheRefusalAfterTheLastDocumentClosedSaysSo() {
            StartOnDocument();
            tracker.RemoveDocument(Is(document), AgentSessionEndReasons.DocumentClosed, Now);

            var refused = Assert.Throws<AgentException>(Arrive);

            Assert.Equal("session_inactive", refused.Code);
            Assert.Contains("last document 'Tower.rvt' was closed", refused.Message);
            Assert.Contains("request_session", refused.Message);
        }

        [Fact]
        public void SavingADocumentUnderAnotherNameRetitlesIt() {
            tracker.Start(new[] { Tower, Annex }, Now);

            Assert.True(tracker.Retitle(Is(annex), "Annex v2.rvt"));

            Assert.Equal(new[] { "Tower.rvt", "Annex v2.rvt" }, Titles(tracker.Describe()));
            Assert.Contains("'Annex v2.rvt'", MessageOf(() => Dequeue(_ => false, "Site.rvt")));
            Assert.False(tracker.Retitle(Is(annex), "Annex v2.rvt"));
            Assert.False(tracker.Retitle(Is(annex), null));
            Assert.False(tracker.Retitle(_ => false, "Site.rvt"));
        }

        [Fact]
        public void RetitlingWithoutASessionDoesNothing() {
            Assert.False(tracker.Retitle(_ => true, "Annex.rvt"));
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
        public void NothingIsRequestedWhileTheNextRequestWouldStartASession() {
            tracker.SetStartMode(AgentSessionStart.Auto);

            Assert.False(tracker.Request("Renumber the doors", Now));
            Assert.True(IsNull(tracker.Describe()["pending_request"]));
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
        public void ResumingClearsADeclineTheUserMadeWhileTheSessionWasPaused() {
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
        public void ChangedIsRaisedForEveryChangeAndNotForNoOps() {
            var raised = 0;
            tracker.Changed += () => raised++;

            tracker.SetStartMode(AgentSessionStart.User);
            tracker.End(AgentSessionEndReasons.EndedInRevit, Now);
            tracker.Decline(Now);
            Assert.Null(tracker.RemoveDocument(_ => true, AgentSessionEndReasons.DocumentClosed, Now));
            Assert.Equal(0, raised);

            StartOnDocument();
            tracker.AddDocument(Annex, byUser: true);
            tracker.AddDocument(Annex, byUser: true);
            tracker.Retitle(Is(annex), "Annex v2.rvt");
            tracker.RemoveDocument(Is(annex), AgentSessionEndReasons.DocumentClosed, Now);
            tracker.Pause();
            tracker.Resume();
            tracker.End(AgentSessionEndReasons.HostStopped, Now);
            tracker.Request(null, Now);
            tracker.Decline(Now);
            tracker.SetStartMode(AgentSessionStart.Auto);
            Assert.Equal(10, raised);
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
