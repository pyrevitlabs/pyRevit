using System;
using System.IO;
using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentRecordingTests : IDisposable {
        private readonly string root = Path.Combine(Path.GetTempPath(), "pyrevit-recording-tests-" + Guid.NewGuid().ToString("N"));

        private readonly System.Collections.Generic.List<AgentRecordingStore> stores = new System.Collections.Generic.List<AgentRecordingStore>();

        public void Dispose() {
            foreach (var store in stores)
                store.Stop("test");
            if (Directory.Exists(root))
                Directory.Delete(root, recursive: true);
        }

        private AgentRecordingStore NewStore(int maxEvents = 100) =>
            Track(AgentRecordingStore.Create(root, new AgentRecordingOptions { MaxEvents = maxEvents }));

        private AgentRecordingStore Track(AgentRecordingStore store) {
            stores.Add(store);
            return store;
        }

        [Fact]
        public void EventsAreReadBackInOrderWithSequenceNumbers() {
            var store = NewStore();
            store.Append("mark", new JObject { ["source"] = "tool" });
            store.Append("output", new JObject { ["text"] = "hello" });
            store.Stop("user");

            var recording = AgentRecordingReader.ReadRecording(store.Directory, 0, 10);

            Assert.Equal("stopped", recording.Value<string>("status"));
            Assert.Equal(new[] { "mark", "output" }, recording["events"].Select(e => e.Value<string>("kind")));
            Assert.Equal(new[] { 1, 2 }, recording["events"].Select(e => e.Value<int>("seq")));
            Assert.Equal("tool", recording["events"][0].Value<string>("source"));
        }

        [Fact]
        public void EventsBeyondTheCapAreCountedAndNotStored() {
            var store = NewStore(maxEvents: 2);
            Assert.True(store.Append("a", null));
            Assert.True(store.Append("b", null));
            Assert.False(store.Append("c", null));
            var summary = store.Stop("user");

            Assert.Equal(2, summary.Value<int>("event_count"));
            Assert.Equal(1, summary.Value<int>("dropped_events"));
            Assert.Equal(2, AgentRecordingReader.ReadRecording(store.Directory, 0, 10).Value<int>("total_events"));
        }

        [Fact]
        public void EventsAfterTheMaximumDurationAreDroppedEvenBeforeStop() {
            var store = Track(AgentRecordingStore.Create(root, new AgentRecordingOptions { MaxDurationSeconds = 1 }));
            Assert.True(store.Append("early", null));
            System.Threading.Thread.Sleep(1100);

            Assert.False(store.Append("late", null));
            Assert.Equal(1, store.Stop("max_duration").Value<int>("dropped_events"));
        }

        [Fact]
        public void LargeMarkDataIsReplacedByAPreviewAndItsOriginalLength() {
            var large = "\"" + new string('x', AgentRecordingStore.MaxMarkLength) + "\"";

            var bounded = (JObject)AgentRecordingStore.ParseMarkData(large);

            Assert.True(bounded.Value<bool>("truncated"));
            Assert.Equal(large.Length, bounded.Value<int>("original_length"));
            Assert.Equal(AgentRecordingStore.MaxTextLength, bounded.Value<string>("preview").Length);
            Assert.Equal(1, AgentRecordingStore.ParseMarkData("{\"a\":1}").Value<int>("a"));
            Assert.Equal("not json", AgentRecordingStore.ParseMarkData("not json").Value<string>());
            Assert.Equal(JTokenType.Null, AgentRecordingStore.ParseMarkData(null).Type);
        }

        [Fact]
        public void PruneNeverDeletesARecordingAnotherHostIsStillWriting() {
            var live = NewStore();
            for (var i = 0; i < AgentRecordingStore.MaxRecordings + 1; i++)
                Directory.CreateDirectory(Path.Combine(root, "29990101-0000" + i.ToString("D2") + "-id" + i));

            AgentRecordingStore.Prune(root, DateTime.Now, null);

            Assert.True(Directory.Exists(live.Directory));
            Assert.True(live.Append("still", null));
            live.Stop("user");
        }

        [Fact]
        public void ARecordingStillHeldByAWriterIsReportedAsRecordingWithItsEventCount() {
            var store = NewStore();
            store.Append("a", null);
            store.Append("b", null);

            var recording = AgentRecordingReader.ReadRecording(store.Directory, 0, 10);

            Assert.Equal("recording", recording.Value<string>("status"));
            Assert.Equal(2, recording.Value<int>("event_count"));
            Assert.NotNull(recording["started"]);
        }

        [Fact]
        public void APageStopsAtTheSizeCapAndPointsToTheNextOffset() {
            var store = NewStore();
            for (var i = 0; i < 5; i++)
                store.Append("e", new JObject { ["text"] = new string('x', 1000) });
            store.Stop("user");

            var page = AgentRecordingReader.ReadRecording(store.Directory, 0, 100, maxChars: 2500);

            Assert.Equal(2, page["events"].Count());
            Assert.Equal(2, page.Value<int>("next_offset"));
            Assert.True(page.Value<bool>("truncated"));
        }

        [Fact]
        public void ErrorStringsAreBoundedAndOtherFieldsKept() {
            var error = new JObject {
                ["type"] = "ValueError",
                ["traceback"] = new string('t', AgentRecordingStore.MaxTextLength * 3),
                ["line"] = 7,
            };

            var bounded = (JObject)AgentRecordingStore.BoundError(error);

            Assert.Equal("ValueError", bounded.Value<string>("type"));
            Assert.True(bounded.Value<string>("traceback").Length < AgentRecordingStore.MaxTextLength + 64);
            Assert.Equal(7, bounded.Value<int>("line"));
            Assert.Equal(JTokenType.Null, AgentRecordingStore.BoundError(JValue.CreateNull()).Type);
        }

        [Fact]
        public void OutputBufferMergesWritesAndDrainsOnce() {
            var buffer = new AgentOutputBuffer();
            buffer.Add("one\n");
            buffer.Add("two\n");

            Assert.Equal("one\ntwo\n", buffer.Drain());
            Assert.Null(buffer.Drain());
        }

        [Fact]
        public void NothingIsAppendedAfterStop() {
            var store = NewStore();
            store.Stop("user");

            Assert.False(store.Append("late", null));
        }

        [Fact]
        public void ARecordingWithoutSummaryIsReportedIncompleteAndStillReadable() {
            var store = NewStore();
            store.Append("a", null);
            store.Stop("test");
            File.Delete(Path.Combine(store.Directory, "recording.json"));

            var recording = AgentRecordingReader.ReadRecording(store.Directory, 0, 10);

            Assert.Equal("incomplete", recording.Value<string>("status"));
            Assert.Equal(store.Id, recording.Value<string>("id"));
            Assert.Single(recording["events"]);
        }

        [Fact]
        public void APartialLastLineAndACorruptSummaryDoNotBreakReading() {
            var store = NewStore();
            store.Append("a", null);
            store.Stop("test");
            File.AppendAllText(Path.Combine(store.Directory, "events.jsonl"), "{\"seq\": 2, \"ki");
            File.WriteAllText(Path.Combine(store.Directory, "recording.json"), "{ truncated");

            var recording = AgentRecordingReader.ReadRecording(store.Directory, 0, 10);

            Assert.Equal("incomplete", recording.Value<string>("status"));
            Assert.Single(recording["events"]);
            Assert.Single(AgentRecordingReader.List(root, 10));
        }

        [Fact]
        public void ARecordingCanBeReadWhileItIsStillWriting() {
            var store = NewStore();
            store.Append("a", null);

            var recording = AgentRecordingReader.ReadRecording(store.Directory, 0, 10);

            Assert.Single(recording["events"]);
            Assert.True(store.Append("b", null));
        }

        [Fact]
        public void ARefundedScreenshotDoesNotCountAgainstTheMaximum() {
            var throttle = new AgentScreenshotThrottle(TimeSpan.FromSeconds(1), maxCount: 1);
            Assert.True(throttle.TryAcquire(TimeSpan.FromSeconds(0)));
            throttle.Refund();

            Assert.True(throttle.TryAcquire(TimeSpan.FromSeconds(2)));
            Assert.False(throttle.TryAcquire(TimeSpan.FromSeconds(4)));
        }

        [Fact]
        public void OffsetAndLimitPageTheTimelineAndFlagTruncation() {
            var store = NewStore();
            for (var i = 0; i < 5; i++)
                store.Append("e", new JObject { ["n"] = i });
            store.Stop("user");

            var page = AgentRecordingReader.ReadRecording(store.Directory, 1, 2);

            Assert.Equal(new[] { 1, 2 }, page["events"].Select(e => e.Value<int>("n")));
            Assert.Equal(5, page.Value<int>("total_events"));
            Assert.True(page.Value<bool>("truncated"));
            Assert.False(AgentRecordingReader.ReadRecording(store.Directory, 3, 10).Value<bool>("truncated"));
        }

        [Fact]
        public void LongTextIsTruncatedWithTheDroppedLength() {
            var text = new string('x', AgentRecordingStore.MaxTextLength + 10);

            var truncated = AgentRecordingStore.Truncate(text);

            Assert.StartsWith(new string('x', AgentRecordingStore.MaxTextLength), truncated);
            Assert.EndsWith("[10 more characters]", truncated);
            Assert.Equal("short", AgentRecordingStore.Truncate("short"));
        }

        [Fact]
        public void FindDirectoryMatchesAnIdAndRejectsWildcardsAndPaths() {
            var store = NewStore();

            Assert.Equal(store.Directory, AgentRecordingReader.FindDirectory(root, store.Id));
            Assert.Null(AgentRecordingReader.FindDirectory(root, "*"));
            Assert.Null(AgentRecordingReader.FindDirectory(root, "..\\x"));
            Assert.Null(AgentRecordingReader.FindDirectory(root, null));
        }

        [Fact]
        public void PruneRemovesExpiredRecordingsAndKeepsTheActiveOne() {
            var old = NewStore();
            old.Stop("user");
            var active = NewStore();
            var expired = DateTime.Now - AgentRecordingStore.Retention - TimeSpan.FromDays(1);
            Directory.SetLastWriteTime(old.Directory, expired);
            Directory.SetLastWriteTime(active.Directory, expired);

            var removed = AgentRecordingStore.Prune(root, DateTime.Now, active.Directory);

            Assert.Equal(1, removed);
            Assert.False(Directory.Exists(old.Directory));
            Assert.True(Directory.Exists(active.Directory));
        }

        [Fact]
        public void PruneKeepsOnlyTheNewestRecordingsBeyondTheCount() {
            for (var i = 0; i < AgentRecordingStore.MaxRecordings + 3; i++)
                Directory.CreateDirectory(Path.Combine(root, "20260101-0000" + i.ToString("D2") + "-id" + i));

            var removed = AgentRecordingStore.Prune(root, DateTime.Now, null);

            Assert.Equal(3, removed);
            Assert.Equal(AgentRecordingStore.MaxRecordings, Directory.GetDirectories(root).Length);
        }

        [Fact]
        public void OptionsHaveBoundedDefaultsAndRejectOutOfRangeValues() {
            var defaults = AgentRecordingOptions.FromJson(new JObject());
            Assert.True(defaults.Screenshots);
            Assert.Equal(20, defaults.MaxScreenshots);

            var configured = AgentRecordingOptions.FromJson(new JObject { ["screenshots"] = false, ["max_screenshots"] = 3 });
            Assert.False(configured.Screenshots);
            Assert.Equal(3, configured.MaxScreenshots);

            Assert.Equal("invalid_params", Assert.Throws<AgentException>(
                () => AgentRecordingOptions.FromJson(new JObject { ["max_events"] = 1000000 })).Code);
            Assert.Equal("invalid_params", Assert.Throws<AgentException>(
                () => AgentRecordingOptions.FromJson(new JObject { ["max_screenshots"] = "many" })).Code);
            Assert.Equal("invalid_params", Assert.Throws<AgentException>(
                () => AgentRecordingOptions.FromJson(new JObject { ["max_duration_s"] = 1.9 })).Code);
            Assert.Equal(2.5, AgentRecordingOptions.FromJson(new JObject { ["screenshot_interval_s"] = 2.5 }).ScreenshotIntervalSeconds);
            Assert.Equal(60, AgentRecordingOptions.FromJson(new JObject { ["max_duration_s"] = 60.0 }).MaxDurationSeconds);
        }

        [Fact]
        public void ThrottleEnforcesTheIntervalAndTheMaximumCount() {
            var throttle = new AgentScreenshotThrottle(TimeSpan.FromSeconds(5), maxCount: 2);

            Assert.True(throttle.TryAcquire(TimeSpan.FromSeconds(0)));
            Assert.False(throttle.TryAcquire(TimeSpan.FromSeconds(4)));
            Assert.True(throttle.TryAcquire(TimeSpan.FromSeconds(5)));
            Assert.False(throttle.TryAcquire(TimeSpan.FromSeconds(60)));
            Assert.Equal(2, throttle.Taken);
        }
    }
}
