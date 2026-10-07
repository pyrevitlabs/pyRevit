using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentLogViewModelTests {
        private static readonly DateTime Now = new DateTime(2026, 10, 5, 14, 5, 30, DateTimeKind.Utc);

        private static readonly Dictionary<string, string> Strings = new Dictionary<string, string> {
            ["AgentPanel.Kind.query"] = "Query",
            ["AgentPanel.Kind.modify"] = "Change",
            ["AgentPanel.Kind.context"] = "Read context",
            ["AgentPanel.Log.NoSession"] = "Without a session",
            ["AgentPanel.Log.Session"] = "{0} from {1}",
            ["AgentPanel.Log.Summary"] = "{0} | {1} | {2} | {3}",
            ["AgentPanel.Log.Duration"] = "{0:0.0}s",
            ["AgentPanel.Log.WithApproval"] = "{0} | {1}",
            ["AgentPanel.Log.Approval.user"] = "you decided",
            ["AgentPanel.Log.Reason"] = "Why: {0}",
            ["AgentPanel.Log.Moved"] = "moved {0} -> {1}",
            ["AgentPanel.Log.Changes"] = "+{0} ~{1} -{2}",
            ["AgentPanel.Log.Flag.OtherDocument"] = "other document",
            ["AgentPanel.Log.Flag.CloseWithoutSaving"] = "close {0} unsaved",
            ["AgentPanel.Log.Flag.NoChanges"] = "no changes",
            ["AgentPanel.Log.Flag.Warning"] = "warned: {0}",
            ["AgentPanel.Log.Engine"] = "engine {0}",
            ["AgentPanel.Log.RunFolder"] = "folder {0}",
        };

        private readonly AgentActivity activity = new AgentActivity();
        private readonly List<AgentLogElement> selected = new List<AgentLogElement>();
        private readonly AgentLogViewModel log;

        public AgentLogViewModelTests() {
            log = new AgentLogViewModel(key => Strings.TryGetValue(key, out var value) ? value : null, selected.Add);
        }

        private static string Local(DateTime utc, string format) {
            return utc.ToLocalTime().ToString(format, CultureInfo.CurrentCulture);
        }

        private AgentRequestRecord Finish(string kind, string title, string session, string outcome = "ok", JObject details = null, string reason = null) {
            var record = activity.Arrive(kind, title, reason, (session, session == null ? null : "Tower.rvt"), Now);
            activity.Start(record, Now);
            activity.Finish(record, outcome, Now.AddSeconds(2), details);
            return activity.Last;
        }

        private static JObject Run(JObject extra = null) {
            var details = new JObject {
                ["mode"] = "modify",
                ["decision"] = "committed",
                ["approval"] = "user",
                ["elapsed_ms"] = 1500,
                ["document"] = "Tower.rvt",
                ["run_dir"] = "C:\\runs\\abc",
                ["added"] = 1,
                ["modified"] = 2,
                ["deleted"] = 0,
                ["by_category"] = new JObject { ["Walls"] = 2, ["Doors"] = 1 },
                ["elements"] = new JArray(
                    new JObject { ["id"] = 101, ["category"] = "Walls", ["name"] = "Basic Wall" },
                    new JObject { ["id"] = 102, ["category"] = "Doors" }),
                ["other_documents"] = 0,
                ["warnings"] = new JArray(),
                ["output"] = "done",
                ["error"] = null,
                ["engine"] = "ironpython 2.7.12",
                ["script"] = "x = 1",
            };
            if (extra != null)
                details.Merge(extra);
            return details;
        }

        [Fact]
        public void RequestsAreGroupedBySessionWithTheLatestFirst() {
            Finish("query", "Count walls", "s1");
            Finish("query", "Without", null);
            Finish("modify", "Add walls", "s1");

            log.Update(activity.History);

            Assert.Equal(new[] { "s1", "" }, log.Groups.Select(group => group.Key));
            Assert.Equal("Tower.rvt from " + Local(Now, "HH:mm"), log.Groups[0].Header);
            Assert.Equal("Without a session", log.Groups[1].Header);
            Assert.Equal(new[] { "Add walls", "Count walls" }, log.Groups[0].Entries.Select(entry => entry.Title));
            Assert.False(log.IsEmpty);
        }

        [Fact]
        public void AMoveShowsAsAMarkerAndTheHeaderNamesTheCurrentDocument() {
            Finish("query", "Before", "s1");
            log.Update(activity.History);
            var group = Assert.Single(log.Groups);
            Assert.Equal("Tower.rvt from " + Local(Now, "HH:mm"), group.Header);

            activity.RecordMove("Tower.rvt", ("s1", "Annex.rvt"), Now.AddMinutes(5));
            var after = activity.Arrive("query", "After", null, ("s1", "Annex.rvt"), Now.AddMinutes(6));
            activity.Finish(after, "ok", Now.AddMinutes(6));
            log.Update(activity.History);

            Assert.Same(group, Assert.Single(log.Groups));
            Assert.Equal("Annex.rvt from " + Local(Now, "HH:mm"), group.Header);
            Assert.Equal(new[] { "After", "moved Tower.rvt -> Annex.rvt", "Before" }, group.Entries.Select(entry => entry.Title));
            var marker = group.Entries[1];
            Assert.Equal("moved", marker.StatusKind);
            Assert.Equal(Local(Now.AddMinutes(5), "HH:mm:ss"), marker.Summary);
            Assert.True(marker.IsVisible);
        }

        [Fact]
        public void AnUpdateKeepsExpandedRowsAndAddsNewOnesOnTop() {
            Finish("query", "First", "s1");
            log.Update(activity.History);
            var first = log.Groups[0].Entries[0];
            first.IsExpanded = true;

            Finish("query", "Second", "s1");
            log.Update(activity.History);

            Assert.Same(first, log.Groups[0].Entries[1]);
            Assert.True(first.IsExpanded);
            Assert.Equal("Second", log.Groups[0].Entries[0].Title);
        }

        [Fact]
        public void RequestsTheHistoryDroppedLeaveTheLog() {
            for (var index = 0; index < AgentActivity.MaxHistory; index++)
                Finish("query", "Old " + index, null);
            log.Update(activity.History);

            Finish("query", "New", "s2");
            log.Update(activity.History);

            Assert.Equal(AgentActivity.MaxHistory, log.Groups.Sum(group => group.Entries.Count));
            Assert.DoesNotContain(log.Groups.SelectMany(group => group.Entries), entry => entry.Title == "Old 0");
        }

        [Fact]
        public void LookupsAreHiddenUntilTheUserAsksForThem() {
            Finish("context", null, "s1");
            activity.RecordLookup("lookup", "Wall", ("s1", "Tower.rvt"), "ok", Now);
            log.Update(activity.History);

            Assert.True(log.IsEmpty);
            Assert.False(log.Groups[0].IsVisible);

            log.ShowLookups = true;

            Assert.False(log.IsEmpty);
            Assert.True(log.Groups[0].IsVisible);
            Assert.All(log.Groups[0].Entries, entry => Assert.True(entry.IsVisible));
            Assert.Equal("Read context", log.Groups[0].Entries[1].Title);
        }

        [Fact]
        public void ARunEntrySummarizesWhatHappened() {
            Finish("modify", "Add walls", "s1", "committed", Run(), "The plan needs them");
            log.Update(activity.History);

            var entry = log.Groups[0].Entries[0];

            Assert.Equal("committed", entry.StatusKind);
            Assert.Equal("Change | " + Local(Now.AddSeconds(2), "HH:mm:ss") + " | committed | " + 1.5.ToString("0.0", CultureInfo.CurrentCulture) + "s | you decided", entry.Summary);
            Assert.Equal("Why: The plan needs them", entry.Reason);
            Assert.Equal("+1 ~2 -0", entry.Changes);
            Assert.Equal("Walls: 2\nDoors: 1", entry.Categories);
            Assert.Equal(new[] { "Basic Wall 101", "Doors 102" }, entry.Elements.Select(element => element.Label));
            Assert.Equal("x = 1", entry.Script);
            Assert.Equal("done", entry.Output);
            Assert.Equal("engine ironpython 2.7.12", entry.Engine);
            Assert.Equal("folder C:\\runs\\abc", entry.RunFolder);
            Assert.False(entry.HasFlags || entry.HasError);
        }

        [Fact]
        public void ClickingAnElementAsksToSelectItInItsDocument() {
            Finish("modify", "Add walls", "s1", "committed", Run());
            log.Update(activity.History);

            log.Groups[0].Entries[0].Elements[0].SelectCommand.Execute(null);

            var element = Assert.Single(selected);
            Assert.Equal(101, element.Id);
            Assert.Equal("Tower.rvt", element.Document);
        }

        [Fact]
        public void FlagsCallOutWhatTheUserShouldKnow() {
            Finish("modify", "Nothing", "s1", "ok", Run(new JObject {
                ["decision"] = "no_changes",
                ["other_documents"] = 1,
                ["warnings"] = new JArray("A commit was lost", "Another"),
            }));
            log.Update(activity.History);

            Assert.Equal(new[] { "other document", "no changes", "warned: A commit was lost" }, log.Groups[0].Entries[0].Flags);
        }

        [Fact]
        public void DocumentsARunLeftChangedAreNamedSoTheUserClosesThemUnsaved() {
            Finish("modify", "Reach across", "s1", "OtherDocumentChanged", Run(new JObject {
                ["other_documents"] = 2,
                ["unreverted_documents"] = new JArray("Annex", "Site"),
            }));
            log.Update(activity.History);

            Assert.Equal(new[] { "close Annex, Site unsaved" }, log.Groups[0].Entries[0].Flags);
        }

        [Fact]
        public void AFailedRunShowsItsErrorAndTraceback() {
            Finish("query", "Read", "s1", "ValueError", Run(new JObject {
                ["error"] = new JObject { ["type"] = "ValueError", ["message"] = "bad", ["traceback"] = "line 3" },
            }));
            log.Update(activity.History);

            var entry = log.Groups[0].Entries[0];
            Assert.Equal("error", entry.StatusKind);
            Assert.Equal("ValueError: bad\n\nline 3", entry.Error);
        }

        [Fact]
        public void ARequestWithoutATitleIsNamedByItsKindAndTimedFromItsStart() {
            Finish("query", null, null, "session_inactive");
            log.Update(activity.History);

            var entry = log.Groups[0].Entries[0];
            Assert.Equal("Query", entry.Title);
            Assert.Equal("error", entry.StatusKind);
            Assert.EndsWith(2.0.ToString("0.0", CultureInfo.CurrentCulture) + "s", entry.Summary);
            Assert.False(entry.HasScript || entry.HasElements || entry.HasRunFolder);
        }

        [Fact]
        public void TogglingARowExpandsAndCollapsesIt() {
            Finish("query", "Read", "s1");
            log.Update(activity.History);
            var entry = log.Groups[0].Entries[0];

            entry.ToggleCommand.Execute(null);
            Assert.True(entry.IsExpanded);
            entry.ToggleCommand.Execute(null);
            Assert.False(entry.IsExpanded);
        }
    }
}
