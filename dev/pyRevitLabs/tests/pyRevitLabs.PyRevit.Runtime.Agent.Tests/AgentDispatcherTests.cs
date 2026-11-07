using System;
using System.Threading;

using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentDispatcherTests {
        private static readonly TimeSpan Long = TimeSpan.FromSeconds(10);

        private static AgentDispatcher StartDispatcher() {
            var dispatcher = new AgentDispatcher(TimeSpan.Zero);
            var mainThread = new object();
            dispatcher.Attach(new ExternalEvent {
                OnRaise = () => {
                    new Thread(() => {
                        lock (mainThread)
                            dispatcher.Execute(null);
                    }) { IsBackground = true }.Start();
                    return ExternalEventRequest.Accepted;
                },
            });
            return dispatcher;
        }

        [Fact]
        public void ScriptStuckPastItsDeadlineReleasesTheCallerAndExplainsLaterBusyErrors() {
            var dispatcher = StartDispatcher();
            using (var blockingCall = new ManualResetEventSlim()) {
                var hung = Assert.Throws<AgentException>(() => dispatcher.Invoke(app => {
                    using (dispatcher.BeginScript(TimeSpan.Zero, "run1", "req1"))
                        blockingCall.Wait();
                    return "hung";
                }, Long));
                Assert.Equal("run_hung", hung.Code);
                Assert.Equal("unknown", hung.Details.Value<string>("outcome"));
                Assert.Equal("run1", hung.Details.Value<string>("run_id"));
                Assert.Equal("req1", hung.Details.Value<string>("request_id"));

                var busy = Assert.Throws<AgentException>(
                    () => dispatcher.Invoke(app => "later", TimeSpan.FromMilliseconds(200)));
                Assert.Equal(AgentException.NotRunCode, busy.Code);
                Assert.Contains("past its time limit", busy.Message);

                blockingCall.Set();
            }
            Assert.Equal("next", dispatcher.Invoke(app => "next", Long).Value<string>());
        }

        [Fact]
        public void WorkThatFailsReachesTheCallerUnwrapped() {
            var dispatcher = StartDispatcher();

            var failure = Assert.Throws<AgentException>(() => dispatcher.Invoke(app => {
                Thread.Sleep(1500);
                throw new AgentException("no_active_document", "none");
            }, Long));

            Assert.Equal("no_active_document", failure.Code);
        }

        [Fact]
        public void WorkOutsideTheScriptPhaseIsWaitedForAsLongAsItTakes() {
            var dispatcher = StartDispatcher();

            var result = dispatcher.Invoke(app => {
                using (dispatcher.BeginScript(TimeSpan.FromHours(1), "outer", "req-outer")) {
                    using (dispatcher.BeginScript(TimeSpan.Zero, "inner", "req-inner")) { }
                    Thread.Sleep(1500);
                }
                Thread.Sleep(1500);
                return new JValue("approved");
            }, Long);

            Assert.Equal("approved", result.Value<string>());
        }
    }
}
