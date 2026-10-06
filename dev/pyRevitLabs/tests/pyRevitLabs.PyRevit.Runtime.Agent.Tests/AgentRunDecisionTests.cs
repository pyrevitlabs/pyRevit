using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentRunDecisionTests {
        private static AgentRunFacts CleanModifyRun(AgentPolicy policy = AgentPolicy.Ask) {
            return new AgentRunFacts {
                Mode = AgentRunMode.Modify,
                HasDocument = true,
                HasChanges = true,
                Policy = policy,
            };
        }

        [Fact]
        public void LeftOpenTransactionWinsOverEveryOtherFailure() {
            var facts = CleanModifyRun(AgentPolicy.Auto);
            facts.TransactionLeftOpen = true;
            facts.ScriptFailed = true;
            facts.ChangedOtherOpenDocument = true;

            Assert.Equal(AgentRunVerdict.TransactionLeftOpen, AgentRunDecision.Decide(facts));
        }

        [Fact]
        public void ScriptFailureRollsBackUnderAutoPolicy() {
            var facts = CleanModifyRun(AgentPolicy.Auto);
            facts.ScriptFailed = true;

            var verdict = AgentRunDecision.Decide(facts);

            Assert.Equal(AgentRunVerdict.ScriptFailed, verdict);
            Assert.Equal("error", AgentRunDecision.Status(verdict));
            Assert.Equal("rolled_back", AgentRunDecision.Decision(verdict));
        }

        [Fact]
        public void ChangingAnotherOpenDocumentFailsEvenWithoutAnActiveDocument() {
            var facts = CleanModifyRun(AgentPolicy.Auto);
            facts.HasDocument = false;
            facts.ChangedOtherOpenDocument = true;

            Assert.Equal(AgentRunVerdict.OtherDocumentChanged, AgentRunDecision.Decide(facts));
        }

        [Fact]
        public void QueryWithChangesIsAnErrorAndNeverCommits() {
            var facts = CleanModifyRun(AgentPolicy.Auto);
            facts.Mode = AgentRunMode.Query;

            var verdict = AgentRunDecision.Decide(facts);

            Assert.Equal(AgentRunVerdict.QueryModifiedModel, verdict);
            Assert.Equal("error", AgentRunDecision.Status(verdict));
            Assert.Equal("rolled_back", AgentRunDecision.Decision(verdict));
        }

        [Fact]
        public void QueryWithoutChangesReportsRolledBackNotNoChanges() {
            var facts = CleanModifyRun();
            facts.Mode = AgentRunMode.Query;
            facts.HasChanges = false;

            var verdict = AgentRunDecision.Decide(facts);

            Assert.Equal("ok", AgentRunDecision.Status(verdict));
            Assert.Equal("rolled_back", AgentRunDecision.Decision(verdict));
        }

        [Fact]
        public void RunWithoutChangesReportsNoChanges() {
            foreach (var mode in new[] { AgentRunMode.DryRun, AgentRunMode.Modify }) {
                var facts = CleanModifyRun(AgentPolicy.Auto);
                facts.Mode = mode;
                facts.HasChanges = false;

                Assert.Equal("no_changes", AgentRunDecision.Decision(AgentRunDecision.Decide(facts)));
            }
        }

        [Fact]
        public void DryRunWithChangesRollsBackUnderAutoPolicy() {
            var facts = CleanModifyRun(AgentPolicy.Auto);
            facts.Mode = AgentRunMode.DryRun;

            var verdict = AgentRunDecision.Decide(facts);

            Assert.Equal(AgentRunVerdict.DryRunRolledBack, verdict);
            Assert.Equal("rolled_back", AgentRunDecision.Decision(verdict));
        }

        [Fact]
        public void ModifyRunWithChangesFollowsThePolicy() {
            Assert.Equal(AgentRunVerdict.PolicyReadOnly, AgentRunDecision.Decide(CleanModifyRun(AgentPolicy.ReadOnly)));
            Assert.Equal(AgentRunVerdict.AskUser, AgentRunDecision.Decide(CleanModifyRun(AgentPolicy.Ask)));
            Assert.Equal(AgentRunVerdict.AutoCommit, AgentRunDecision.Decide(CleanModifyRun(AgentPolicy.Auto)));
        }

        [Fact]
        public void PolicyLoosenedDuringTheRunDoesNotApply() {
            Assert.Equal(AgentPolicy.ReadOnly, AgentRunDecision.Stricter(AgentPolicy.Auto, AgentPolicy.ReadOnly));
            Assert.Equal(AgentPolicy.Ask, AgentRunDecision.Stricter(AgentPolicy.Auto, AgentPolicy.Ask));
            Assert.Equal(AgentPolicy.Ask, AgentRunDecision.Stricter(AgentPolicy.Ask, AgentPolicy.Auto));
            Assert.Equal(AgentPolicy.ReadOnly, AgentRunDecision.Stricter(AgentPolicy.ReadOnly, AgentPolicy.Auto));
        }

        [Fact]
        public void VerdictMapsToTheResponseFields() {
            AssertResponse(AgentRunVerdict.AutoCommit, "ok", "committed", "auto");
            AssertResponse(AgentRunVerdict.UserApproved, "ok", "committed", "user");
            AssertResponse(AgentRunVerdict.UserDiscarded, "rejected", "discarded", "user");
            AssertResponse(AgentRunVerdict.PolicyReadOnly, "rejected", "rolled_back", null);
            AssertResponse(AgentRunVerdict.NoDocument, "ok", "no_document", null);
        }

        private static void AssertResponse(AgentRunVerdict verdict, string status, string decision, string approval) {
            Assert.Equal(status, AgentRunDecision.Status(verdict));
            Assert.Equal(decision, AgentRunDecision.Decision(verdict));
            Assert.Equal(approval, AgentRunDecision.Approval(verdict));
        }
    }
}
