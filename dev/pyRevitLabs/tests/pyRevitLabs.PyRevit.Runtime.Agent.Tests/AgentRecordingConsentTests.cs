using System;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    /// <summary>
    /// Covers the consent to record: how recordings start, the request that waits for the user,
    /// and what an agent run may not loosen.
    /// </summary>
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentRecordingConsentTests {
        private static readonly DateTime Asked = new DateTime(2026, 11, 27, 9, 30, 0, DateTimeKind.Utc);

        private bool runExecuting;
        private int changes;
        private readonly AgentRecordingConsent consent;

        public AgentRecordingConsentTests() {
            consent = new AgentRecordingConsent(() => runExecuting);
            consent.Changed += () => changes++;
        }

        private static AgentRecordingOptions Limits(int maxDurationSeconds = 600, bool screenshots = false) {
            return new AgentRecordingOptions { MaxDurationSeconds = maxDurationSeconds, Screenshots = screenshots };
        }

        [Fact]
        public void RecordingsStartInThePanelUntilToldOtherwise() {
            var described = consent.Describe();

            Assert.Equal(AgentRecordingStart.User, consent.StartMode);
            Assert.Equal("user", described.Value<string>("start"));
            Assert.Equal(JTokenType.Null, described["pending_request"].Type);
            Assert.Equal(JTokenType.Null, described["declined_request"].Type);
            Assert.Null(consent.PendingOptions);
        }

        [Fact]
        public void ARequestWaitsWithItsReasonTimeAndLimits() {
            var limits = Limits();

            var requested = consent.Request(limits, "  Reproduce the crash  ", Asked);

            var pending = (JObject)consent.Describe()["pending_request"];
            Assert.True(JToken.DeepEquals(requested, pending));
            Assert.Equal("Reproduce the crash", pending.Value<string>("reason"));
            Assert.Equal(Asked.ToString("o"), pending.Value<string>("requested"));
            Assert.Equal(600, pending["options"].Value<int>("max_duration_s"));
            Assert.False(pending["options"].Value<bool>("screenshots"));
            Assert.Same(limits, consent.PendingOptions);
            Assert.Equal(1, changes);
        }

        [Fact]
        public void ARequestWithoutAReasonKeepsNone() {
            consent.Request(Limits(), " ", Asked);

            Assert.Equal(JTokenType.Null, consent.Describe()["pending_request"]["reason"].Type);
        }

        [Fact]
        public void DecliningKeepsTheRequestAsDeclinedAndForgetsItsLimits() {
            consent.Request(Limits(), "Reproduce the crash", Asked);

            Assert.True(consent.Decline(Asked.AddMinutes(1)));

            var described = consent.Describe();
            Assert.Equal(JTokenType.Null, described["pending_request"].Type);
            Assert.Equal("Reproduce the crash", described["declined_request"].Value<string>("reason"));
            Assert.Equal(Asked.AddMinutes(1).ToString("o"), described["declined_request"].Value<string>("declined"));
            Assert.Null(consent.PendingOptions);
        }

        [Fact]
        public void DecliningWithNothingPendingChangesNothing() {
            Assert.False(consent.Decline(Asked));

            Assert.Equal(0, changes);
        }

        [Fact]
        public void ANewRequestReplacesTheOldOneAndClearsTheDecline() {
            consent.Request(Limits(600), "First", Asked);
            consent.Decline(Asked);
            var second = Limits(120);

            consent.Request(second, "Second", Asked.AddMinutes(2));

            var described = consent.Describe();
            Assert.Equal("Second", described["pending_request"].Value<string>("reason"));
            Assert.Equal(JTokenType.Null, described["declined_request"].Type);
            Assert.Same(second, consent.PendingOptions);
        }

        [Fact]
        public void ClearingForgetsTheRequestAndTheDeclineAndSaysSoOnlyWhenThereWasOne() {
            consent.Clear();
            Assert.Equal(0, changes);

            consent.Request(Limits(), "Pending", Asked);
            consent.Clear();
            consent.Request(Limits(), "Declined", Asked);
            consent.Decline(Asked);
            consent.Clear();

            var described = consent.Describe();
            Assert.Equal(JTokenType.Null, described["pending_request"].Type);
            Assert.Equal(JTokenType.Null, described["declined_request"].Type);
            Assert.Null(consent.PendingOptions);
            Assert.Equal(5, changes);
        }

        [Fact]
        public void TheStartModeChangesOnceAndIsDescribed() {
            consent.SetStartMode(AgentRecordingStart.Auto);
            consent.SetStartMode(AgentRecordingStart.Auto);

            Assert.Equal(AgentRecordingStart.Auto, consent.StartMode);
            Assert.Equal("auto", consent.Describe().Value<string>("start"));
            Assert.Equal(1, changes);
        }

        [Fact]
        public void RunCodeCanNotMakeRecordingsStartAutomaticallyButCanTightenThem() {
            runExecuting = true;

            var refused = Assert.Throws<AgentException>(() => consent.SetStartMode(AgentRecordingStart.Auto));

            Assert.Equal("recording_locked", refused.Code);
            Assert.Equal(AgentRecordingStart.User, consent.StartMode);

            runExecuting = false;
            consent.SetStartMode(AgentRecordingStart.Auto);
            runExecuting = true;
            consent.SetStartMode(AgentRecordingStart.User);

            Assert.Equal(AgentRecordingStart.User, consent.StartMode);
        }

        [Fact]
        public void StartingAsTheUserIsRefusedOnlyWhileARunExecutes() {
            consent.RefuseWhileRunExecutes("not while a run executes");
            runExecuting = true;

            var refused = Assert.Throws<AgentException>(() => consent.RefuseWhileRunExecutes("not while a run executes"));

            Assert.Equal("recording_locked", refused.Code);
            Assert.Equal("not while a run executes", refused.Message);
        }
    }
}
