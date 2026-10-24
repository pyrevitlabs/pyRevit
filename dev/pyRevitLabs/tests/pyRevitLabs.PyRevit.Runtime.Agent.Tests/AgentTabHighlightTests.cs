using System;
using System.Collections.Generic;
using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace pyRevitLabs.PyRevit.Runtime.Agent.Tests {
    /// <summary>Exercises the Revit-free lease, timing, failure and property ownership contracts.</summary>
    public sealed class AgentTabHighlightTests {
        private sealed class Harness : IAgentTabHighlightVisuals {
            internal long Now;
            internal readonly List<(long Due, Action Callback)> Scheduled = new List<(long, Action)>();
            internal readonly Dictionary<long, string> Values = new Dictionary<long, string>();
            internal readonly Dictionary<long, object> Installed = new Dictionary<long, object>();
            internal readonly List<long> Restored = new List<long>();
            internal bool HasTabs = true;
            internal bool Fail;
            internal int Logs;
            internal readonly AgentTabHighlight Coordinator;

            internal Harness() {
                Coordinator = new AgentTabHighlight(() => Now,
                    (delay, callback) => Scheduled.Add((Now + delay, callback)), this, exception => Logs++);
            }

            /// <summary>Simulates painting and optionally fails after installing an owned value.</summary>
            public bool Apply(long key, string tooltip) {
                if (!HasTabs)
                    return false;
                Values[key] = tooltip;
                Installed[key] = new object();
                if (Fail)
                    throw new InvalidOperationException("visual failure");
                return true;
            }

            /// <summary>Removes the fake visual properties owned by the target.</summary>
            public void Restore(long key) {
                Values.Remove(key);
                Installed.Remove(key);
                Restored.Add(key);
            }

            /// <summary>Releases a completed document registration.</summary>
            public void Forget(long key) { }

            internal void Advance(long now) {
                Now = now;
                foreach (var callback in Scheduled.Where(item => item.Due <= now).ToArray()) {
                    Scheduled.Remove(callback);
                    callback.Callback();
                }
            }
        }

        /// <summary>Restoration occurs at 1500 milliseconds, not at 1499.</summary>
        [Fact]
        public void MinimumVisibilityBoundary() {
            var harness = new Harness();
            var lease = harness.Coordinator.Begin(1, "Run");
            harness.Coordinator.End(lease);
            harness.Advance(1499);
            Assert.Equal("Agent: Run", harness.Values[1]);
            harness.Scheduled.Single().Callback();
            Assert.Equal("Agent: Run", harness.Values[1]);
            harness.Advance(1500);
            Assert.Empty(harness.Values);
        }

        /// <summary>A later paint starts the visibility interval when earlier attempts find no tabs.</summary>
        [Fact]
        public void MinimumVisibilityStartsAtFirstPaint() {
            var harness = new Harness { HasTabs = false };
            var lease = harness.Coordinator.Begin(1, "Run");
            harness.Now = 1000;
            harness.HasTabs = true;
            harness.Coordinator.Refresh();
            harness.Coordinator.End(lease);
            harness.Advance(2499);
            Assert.Single(harness.Values);
            harness.Advance(2500);
            Assert.Empty(harness.Values);
        }

        /// <summary>Consecutive leases retain their first paint and ignore the previous expiry callback.</summary>
        [Fact]
        public void ConsecutiveLeasesMergeWithoutRestoring() {
            var harness = new Harness();
            var first = harness.Coordinator.Begin(1, "First");
            harness.Coordinator.End(first);
            harness.Now = 1000;
            var second = harness.Coordinator.Begin(1, "Second");
            harness.Advance(1500);
            Assert.Empty(harness.Restored);
            Assert.Equal("Agent: Second", harness.Values[1]);
            harness.Coordinator.End(second);
            Assert.Empty(harness.Values);
        }

        /// <summary>An old callback cannot clear a new document state with the same native key.</summary>
        [Fact]
        public void StaleGenerationCannotRestoreNewLease() {
            var harness = new Harness();
            var first = harness.Coordinator.Begin(1, "First");
            harness.Coordinator.End(first);
            var stale = harness.Scheduled.Single().Callback;
            harness.Advance(1500);
            var second = harness.Coordinator.Begin(1, "Second");
            stale();
            Assert.Equal("Agent: Second", harness.Values[1]);
            harness.Coordinator.End(second);
            harness.Advance(3000);
            Assert.Empty(harness.Values);
        }

        /// <summary>Each document has a separate visibility interval and approval label.</summary>
        [Fact]
        public void DocumentsRemainIndependent() {
            var harness = new Harness();
            var first = harness.Coordinator.Begin(1, "First");
            harness.Now = 1000;
            var second = harness.Coordinator.Begin(2, "Second");
            harness.Coordinator.AwaitApproval(second);
            harness.Coordinator.End(first);
            harness.Coordinator.End(second);
            harness.Advance(1500);
            Assert.False(harness.Values.ContainsKey(1));
            Assert.Equal("Agent: Second (awaiting approval)", harness.Values[2]);
            harness.Advance(2500);
            Assert.Empty(harness.Values);
        }

        /// <summary>Ending a nested lease restores the remaining lease's approval label without clearing.</summary>
        [Fact]
        public void OverlappingLeasesKeepRemainingApproval() {
            var harness = new Harness();
            var first = harness.Coordinator.Begin(1, "First");
            harness.Coordinator.AwaitApproval(first);
            var second = harness.Coordinator.Begin(1, "Second");
            harness.Coordinator.End(second);
            Assert.Equal("Agent: First (awaiting approval)", harness.Values[1]);
            Assert.Empty(harness.Restored);
        }

        /// <summary>Restoration uses identity and leaves independently replaced property values intact.</summary>
        [Fact]
        public void PropertyRestorationSkipsOtherOwners() {
            var original = new object();
            var current = original;
            var installed = new string('x', 1);
            var property = new AgentTabHighlightValue(() => current, value => current = value, () => current = original);
            property.Apply(installed);
            var otherOwner = new string('x', 1);
            Assert.Equal(installed, otherOwner);
            Assert.NotSame(installed, otherOwner);
            current = otherOwner;
            property.Restore();
            Assert.Same(otherOwner, current);
            property = new AgentTabHighlightValue(() => current, value => current = value, () => current = otherOwner);
            property.Apply(installed);
            property.Restore();
            Assert.Same(otherOwner, current);
        }

        /// <summary>Missing tabs neither schedule delayed restoration nor contribute to failure disabling.</summary>
        [Fact]
        public void NoTabsAreNotFailures() {
            var harness = new Harness { HasTabs = false };
            for (var index = 0; index < 5; index++) {
                var lease = harness.Coordinator.Begin(1, "Run");
                harness.Coordinator.End(lease);
            }
            Assert.Empty(harness.Scheduled);
            Assert.Equal(0, harness.Logs);
            harness.HasTabs = true;
            Assert.NotNull(harness.Coordinator.Begin(1, "Visible"));
            Assert.Single(harness.Values);
        }

        /// <summary>Three consecutive failures disable all painting and log only once.</summary>
        [Fact]
        public void ThreeFailuresDisableAndCleanUp() {
            var harness = new Harness { Fail = true };
            var lease = harness.Coordinator.Begin(1, "Run");
            Assert.Empty(harness.Installed);
            harness.Coordinator.AwaitApproval(lease);
            harness.Coordinator.Refresh();
            Assert.Equal(1, harness.Logs);
            Assert.Null(harness.Coordinator.Begin(2, "Disabled"));
            harness.Coordinator.Refresh();
            Assert.Equal(1, harness.Logs);
            Assert.Empty(harness.Values);
        }

        /// <summary>A successful paint resets the failure counter; cleanup does not reset it.</summary>
        [Fact]
        public void SuccessfulPaintResetsFailureCounter() {
            var harness = new Harness { Fail = true };
            var first = harness.Coordinator.Begin(1, "First");
            harness.Coordinator.End(first);
            var second = harness.Coordinator.Begin(1, "Second");
            harness.Fail = false;
            harness.Coordinator.Refresh();
            harness.Fail = true;
            harness.Coordinator.Refresh();
            harness.Coordinator.Refresh();
            Assert.Equal(0, harness.Logs);
            harness.Coordinator.Refresh();
            Assert.Equal(1, harness.Logs);
            harness.Coordinator.End(second);
        }

        /// <summary>Disposal removes active visuals immediately and makes queued callbacks harmless.</summary>
        [Fact]
        public void DisposeWithActiveLease() {
            var harness = new Harness();
            var first = harness.Coordinator.Begin(1, "First");
            harness.Coordinator.End(first);
            harness.Coordinator.Begin(2, "Active");
            harness.Coordinator.Dispose();
            Assert.Empty(harness.Values);
            harness.Advance(1500);
            Assert.Null(harness.Coordinator.Begin(3, "Disposed"));
            Assert.Empty(harness.Values);
        }

        /// <summary>A target exception after writing a property cannot leak an owned value from Begin.</summary>
        [Fact]
        public void PartialPaintFailureRestoresOwnedValues() {
            var harness = new Harness { Fail = true };
            var exception = Record.Exception(() => harness.Coordinator.Begin(1, "Run"));
            Assert.Null(exception);
            Assert.Empty(harness.Installed);
            Assert.Empty(harness.Values);
        }

        /// <summary>A failing setter that already changed its value remains restorable by identity.</summary>
        [Fact]
        public void PropertySetterFailureRetainsOwnership() {
            var original = new object();
            var current = original;
            var installed = new object();
            var property = new AgentTabHighlightValue(() => current, value => {
                current = value;
                throw new InvalidOperationException("setter failed");
            }, () => current = original);
            Assert.Throws<InvalidOperationException>(() => property.Apply(installed));
            property.Restore();
            Assert.Same(original, current);
        }
    }
}
