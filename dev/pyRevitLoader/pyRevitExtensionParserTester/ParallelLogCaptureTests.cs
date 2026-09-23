using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using NUnit.Framework;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitExtensionParserTester
{
    [TestFixture]
    public class ParallelLogCaptureTests
    {
        private sealed class RecordingLogger : ILogger
        {
            internal readonly List<string> Lines = new List<string>();

            public void Info(string message) => Lines.Add("INFO " + message);
            public void Debug(string message) => Lines.Add("DEBUG " + message);
            public void Error(string message) => Lines.Add("ERROR " + message);
            public void Warning(string message) => Lines.Add("WARNING " + message);
        }

        private static List<(CapturedLogLevel Level, string Message)> NewBuffer()
        {
            return new List<(CapturedLogLevel Level, string Message)>();
        }

        [Test]
        public void TryCaptureReportsNotCapturingOutsideAScope()
        {
            Assert.That(ParallelLogCapture.TryCapture(CapturedLogLevel.Debug, "loose"), Is.False);
        }

        [Test]
        public void CaptureRedirectsInsideTheScopeAndStopsAfterIt()
        {
            var buffer = NewBuffer();
            using (ParallelLogCapture.Begin(buffer))
            {
                Assert.That(ParallelLogCapture.TryCapture(CapturedLogLevel.Info, "inside"), Is.True);
            }

            Assert.That(ParallelLogCapture.TryCapture(CapturedLogLevel.Info, "outside"), Is.False);
            Assert.That(buffer.Select(r => r.Message), Is.EqualTo(new[] { "inside" }));
        }

        [Test]
        public void ReplayPreservesOrderAndLevel()
        {
            var buffer = NewBuffer();
            using (ParallelLogCapture.Begin(buffer))
            {
                ParallelLogCapture.TryCapture(CapturedLogLevel.Info, "created");
                ParallelLogCapture.TryCapture(CapturedLogLevel.Debug, "timing");
                ParallelLogCapture.TryCapture(CapturedLogLevel.Warning, "skipped");
                ParallelLogCapture.TryCapture(CapturedLogLevel.Error, "failed");
            }

            var logger = new RecordingLogger();
            ParallelLogCapture.Replay(logger, buffer);

            Assert.That(logger.Lines, Is.EqualTo(new[]
            {
                "INFO created",
                "DEBUG timing",
                "WARNING skipped",
                "ERROR failed",
            }));
        }

        [Test]
        public void ReplayToleratesNullRecords()
        {
            var logger = new RecordingLogger();
            Assert.DoesNotThrow(() => ParallelLogCapture.Replay(logger, null));
            Assert.That(logger.Lines, Is.Empty);
        }

        [Test]
        public void ParallelWorkReplaysInIndexOrderNotCompletionOrder()
        {
            const int items = 12;
            var buffers = new List<(CapturedLogLevel Level, string Message)>[items];

            Parallel.For(0, items, i =>
            {
                var captured = NewBuffer();
                buffers[i] = captured;
                using (ParallelLogCapture.Begin(captured))
                {
                    System.Threading.Thread.Sleep((items - i) * 5);
                    ParallelLogCapture.TryCapture(CapturedLogLevel.Info, "created-" + i);
                    ParallelLogCapture.TryCapture(CapturedLogLevel.Debug, "timing-" + i);
                }
            });

            var logger = new RecordingLogger();
            foreach (var buffer in buffers)
                ParallelLogCapture.Replay(logger, buffer);

            var expected = Enumerable.Range(0, items)
                .SelectMany(i => new[] { "INFO created-" + i, "DEBUG timing-" + i })
                .ToArray();
            Assert.That(logger.Lines, Is.EqualTo(expected));
        }

        [Test]
        public void EachThreadCapturesIntoItsOwnBuffer()
        {
            const int threads = 8;
            var buffers = new List<(CapturedLogLevel Level, string Message)>[threads];

            Parallel.For(0, threads, i =>
            {
                var captured = NewBuffer();
                buffers[i] = captured;
                using (ParallelLogCapture.Begin(captured))
                {
                    for (var n = 0; n < 50; n++)
                        ParallelLogCapture.TryCapture(CapturedLogLevel.Debug, i + ":" + n);
                }
            });

            for (var i = 0; i < threads; i++)
            {
                Assert.That(buffers[i], Has.Count.EqualTo(50));
                Assert.That(
                    buffers[i].All(r => r.Message.StartsWith(i + ":")),
                    Is.True,
                    "buffer " + i + " picked up another worker's records");
            }
        }
    }
}
