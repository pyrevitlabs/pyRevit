using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentPolicyInForceTests {
        private static bool Refuse(AgentPolicy inForce, AgentPolicy configured) => false;

        private static bool Accept(AgentPolicy inForce, AgentPolicy configured) => true;

        [Fact]
        public void TheFirstPolicyReadIsTrustedWithoutAsking() {
            var policy = new AgentPolicyInForce();

            Assert.Equal(AgentPolicy.Auto, policy.Start(AgentPolicy.Auto, (_, __) => throw new Xunit.Sdk.XunitException("asked")));
        }

        [Fact]
        public void AStricterPolicyAppliesWithoutAsking() {
            var policy = new AgentPolicyInForce();
            policy.Start(AgentPolicy.Auto, Refuse);

            Assert.Equal(AgentPolicy.ReadOnly, policy.Start(AgentPolicy.ReadOnly, (_, __) => throw new Xunit.Sdk.XunitException("asked")));
        }

        [Fact]
        public void ALooserPolicyAppliesOnlyOnceConfirmed() {
            var declined = new AgentPolicyInForce();
            declined.Start(AgentPolicy.Ask, Refuse);
            var accepted = new AgentPolicyInForce();
            accepted.Start(AgentPolicy.Ask, Refuse);

            Assert.Equal(AgentPolicy.Ask, declined.Start(AgentPolicy.Auto, Refuse));
            Assert.Equal(AgentPolicy.Auto, accepted.Start(AgentPolicy.Auto, Accept));
        }

        [Fact]
        public void ADeclinedPolicyIsNotAskedAboutAgain() {
            var policy = new AgentPolicyInForce();
            policy.Start(AgentPolicy.ReadOnly, Refuse);
            var asked = 0;
            bool Count(AgentPolicy inForce, AgentPolicy configured) {
                asked++;
                return false;
            }

            policy.Start(AgentPolicy.Auto, Count);
            policy.Start(AgentPolicy.Auto, Count);

            Assert.Equal(1, asked);
        }

        [Fact]
        public void AStricterPolicySeenOutsideAStartStillNeedsConfirmingToLoosen() {
            var policy = new AgentPolicyInForce();
            policy.Start(AgentPolicy.Auto, Refuse);
            var asked = 0;

            policy.Tighten(AgentPolicy.ReadOnly);
            var started = policy.Start(AgentPolicy.Auto, (_, __) => {
                asked++;
                return false;
            });

            Assert.Equal(1, asked);
            Assert.Equal(AgentPolicy.ReadOnly, started);
        }

        [Fact]
        public void CurrentReportsTheStricterOfConfiguredAndInForce() {
            var policy = new AgentPolicyInForce();
            Assert.Equal(AgentPolicy.Auto, policy.Current(AgentPolicy.Auto));

            policy.Start(AgentPolicy.ReadOnly, Refuse);

            Assert.Equal(AgentPolicy.ReadOnly, policy.Current(AgentPolicy.Auto));
            Assert.Equal(AgentPolicy.ReadOnly, policy.Current(AgentPolicy.ReadOnly));
        }
    }
}
