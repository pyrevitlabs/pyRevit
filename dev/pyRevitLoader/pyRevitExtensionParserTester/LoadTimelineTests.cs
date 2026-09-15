using System.Diagnostics;
using pyRevitLabs.Common;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    [NonParallelizable]
    public class LoadTimelineTests
    {
        [TearDown]
        public void TearDown()
        {
            while (LoadTimeline.Active != null)
                LoadTimeline.Active.End();
        }

        [Test]
        public void BeginMakesTimelineActiveUntilEnded()
        {
            var timeline = LoadTimeline.Begin("load", Stopwatch.GetTimestamp());
            Assert.That(LoadTimeline.Active, Is.SameAs(timeline));

            timeline.End();

            Assert.That(LoadTimeline.Active, Is.Null);
            Assert.That(timeline.IsEnded, Is.True);
        }

        [Test]
        public void StartSpanNestsUnderInnermostOpenSpan()
        {
            var timeline = LoadTimeline.Begin("load", Stopwatch.GetTimestamp());

            var outer = timeline.StartSpan("outer");
            var inner = timeline.StartSpan("inner");
            inner.End();
            var sibling = timeline.StartSpan("sibling");
            sibling.End();
            outer.End();
            var next = timeline.StartSpan("next");

            Assert.That(timeline.Root.Children, Is.EqualTo(new[] { outer, next }));
            Assert.That(outer.Children, Is.EqualTo(new[] { inner, sibling }));
        }

        [Test]
        public void EndingOuterSpanClosesSpansLeftOpenInsideIt()
        {
            var timeline = LoadTimeline.Begin("load", Stopwatch.GetTimestamp());
            var outer = timeline.StartSpan("outer");
            var inner = timeline.StartSpan("inner");

            outer.End();
            var next = timeline.StartSpan("next");

            Assert.That(inner.IsEnded, Is.True);
            Assert.That(inner.EndTimestamp, Is.EqualTo(outer.EndTimestamp));
            Assert.That(next.Parent, Is.SameAs(timeline.Root));
        }

        [Test]
        public void EndingSpanTwiceKeepsFirstDuration()
        {
            var timeline = LoadTimeline.Begin("load", Stopwatch.GetTimestamp());
            var span = timeline.StartSpan("step");

            var first = span.End();
            Thread.Sleep(20);

            Assert.That(span.End(), Is.EqualTo(first));
        }

        [Test]
        public void BeginDuringUnfinishedLoadMarksItReplaced()
        {
            var outer = LoadTimeline.Begin("outer", Stopwatch.GetTimestamp());
            var inner = LoadTimeline.Begin("inner", Stopwatch.GetTimestamp());

            outer.End();

            Assert.That(outer.IsReplaced, Is.True);
            Assert.That(inner.IsReplaced, Is.False);
            Assert.That(LoadTimeline.Active, Is.SameAs(inner));
        }

        [Test]
        public void BeginAfterLoadEndedDoesNotMarkItReplaced()
        {
            var first = LoadTimeline.Begin("first", Stopwatch.GetTimestamp());
            first.End();

            LoadTimeline.Begin("second", Stopwatch.GetTimestamp());

            Assert.That(first.IsReplaced, Is.False);
        }

        [Test]
        public void SpansStartedAfterEndAreNotAttached()
        {
            var timeline = LoadTimeline.Begin("load", Stopwatch.GetTimestamp());
            timeline.End();

            var late = timeline.StartSpan("late");
            late.End();

            Assert.That(timeline.Root.Children, Is.Empty);
            Assert.That(late.IsEnded, Is.True);
        }

        [Test]
        public void UnaccountedTimeExcludesTopLevelSteps()
        {
            var second = Stopwatch.Frequency;
            var start = Stopwatch.GetTimestamp() - 10 * second;
            var timeline = LoadTimeline.Begin("load", start);

            timeline.RecordSpan("step", start, start + 6 * second);
            timeline.End();

            Assert.That(
                timeline.UnaccountedMilliseconds,
                Is.EqualTo(timeline.ElapsedMilliseconds - 6000.0).Within(0.001));
        }

        [Test]
        public void RecordSpanAttachesUnderInnermostOpenSpan()
        {
            var second = Stopwatch.Frequency;
            var start = Stopwatch.GetTimestamp();
            var timeline = LoadTimeline.Begin("load", start);
            var step = timeline.StartSpan("step");

            var recorded = timeline.RecordSpan("recorded", start, start + second);

            Assert.That(recorded.Parent, Is.SameAs(step));
            Assert.That(recorded.ElapsedMilliseconds, Is.EqualTo(1000.0).Within(0.001));
        }
    }
}
