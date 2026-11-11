using System;
using System.IO;
using System.IO.Pipes;
using System.Text;
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

        /// <summary>
        /// A pipe name another process already serves, even one that allows several instances, is
        /// never joined: its owner's access list would apply to the host's instances too.
        /// </summary>
        [Fact]
        [Trait("Level", "Integration")]
        public void APipeNameAnotherServerAlreadyHoldsIsNotJoined() {
            var pipeName = UniquePipeName();
            using (var squatter = new NamedPipeServerStream(pipeName, PipeDirection.InOut, 4))
            using (var stopped = new ManualResetEventSlim()) {
                var server = new AgentPipeServer(pipeName, line => line, _ => stopped.Set(), TimeSpan.FromMilliseconds(1));
                using (server) {
                    server.Start();

                    Assert.True(stopped.Wait(Long));
                    Assert.False(server.IsListening);
                }
            }
        }

        /// <summary>A connection whose request is still being handled doesn't keep the next client from connecting (#3949).</summary>
        [Fact]
        [Trait("Level", "Integration")]
        public void AClientConnectsWhileAnotherRequestIsStillBeingHandled() {
            var pipeName = UniquePipeName();
            using (var release = new ManualResetEventSlim())
            using (var server = new AgentPipeServer(pipeName, line => BlockOn(line, release), _ => { })) {
                server.Start();
                using (var first = Connect(pipeName, Long)) {
                    first.Send("block");

                    using (var second = Connect(pipeName, Long)) {
                        second.Send("ping");
                        Assert.Equal("ping", second.Receive());
                    }

                    release.Set();
                    Assert.Equal("block", first.Receive());
                }
            }
        }

        /// <summary>No more than the connection cap are open at once; a closed one frees its place.</summary>
        [Fact]
        [Trait("Level", "Integration")]
        public void ConnectionsBeyondTheCapWaitUntilOneCloses() {
            var pipeName = UniquePipeName();
            using (var release = new ManualResetEventSlim())
            using (var server = new AgentPipeServer(pipeName, line => BlockOn(line, release), _ => { }, TimeSpan.FromMilliseconds(1), 2)) {
                server.Start();
                var first = Connect(pipeName, Long);
                using (var second = Connect(pipeName, Long)) {
                    first.Send("block");
                    second.Send("block");

                    Assert.Throws<TimeoutException>(() => Connect(pipeName, TimeSpan.FromMilliseconds(500)));

                    release.Set();
                    Assert.Equal("block", first.Receive());
                    first.Dispose();
                    using (var third = Connect(pipeName, Long)) {
                        third.Send("ping");
                        Assert.Equal("ping", third.Receive());
                    }
                }
            }
        }

        /// <summary>Disposing the server closes every open connection, not only the newest one.</summary>
        [Fact]
        [Trait("Level", "Integration")]
        public void DisposingTheServerClosesEveryOpenConnection() {
            var pipeName = UniquePipeName();
            var server = new AgentPipeServer(pipeName, line => line, _ => { });
            server.Start();
            using (var first = Connect(pipeName, Long))
            using (var second = Connect(pipeName, Long)) {
                first.Send("ping");
                Assert.Equal("ping", first.Receive());
                second.Send("ping");
                Assert.Equal("ping", second.Receive());

                server.Dispose();

                Assert.Null(first.Receive());
                Assert.Null(second.Receive());
            }
        }

        private static string BlockOn(string line, ManualResetEventSlim release) {
            if (line == "block" && !release.Wait(Long))
                return "timed out";
            return line;
        }

        private static PipeClient Connect(string pipeName, TimeSpan timeout) {
            var pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
            try {
                pipe.Connect((int)timeout.TotalMilliseconds);
                return new PipeClient(pipe);
            }
            catch {
                pipe.Dispose();
                throw;
            }
        }

        private sealed class PipeClient : IDisposable {
            private readonly NamedPipeClientStream pipe;
            private readonly StreamReader reader;
            private readonly StreamWriter writer;

            public PipeClient(NamedPipeClientStream pipe) {
                this.pipe = pipe;
                reader = new StreamReader(pipe, new UTF8Encoding(false));
                writer = new StreamWriter(pipe, new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };
            }

            public void Send(string line) => writer.WriteLine(line);

            public string Receive() {
                var read = reader.ReadLineAsync();
                if (!read.Wait(Long))
                    throw new TimeoutException("No answer from the pipe server.");
                return read.Result;
            }

            public void Dispose() => pipe.Dispose();
        }
    }
}
