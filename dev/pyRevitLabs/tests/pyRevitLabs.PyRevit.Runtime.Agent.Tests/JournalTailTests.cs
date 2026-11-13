using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class JournalTailTests : IDisposable {
        private readonly string _path = Path.Combine(Path.GetTempPath(), "journal-tail-" + Guid.NewGuid().ToString("N") + ".txt");

        public void Dispose() {
            if (File.Exists(_path))
                File.Delete(_path);
        }

        private void Append(string text) {
            AppendBytes(Encoding.UTF8.GetBytes(text), 0, Encoding.UTF8.GetByteCount(text));
        }

        private void AppendBytes(byte[] bytes, int offset, int count) {
            using var stream = new FileStream(_path, FileMode.Append, FileAccess.Write, FileShare.ReadWrite);
            stream.Write(bytes, offset, count);
        }

        private static string[] ReadAll(JournalTail tail) {
            var lines = new List<string>();
            for (int i = 0; i < 10; i++)
                lines.AddRange(tail.ReadNewLines());
            return lines.ToArray();
        }

        [Fact]
        public void ExistingContentIsSkipped() {
            File.WriteAllText(_path, "old line\r\n");
            var tail = new JournalTail(_path);

            Assert.Empty(tail.ReadNewLines());

            Append("new line\r\n");
            Assert.Equal(new[] { "new line" }, tail.ReadNewLines());
        }

        [Fact]
        public void LineSplitAcrossReadsIsDeliveredOnceWhole() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append(" Jrn.Command \"Ribbon\" , \"x\" , ID_");
            Assert.Empty(tail.ReadNewLines());

            Append("CMD\r\n");
            Assert.Equal(new[] { " Jrn.Command \"Ribbon\" , \"x\" , ID_CMD" }, tail.ReadNewLines());
            Assert.Empty(tail.ReadNewLines());
        }

        [Fact]
        public void LineBreakSplitBetweenCarriageReturnAndLineFeedYieldsNoEmptyLine() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append("first\r");
            Assert.Empty(tail.ReadNewLines());

            Append("\nsecond\r\n");
            Assert.Equal(new[] { "first", "second" }, tail.ReadNewLines());
        }

        [Fact]
        public void BlankLinesArePreserved() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append("a\r\n\r\nb\n");
            Assert.Equal(new[] { "a", "", "b" }, tail.ReadNewLines());
        }

        [Fact]
        public void LinesBeyondTheChunkLimitAreDeliveredOnLaterReads() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 8);

            Append("aaa\nbbb\nccc\nddd\n");
            Assert.Equal(new[] { "aaa", "bbb" }, tail.ReadNewLines());
            Assert.Equal(new[] { "ccc", "ddd" }, tail.ReadNewLines());
        }

        [Fact]
        public void ChunkWithoutLineFeedAtTheLimitIsDiscardedSoReadingContinues() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("xxxxxxxx");
            Assert.Empty(tail.ReadNewLines());
            Assert.Empty(tail.ReadNewLines());

            Append("\nok\n");
            Assert.Equal(new[] { "ok" }, ReadAll(tail));
        }

        [Fact]
        public void OversizedLineEndingPartwayThroughALaterChunkDoesNotLeakItsTail() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcdef\n" + "ok\n");
            Assert.Equal(new[] { "ok" }, ReadAll(tail));
        }

        [Fact]
        public void OversizedLineEndingExactlyAtAChunkBoundaryDoesNotLeakAnEmptyLine() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcd\n" + "ok\n");
            Assert.Equal(new[] { "ok" }, ReadAll(tail));
        }

        [Fact]
        public void SeveralConsecutiveOversizedChunksAreAllDiscarded() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcdefghijkl");
            Assert.Empty(tail.ReadNewLines());
            Assert.Empty(tail.ReadNewLines());
            Assert.Empty(tail.ReadNewLines());

            Append("mn\n" + "ok\n");
            Assert.Equal(new[] { "ok" }, ReadAll(tail));
        }

        [Fact]
        public void DiscardEndsWhenTheFileIsTruncated() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcdefgh");
            Assert.Empty(tail.ReadNewLines());

            File.WriteAllText(_path, "x\n");
            Assert.Equal(new[] { "x" }, tail.ReadNewLines());
        }

        [Fact]
        public void FileReplacedByAShorterOneAfterPartialLineIsReadFromTheStart() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append("a long unfinished line without a break");
            Assert.Empty(tail.ReadNewLines());

            File.WriteAllText(_path, "new\n");
            Assert.Equal(new[] { "new" }, tail.ReadNewLines());
        }

        [Fact]
        public void MultiByteCharacterSplitAcrossReadsIsDecodedIntact() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);
            var bytes = Encoding.UTF8.GetBytes("café\r\n");

            AppendBytes(bytes, 0, 4);
            Assert.Empty(tail.ReadNewLines());

            AppendBytes(bytes, 4, bytes.Length - 4);
            Assert.Equal(new[] { "café" }, tail.ReadNewLines());
        }

        [Fact]
        public void TruncatedFileIsReadFromTheStart() {
            File.WriteAllText(_path, "a long first generation of journal text\r\n");
            var tail = new JournalTail(_path);

            File.WriteAllText(_path, "fresh\r\n");
            Assert.Equal(new[] { "fresh" }, tail.ReadNewLines());
        }

        [Fact]
        public void MissingFileYieldsNothingAndPicksUpLaterContent() {
            var tail = new JournalTail(_path);
            Assert.Empty(tail.ReadNewLines());

            Append("late\r\n");
            Assert.Equal(new[] { "late" }, tail.ReadNewLines());
        }
    }
}
