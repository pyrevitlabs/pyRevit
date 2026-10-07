using System;
using System.Collections.Generic;
using System.Globalization;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentPanelViewModelTests {
        private static readonly DateTime Started = new DateTime(2026, 10, 5, 14, 2, 0, DateTimeKind.Utc);

        private static readonly Dictionary<string, string> Strings = new Dictionary<string, string> {
            ["AgentPanel.State.Off"] = "AGENT HOST OFF",
            ["AgentPanel.State.Inactive"] = "NO SESSION",
            ["AgentPanel.State.Active"] = "ACTIVE",
            ["AgentPanel.State.Paused"] = "PAUSED",
            ["AgentPanel.Document.HostOff"] = "host off",
            ["AgentPanel.Document.NoDocument"] = "no document",
            ["AgentPanel.Document.Ready"] = "ready",
            ["AgentPanel.Document.Optional"] = "optional",
            ["AgentPanel.Document.Bound"] = "{0} since {1}",
            ["AgentPanel.Start"] = "Start on {0}",
            ["AgentPanel.Resume"] = "Resume",
            ["AgentPanel.Paused.ByHost"] = "paused: {0}",
            ["AgentPanel.Paused.PanelHidden"] = "panel hidden",
            ["AgentPanel.Request.NoReason"] = "no reason",
            ["AgentPanel.Request.Time"] = "asked {0}",
            ["AgentPanel.Policy.Ask"] = "ask",
            ["AgentPanel.Policy.Readonly"] = "read-only",
            ["AgentPanel.Client.Unknown"] = "unknown client",
            ["AgentPanel.Last"] = "{0} | {1} | {2}",
            ["AgentPanel.Waiting.Approval"] = "{0} approval",
            ["AgentPanel.Waiting.Running"] = "{0} running",
            ["AgentPanel.Waiting.Dialog"] = "{0} blocked by {1}",
            ["AgentPanel.Waiting.Revit"] = "{0} waiting",
            ["AgentPanel.Kind.modify"] = "Change",
            ["AgentPanel.Kind.query"] = "Query",
        };

        private readonly FakeBackend backend = new FakeBackend();

        private AgentPanelViewModel Panel() {
            return new AgentPanelViewModel(backend, key => Strings.TryGetValue(key, out var value) ? value : null);
        }

        private static string Local(DateTime utc) {
            return utc.ToLocalTime().ToString("HH:mm", CultureInfo.CurrentCulture);
        }

        private static JObject Session(string state, bool required = true, JObject request = null) {
            var open = state != "inactive";
            return new JObject {
                ["required"] = required,
                ["state"] = state,
                ["document"] = open ? "Tower.rvt" : null,
                ["started"] = open ? Started.ToString("o") : null,
                ["pending_request"] = request,
            };
        }

        [Fact]
        public void WhileTheHostIsOffNothingCanBeDone() {
            backend.HostRunning = false;
            backend.Session = Session("active", request: new JObject { ["reason"] = "x" });

            var panel = Panel();

            Assert.Equal("off", panel.StateKind);
            Assert.Equal("AGENT HOST OFF", panel.StateLabel);
            Assert.Equal("host off", panel.DocumentLine);
            Assert.False(panel.CanStart || panel.CanPause || panel.CanResume || panel.CanEnd || panel.HasRequest);
        }

        [Fact]
        public void WithoutASessionTheActiveDocumentCanBeStarted() {
            var panel = Panel();

            Assert.Equal("NO SESSION", panel.StateLabel);
            Assert.True(panel.CanStart);
            Assert.Equal("Start on Tower.rvt", panel.StartLabel);
            Assert.Equal("ready", panel.DocumentLine);
            Assert.False(panel.CanPause || panel.CanResume || panel.CanEnd);
        }

        [Fact]
        public void WithoutADocumentNothingCanBeStarted() {
            backend.ActiveDocumentTitle = null;

            var panel = Panel();

            Assert.False(panel.CanStart);
            Assert.Equal("no document", panel.DocumentLine);
        }

        [Fact]
        public void WhenSessionsAreOptionalThePanelSaysSo() {
            backend.Session = Session("inactive", required: false);

            Assert.Equal("optional", Panel().DocumentLine);
        }

        [Fact]
        public void AnActiveSessionCanBePausedOrEnded() {
            backend.Session = Session("active");

            var panel = Panel();

            Assert.Equal("ACTIVE", panel.StateLabel);
            Assert.Equal("Tower.rvt since " + Local(Started), panel.DocumentLine);
            Assert.True(panel.CanPause && panel.CanEnd);
            Assert.False(panel.CanStart || panel.CanResume);
        }

        [Fact]
        public void APausedSessionCanBeResumedOrEnded() {
            backend.Session = Session("paused");

            var panel = Panel();

            Assert.Equal("PAUSED", panel.StateLabel);
            Assert.True(panel.CanResume && panel.CanEnd);
            Assert.False(panel.CanStart || panel.CanPause || panel.HasPausedReason);
        }

        [Fact]
        public void APauseByPyRevitSaysWhy() {
            backend.Session = Session("paused");
            backend.Session["paused_reason"] = "it changed Annex.rvt.";

            var panel = Panel();

            Assert.True(panel.HasPausedReason);
            Assert.Equal("paused: it changed Annex.rvt.", panel.PausedReason);
            Assert.True(panel.CanResume);

            backend.Session = Session("active");
            backend.Session["paused_reason"] = "stale";
            panel.Refresh();

            Assert.False(panel.HasPausedReason);
            Assert.Equal(string.Empty, panel.PausedReason);
        }

        [Fact]
        public void APauseWhenThePanelWasHiddenSaysSoInThePanelsOwnWords() {
            backend.Session = Session("paused");
            backend.Session["paused_cause"] = "panel_hidden";
            backend.Session["paused_reason"] = "the agent panel in Revit was closed or hidden.";

            var panel = Panel();

            Assert.True(panel.HasPausedReason);
            Assert.Equal("panel hidden", panel.PausedReason);
        }

        [Fact]
        public void APendingRequestShowsItsReasonAndCanBeAccepted() {
            backend.Session = Session("inactive", request: new JObject { ["reason"] = "Renumber doors", ["requested"] = Started.ToString("o") });

            var panel = Panel();
            panel.AcceptCommand.Execute(null);

            Assert.True(panel.HasRequest);
            Assert.Equal("Renumber doors", panel.RequestReason);
            Assert.Equal("asked " + Local(Started), panel.RequestTime);
            Assert.Equal("Start on Tower.rvt", panel.AcceptLabel);
            Assert.Equal(1, backend.Starts);
        }

        [Fact]
        public void APendingRequestWhilePausedResumesWhenAccepted() {
            backend.Session = Session("paused", request: new JObject { ["reason"] = null });

            var panel = Panel();
            panel.AcceptCommand.Execute(null);

            Assert.Equal("no reason", panel.RequestReason);
            Assert.Equal("Resume", panel.AcceptLabel);
            Assert.Equal(new[] { "Resume" }, backend.Calls);
        }

        [Fact]
        public void EachCommandCallsTheBackend() {
            var panel = Panel();

            panel.PauseCommand.Execute(null);
            panel.ResumeCommand.Execute(null);
            panel.EndCommand.Execute(null);
            panel.DeclineCommand.Execute(null);
            panel.StartCommand.Execute(null);

            Assert.Equal(new[] { "Pause", "Resume", "End", "Decline" }, backend.Calls);
            Assert.Equal(1, backend.Starts);
        }

        [Fact]
        public void ARefusedActionShowsItsMessageUntilTheNextAction() {
            backend.Refusal = new AgentException("session_inactive", "There is no agent session to pause.");
            var panel = Panel();

            panel.PauseCommand.Execute(null);
            Assert.True(panel.HasError);
            Assert.Equal("There is no agent session to pause.", panel.ErrorText);

            backend.Refusal = null;
            panel.EndCommand.Execute(null);
            Assert.False(panel.HasError);
        }

        [Fact]
        public void AStartThatFailsLaterShowsTheError() {
            var panel = Panel();

            panel.StartCommand.Execute(null);
            backend.ReportStartFailure("Revit is busy.");

            Assert.Equal("Revit is busy.", panel.ErrorText);
        }

        [Fact]
        public void TheLastRequestShowsWhatWhenAndHowItEnded() {
            var record = backend.Activity.Arrive("modify", "Add walls", null, (null, null), Started);
            backend.Activity.Finish(record, "committed", Started);

            var panel = Panel();

            Assert.True(panel.HasLast);
            Assert.Equal("Change: Add walls | " + Local(Started) + " | committed", panel.LastText);
        }

        [Fact]
        public void AWaitingRequestSaysWhatHoldsItUp() {
            var record = backend.Activity.Arrive("query", null, null, (null, null), Started);
            Assert.Equal("Query waiting", Panel().WaitingText);

            backend.Dialogs.Add("'Save reminder' (#32770)");
            Assert.Equal("Query blocked by 'Save reminder' (#32770)", Panel().WaitingText);

            backend.Activity.Start(record, Started);
            Assert.Equal("Query running", Panel().WaitingText);

            backend.Activity.SetAwaitingApproval(true);
            Assert.Equal("Query approval", Panel().WaitingText);
        }

        [Fact]
        public void PolicyAndClientAreShown() {
            backend.Policy = "readonly";
            var panel = Panel();
            Assert.Equal("read-only", panel.PolicyText);
            Assert.Equal("unknown client", panel.ClientText);

            backend.Activity.NoteClient("Claude Code");
            panel.Refresh();
            Assert.Equal("Claude Code", panel.ClientText);
        }

        [Fact]
        public void AMissingStringFallsBackToItsKey() {
            backend.Policy = "auto";

            Assert.Equal("AgentPanel.Policy.Auto", Panel().PolicyText);
        }

        [Fact]
        public void RefreshTellsTheViewThatEverythingChanged() {
            var panel = Panel();
            string changed = null;
            panel.PropertyChanged += (_, args) => changed = args.PropertyName;

            panel.Refresh();

            Assert.Equal(string.Empty, changed);
        }

        [Fact]
        public void ClickingALoggedElementShowsItOrTheRefusal() {
            var record = backend.Activity.Arrive("modify", "Add walls", null, ("s1", "Tower.rvt"), Started);
            backend.Activity.Finish(record, "committed", Started, new JObject {
                ["document"] = "Tower.rvt",
                ["elements"] = new JArray(new JObject { ["id"] = 5, ["name"] = "Wall" }),
            });
            var panel = Panel();

            panel.Log.Groups[0].Entries[0].Elements[0].SelectCommand.Execute(null);
            backend.ShowFailure("The link belongs to a different or closed document.");

            var shown = Assert.Single(backend.Shown);
            Assert.Equal(new long[] { 5 }, shown.Ids);
            Assert.Equal("Tower.rvt", shown.Document);
            Assert.Equal("The link belongs to a different or closed document.", panel.ErrorText);
        }

        private sealed class FakeBackend : IAgentPanelBackend {
            private Action<string> startFailure;

            public bool HostRunning { get; set; } = true;
            public string Policy { get; set; } = "ask";
            public string ActiveDocumentTitle { get; set; } = "Tower.rvt";
            public JObject Session { get; set; } = AgentPanelViewModelTests.Session("inactive");
            public AgentActivity Activity { get; } = new AgentActivity();
            public List<string> Dialogs { get; } = new List<string>();
            public List<string> Calls { get; } = new List<string>();
            public int Starts { get; private set; }
            public AgentException Refusal { get; set; }

            public IList<string> OpenDialogs() {
                return Dialogs;
            }

            public void Start(Action<string> onError) {
                Starts++;
                startFailure = onError;
            }

            public void ReportStartFailure(string message) {
                startFailure(message);
            }

            public List<(IList<long> Ids, string Document)> Shown { get; } = new List<(IList<long>, string)>();

            public Action<string> ShowFailure { get; private set; }

            public void ShowElements(IList<long> ids, string document, Action<string> onError) {
                Shown.Add((ids, document));
                ShowFailure = onError;
            }

            public void Pause() {
                Record("Pause");
            }

            public void Resume() {
                Record("Resume");
            }

            public void End() {
                Record("End");
            }

            public void Decline() {
                Record("Decline");
            }

            private void Record(string call) {
                if (Refusal != null)
                    throw Refusal;
                Calls.Add(call);
            }
        }
    }
}
