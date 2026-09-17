using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

using NUnit.Framework;
using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class HeldRecordBufferTests
    {
        private static List<string> DrainAll(HeldRecordBuffer buffer, out int dropped)
        {
            var released = new List<string>();
            dropped = 0;
            while (true)
            {
                int batchDropped;
                var batch = buffer.DrainOrOpen(out batchDropped);
                if (batch.Length == 0 && batchDropped == 0)
                    return released;
                dropped += batchDropped;
                released.AddRange(batch.Select(r => r.Content));
            }
        }

        [Test]
        public void GateStartsClosedSoRecordsAreHeld()
        {
            var buffer = new HeldRecordBuffer(10);

            Assert.That(buffer.IsOpen, Is.False);
            Assert.That(buffer.TryHold("early", markError: false), Is.True);
            Assert.That(buffer.Count, Is.EqualTo(1));
        }

        [Test]
        public void DrainReturnsRecordsOldestFirstWithTheirErrorFlag()
        {
            var buffer = new HeldRecordBuffer(10);
            buffer.TryHold("first", markError: false);
            buffer.TryHold("second", markError: true);
            buffer.TryHold("third", markError: false);

            int dropped;
            var released = buffer.DrainOrOpen(out dropped);

            Assert.That(dropped, Is.EqualTo(0));
            Assert.That(released.Select(r => r.Content), Is.EqualTo(new[] { "first", "second", "third" }));
            Assert.That(released.Select(r => r.MarkError), Is.EqualTo(new[] { false, true, false }));
        }

        [Test]
        public void GateStaysClosedUntilADrainFindsNothing()
        {
            var buffer = new HeldRecordBuffer(10);
            buffer.TryHold("held", markError: false);

            int dropped;
            buffer.DrainOrOpen(out dropped);
            Assert.That(buffer.IsOpen, Is.False, "a drain that returned records must not open the gate");

            Assert.That(buffer.DrainOrOpen(out dropped), Is.Empty);
            Assert.That(buffer.IsOpen, Is.True);
            Assert.That(buffer.TryHold("live", markError: false), Is.False);
            Assert.That(buffer.Count, Is.EqualTo(0));
        }

        [Test]
        public void RecordHeldDuringReleaseComesOutAfterOlderRecords()
        {
            var buffer = new HeldRecordBuffer(10);
            buffer.TryHold("older-1", markError: false);
            buffer.TryHold("older-2", markError: false);

            int dropped;
            var firstBatch = buffer.DrainOrOpen(out dropped);
            Assert.That(buffer.TryHold("during-release", markError: false), Is.True,
                "a record arriving mid-release must wait rather than jump the backlog");
            var secondBatch = buffer.DrainOrOpen(out dropped);

            Assert.That(
                firstBatch.Concat(secondBatch).Select(r => r.Content),
                Is.EqualTo(new[] { "older-1", "older-2", "during-release" }));
            Assert.That(buffer.DrainOrOpen(out dropped), Is.Empty);
            Assert.That(buffer.IsOpen, Is.True);
        }

        [Test]
        public void CloseMakesRecordsWaitAgain()
        {
            var buffer = new HeldRecordBuffer(10);
            int dropped;
            buffer.DrainOrOpen(out dropped);
            Assert.That(buffer.TryHold("while-open", markError: false), Is.False);

            buffer.Close();

            Assert.That(buffer.IsOpen, Is.False);
            Assert.That(buffer.TryHold("after-close", markError: false), Is.True);
            Assert.That(DrainAll(buffer, out dropped), Is.EqualTo(new[] { "after-close" }));
        }

        [Test]
        public void OverflowDiscardsOldestAndCountsEveryLoss()
        {
            var buffer = new HeldRecordBuffer(3);
            for (var i = 0; i < 10; i++)
                buffer.TryHold("record-" + i, markError: false);

            Assert.That(buffer.Count, Is.EqualTo(3));

            int dropped;
            var released = DrainAll(buffer, out dropped);

            Assert.That(dropped, Is.EqualTo(7));
            Assert.That(released, Is.EqualTo(new[] { "record-7", "record-8", "record-9" }));
        }

        [Test]
        public void DropCountIsReportedOnce()
        {
            var buffer = new HeldRecordBuffer(1);
            buffer.TryHold("a", markError: false);
            buffer.TryHold("b", markError: false);

            int dropped;
            buffer.DrainOrOpen(out dropped);
            Assert.That(dropped, Is.EqualTo(1));

            buffer.DrainOrOpen(out dropped);
            Assert.That(dropped, Is.EqualTo(0), "a reported drop count must not be reported twice");
        }

        [Test]
        public void BuffersAreIndependentOfEachOther()
        {
            var session = new HeldRecordBuffer(10);
            var command = new HeldRecordBuffer(10);
            session.TryHold("session-record", markError: false);

            int dropped;
            Assert.That(command.DrainOrOpen(out dropped), Is.Empty);
            Assert.That(command.IsOpen, Is.True);
            Assert.That(session.IsOpen, Is.False);
            Assert.That(session.Count, Is.EqualTo(1));
        }

        [Test]
        public void ConcurrentWritersNeverStrandOrReorderRecordsAcrossTheGateOpening()
        {
            const int writers = 8;
            const int perWriter = 2000;
            var buffer = new HeldRecordBuffer(writers * perWriter);
            var writtenDirectly = new List<int>[writers];
            var released = new List<string>();

            var releaser = Task.Run(() =>
            {
                SpinWait.SpinUntil(() => buffer.Count >= 500);
                int dropped;
                released.AddRange(DrainAll(buffer, out dropped));
            });

            Parallel.For(0, writers, w =>
            {
                var direct = new List<int>();
                for (var i = 0; i < perWriter; i++)
                {
                    if (!buffer.TryHold(w + ":" + i, markError: false))
                        direct.Add(i);
                }
                writtenDirectly[w] = direct;
            });
            releaser.Wait();

            Assert.That(buffer.Count, Is.EqualTo(0), "a record was held after the gate opened and never released");

            for (var w = 0; w < writers; w++)
            {
                var releasedForWriter = released
                    .Where(r => r.StartsWith(w + ":"))
                    .Select(r => int.Parse(r.Substring(r.IndexOf(':') + 1)))
                    .ToList();
                var inOrder = releasedForWriter.Concat(writtenDirectly[w]).ToList();

                Assert.That(inOrder, Is.EqualTo(Enumerable.Range(0, perWriter)),
                    "writer " + w + " had a record come out ahead of an older one, or lost one");
            }
        }
    }
}
