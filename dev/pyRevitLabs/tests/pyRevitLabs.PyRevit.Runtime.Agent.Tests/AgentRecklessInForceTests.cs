using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentRecklessInForceTests {
        private static bool Refuse(bool inForce, bool configured) => false;

        private static bool Accept(bool inForce, bool configured) => true;

        private static bool NeverAsked(bool inForce, bool configured) => throw new Xunit.Sdk.XunitException("asked");

        [Fact]
        public void TheFirstSettingReadIsTrustedWithoutAsking() {
            var reckless = new AgentRecklessInForce();

            Assert.True(reckless.Start(true, NeverAsked));
        }

        [Fact]
        public void TurningRecklessOffAppliesWithoutAsking() {
            var reckless = new AgentRecklessInForce();
            reckless.Start(true, Refuse);

            Assert.False(reckless.Start(false, NeverAsked));
        }

        [Fact]
        public void TurningRecklessOnAppliesOnlyOnceConfirmed() {
            var declined = new AgentRecklessInForce();
            declined.Start(false, Refuse);
            var accepted = new AgentRecklessInForce();
            accepted.Start(false, Refuse);

            Assert.False(declined.Start(true, Refuse));
            Assert.True(accepted.Start(true, Accept));
        }

        [Fact]
        public void DecliningRecklessIsNotAskedAboutAgain() {
            var reckless = new AgentRecklessInForce();
            reckless.Start(false, Refuse);
            var asked = 0;
            bool Count(bool inForce, bool configured) {
                asked++;
                return false;
            }

            reckless.Start(true, Count);
            reckless.Start(true, Count);

            Assert.Equal(1, asked);
        }

        [Fact]
        public void RecklessOffSeenOutsideAStartStillNeedsConfirmingToTurnOn() {
            var reckless = new AgentRecklessInForce();
            reckless.Start(true, Refuse);
            var asked = 0;

            reckless.Tighten(false);
            var started = reckless.Start(true, (_, __) => {
                asked++;
                return false;
            });

            Assert.Equal(1, asked);
            Assert.False(started);
        }
    }
}
