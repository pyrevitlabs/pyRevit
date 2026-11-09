using System;
using System.Collections.Concurrent;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentEngineWarmUpTests {
        [Theory]
        [InlineData("ping")]
        [InlineData("get_context")]
        [InlineData("lookup_api")]
        [InlineData("no_such_method")]
        public void TheFirstRequestOfASessionLoadQueuesTheWarmUp(string method) {
            var warmUp = new AgentEngineWarmUp();

            Assert.True(warmUp.OnRequest(method, warmUp.Load));
        }

        [Fact]
        public void LaterRequestsQueueNothing() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.OnRequest("ping", warmUp.Load);

            Assert.False(warmUp.OnRequest("ping", warmUp.Load));
            Assert.False(warmUp.OnRequest("get_context", warmUp.Load));
        }

        [Fact]
        public void ARunQueuesNothingAndLeavesTheNextRequestToWarm() {
            var warmUp = new AgentEngineWarmUp();

            Assert.False(warmUp.OnRequest("run", warmUp.Load));
            Assert.True(warmUp.OnRequest("ping", warmUp.Load));
        }

        [Fact]
        public void AReloadLetsTheNextRequestWarmAgain() {
            var warmUp = new AgentEngineWarmUp();
            warmUp.OnRequest("ping", warmUp.Load);

            warmUp.Reset();

            Assert.True(warmUp.OnRequest("get_context", warmUp.Load));
        }

        [Fact]
        public void ARequestDuringWhichPyRevitReloadedLeavesTheNewLoadUncontacted() {
            var warmUp = new AgentEngineWarmUp();
            var loadAtStart = warmUp.Load;

            warmUp.Reset();

            Assert.False(warmUp.OnRequest("run", loadAtStart));
            Assert.True(warmUp.OnRequest("ping", warmUp.Load));
        }

        [Fact]
        public void ARequestThatStartedBeforeAReloadDoesNotWarmTheNewLoad() {
            var warmUp = new AgentEngineWarmUp();
            var loadAtStart = warmUp.Load;

            warmUp.Reset();

            Assert.False(warmUp.OnRequest("ping", loadAtStart));
            Assert.True(warmUp.OnRequest("get_context", warmUp.Load));
        }

        [Fact]
        public void ConcurrentFirstRequestsQueueOneWarmUp() {
            var warmUp = new AgentEngineWarmUp();
            var queued = 0;

            Parallel.For(0, 64, _ => {
                if (warmUp.OnRequest("ping", warmUp.Load))
                    Interlocked.Increment(ref queued);
            });

            Assert.Equal(1, queued);
        }

        [Fact]
        public void RevitProcessesWarmingTogetherEachRunTheirWholeEntryScriptAndLeaveNothing() {
            const string source = "from pyrevit.agent import _runner\n_runner.warm_up()\n";
            var folder = Path.Combine(Path.GetTempPath(), "pyrevit-agent-tests-" + Guid.NewGuid().ToString("N"));
            try {
                var processIds = Enumerable.Range(1000, 16).ToArray();
                var paths = new ConcurrentBag<string>();
                using (var start = new Barrier(processIds.Length)) {
                    Parallel.ForEach(processIds, new ParallelOptions { MaxDegreeOfParallelism = processIds.Length }, processId => {
                        start.SignalAndWait();
                        var read = AgentEngineWarmUp.WithEntryScript(folder, processId, source, path => {
                            paths.Add(path);
                            return File.ReadAllText(path);
                        });
                        Assert.Equal(source, read);
                    });
                }

                Assert.Equal(processIds.Length, paths.Distinct().Count());
                Assert.Empty(Directory.GetFiles(folder));
            }
            finally {
                Directory.Delete(folder, recursive: true);
            }
        }

        [Fact]
        public void TheEntryScriptIsDeletedEvenWhenTheRunFails() {
            var folder = Path.Combine(Path.GetTempPath(), "pyrevit-agent-tests-" + Guid.NewGuid().ToString("N"));
            try {
                Assert.Throws<InvalidOperationException>(() =>
                    AgentEngineWarmUp.WithEntryScript<int>(folder, 1, "pass\n", _ => throw new InvalidOperationException()));

                Assert.Empty(Directory.GetFiles(folder));
            }
            finally {
                Directory.Delete(folder, recursive: true);
            }
        }

        [Theory]
        [InlineData(true, true, false, true)]
        [InlineData(false, true, false, false)]
        [InlineData(true, false, false, false)]
        [InlineData(true, true, true, false)]
        public void WarmsOnlyAnEnabledIronPythonDefaultWithNoCachedEngine(
            bool agentEnabled, bool defaultEngineIsIronPython, bool engineCached, bool expected) {
            Assert.Equal(expected, AgentEngineWarmUp.ShouldWarm(agentEnabled, defaultEngineIsIronPython, engineCached));
        }
    }
}
