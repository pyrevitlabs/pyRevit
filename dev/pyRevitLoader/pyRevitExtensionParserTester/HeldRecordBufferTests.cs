using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using NUnit.Framework;
using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class HeldRecordBufferTests
    {
        [Test]
        public void DrainReturnsRecordsOldestFirst()
        {
            var buffer = new HeldRecordBuffer(10);
            buffer.Hold("first", markError: false);
            buffer.Hold("second", markError: true);
            buffer.Hold("third", markError: false);

            int dropped;
            var released = buffer.Drain(out dropped);

            Assert.That(dropped, Is.EqualTo(0));
            Assert.That(released.Select(r => r.Content), Is.EqualTo(new[] { "first", "second", "third" }));
            Assert.That(released[1].MarkError, Is.True);
            Assert.That(released[0].MarkError, Is.False);
        }

        [Test]
        public void DrainEmptiesTheBuffer()
        {
            var buffer = new HeldRecordBuffer(10);
            buffer.Hold("only", markError: false);

            int dropped;
            buffer.Drain(out dropped);

            Assert.That(buffer.Count, Is.EqualTo(0));
            Assert.That(buffer.Drain(out dropped), Is.Empty);
            Assert.That(dropped, Is.EqualTo(0));
        }

        [Test]
        public void EmptyDrainIsDistinguishableFromADrainThatReportsDrops()
        {
            var buffer = new HeldRecordBuffer(1);
            buffer.Hold("evicted", markError: false);
            buffer.Hold("kept", markError: false);

            int dropped;
            var released = buffer.Drain(out dropped);

            Assert.That(dropped, Is.EqualTo(1));
            Assert.That(released.Select(r => r.Content), Is.EqualTo(new[] { "kept" }));
        }

        [Test]
        public void OverflowDiscardsOldestAndCountsEveryLoss()
        {
            var buffer = new HeldRecordBuffer(3);
            for (var i = 0; i < 10; i++)
                buffer.Hold("record-" + i, markError: false);

            Assert.That(buffer.Count, Is.EqualTo(3));

            int dropped;
            var released = buffer.Drain(out dropped);

            Assert.That(dropped, Is.EqualTo(7));
            Assert.That(
                released.Select(r => r.Content),
                Is.EqualTo(new[] { "record-7", "record-8", "record-9" }));
        }

        [Test]
        public void DropCountSurvivesUntilTheNextDrainReportsIt()
        {
            var buffer = new HeldRecordBuffer(1);
            buffer.Hold("a", markError: false);
            buffer.Hold("b", markError: false);

            int dropped;
            buffer.Drain(out dropped);
            Assert.That(dropped, Is.EqualTo(1));

            buffer.Drain(out dropped);
            Assert.That(dropped, Is.EqualTo(0), "a reported drop count must not be reported twice");
        }

        [Test]
        public void BuffersAreIndependentOfEachOther()
        {
            var session = new HeldRecordBuffer(10);
            var command = new HeldRecordBuffer(10);
            session.Hold("session-record", markError: false);

            int dropped;
            Assert.That(command.Drain(out dropped), Is.Empty);
            Assert.That(dropped, Is.EqualTo(0));
            Assert.That(session.Count, Is.EqualTo(1));
        }

        [Test]
        public void ConcurrentHoldsKeepEveryRecordAndStayWithinCapacity()
        {
            const int capacity = 500;
            const int writers = 8;
            const int perWriter = 250;
            var buffer = new HeldRecordBuffer(capacity);

            Parallel.For(0, writers, w =>
            {
                for (var i = 0; i < perWriter; i++)
                    buffer.Hold("w" + w + "-" + i, markError: false);
            });

            Assert.That(buffer.Count, Is.EqualTo(capacity));

            int dropped;
            var released = buffer.Drain(out dropped);
            Assert.That(
                released.Length + dropped,
                Is.EqualTo(writers * perWriter),
                "every held record must be either released or counted as dropped");
        }
    }
}
