using System;
using System.IO.Pipes;
using System.Threading;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    /// <summary>
    /// Checks how <see cref="AgentPipeServer"/> retries creating its pipe and that it reports
    /// giving up through its stopped-listening callback.
    /// </summary>
    [Trait("Environment", "HostFree")]
    public sealed class AgentPipeServerTests {
        private static readonly TimeSpan Long = TimeSpan.FromSeconds(10);

        private static string UniquePipeName() => "pyrevit-agent-test-" + Guid.NewGuid().ToString("N");

        /// <summary>The wait between pipe creation attempts doubles from the first delay and stops at thirty seconds.</summary>
        [Fact]
        [Trait("Level", "Unit")]
        public void TheRetryDelayDoublesUpToThirtySeconds() {
            var first = TimeSpan.FromMilliseconds(500);

            Assert.Equal(TimeSpan.FromMilliseconds(500), AgentPipeServer.CreateRetryDelay(1, first));
            Assert.Equal(TimeSpan.FromSeconds(1), AgentPipeServer.CreateRetryDelay(2, first));
            Assert.Equal(TimeSpan.FromSeconds(16), AgentPipeServer.CreateRetryDelay(6, first));
            Assert.Equal(TimeSpan.FromSeconds(30), AgentPipeServer.CreateRetryDelay(7, first));
            Assert.Equal(TimeSpan.FromSeconds(30), AgentPipeServer.CreateRetryDelay(9, first));
        }

        /// <summary>A server that can never create its pipe stops and says so, so the host stops advertising it (#3949).</summary>
        [Fact]
        [Trait("Level", "Integration")]
        public void AServerThatGivesUpReportsThatItStoppedListening() {
            var pipeName = UniquePipeName();
            using (var occupied = new NamedPipeServerStream(pipeName, PipeDirection.InOut, 1))
            using (var stopped = new ManualResetEventSlim()) {
                AgentPipeServer reported = null;
                var server = new AgentPipeServer(pipeName, line => line, stoppedServer => {
                    reported = stoppedServer;
                    stopped.Set();
                }, TimeSpan.FromMilliseconds(1));
                using (server) {
                    server.Start();

                    Assert.True(stopped.Wait(Long));
                    Assert.Same(server, reported);
                    Assert.False(server.IsListening);
                }
            }
        }
    }
}
