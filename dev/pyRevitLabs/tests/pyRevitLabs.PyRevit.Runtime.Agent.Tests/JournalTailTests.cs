using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    /// <summary>Unit tests for the append-only reading contract of <see cref="JournalTail"/>.</summary>
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class JournalTailTests : IDisposable {
        private readonly string _path = Path.Combine(Path.GetTempPath(), "journal-tail-" + Guid.NewGuid().ToString("N") + ".txt");

        /// <summary>Deletes the temporary journal file created for the test.</summary>
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

        /// <summary>Appending to a file whose last line is unfinished at construction does not return that line's remainder.</summary>
        [Fact]
        public void PartialLineInProgressAtConstructionIsDropped() {
            File.WriteAllText(_path, "old prefix");
            var tail = new JournalTail(_path);

            Append("suffix\nnext\n");
            Assert.Equal(new[] { "next" }, ReadAll(tail));
        }

        /// <summary>Content ending with a line feed at construction does not trigger the partial-line discard.</summary>
        [Fact]
        public void CompleteLineAtConstructionDoesNotDropTheNextLine() {
            File.WriteAllText(_path, "old\n");
            var tail = new JournalTail(_path);

            Append("next\n");
            Assert.Equal(new[] { "next" }, ReadAll(tail));
        }

        /// <summary>Content present at construction is not returned; only later appends are.</summary>
        [Fact]
        public void ExistingContentIsSkipped() {
            File.WriteAllText(_path, "old line\r\n");
            var tail = new JournalTail(_path);

            Assert.Empty(tail.ReadNewLines());

            Append("new line\r\n");
            Assert.Equal(new[] { "new line" }, tail.ReadNewLines());
        }

        /// <summary>A line written across several reads is returned once, whole, after its line break arrives.</summary>
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

        /// <summary>A CRLF split across reads does not produce an empty line.</summary>
        [Fact]
        public void LineBreakSplitBetweenCarriageReturnAndLineFeedYieldsNoEmptyLine() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append("first\r");
            Assert.Empty(tail.ReadNewLines());

            Append("\nsecond\r\n");
            Assert.Equal(new[] { "first", "second" }, tail.ReadNewLines());
        }

        /// <summary>Blank lines are returned as empty entries.</summary>
        [Fact]
        public void BlankLinesArePreserved() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append("a\r\n\r\nb\n");
            Assert.Equal(new[] { "a", "", "b" }, tail.ReadNewLines());
        }

        /// <summary>Lines beyond the per-read chunk limit are returned by later reads.</summary>
        [Fact]
        public void LinesBeyondTheChunkLimitAreDeliveredOnLaterReads() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 8);

            Append("aaa\nbbb\nccc\nddd\n");
            Assert.Equal(new[] { "aaa", "bbb" }, tail.ReadNewLines());
            Assert.Equal(new[] { "ccc", "ddd" }, tail.ReadNewLines());
        }

        /// <summary>A full chunk without a line feed is discarded and reading resumes at the next line.</summary>
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

        /// <summary>The tail of an oversized line ending inside a later chunk is not returned.</summary>
        [Fact]
        public void OversizedLineEndingPartwayThroughALaterChunkDoesNotLeakItsTail() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcdef\n" + "ok\n");
            Assert.Equal(new[] { "ok" }, ReadAll(tail));
        }

        /// <summary>An oversized line ending exactly at a chunk boundary does not yield an empty line.</summary>
        [Fact]
        public void OversizedLineEndingExactlyAtAChunkBoundaryDoesNotLeakAnEmptyLine() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcd\n" + "ok\n");
            Assert.Equal(new[] { "ok" }, ReadAll(tail));
        }

        /// <summary>Consecutive chunks of one oversized line are all discarded.</summary>
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

        /// <summary>Truncating the file ends the discard state and reads from the start.</summary>
        [Fact]
        public void DiscardEndsWhenTheFileIsTruncated() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path, 4);

            Append("abcdefgh");
            Assert.Empty(tail.ReadNewLines());

            File.WriteAllText(_path, "x\n");
            Assert.Equal(new[] { "x" }, tail.ReadNewLines());
        }

        /// <summary>A shorter replacement file is read from the start, dropping the pending partial line.</summary>
        [Fact]
        public void FileReplacedByAShorterOneAfterPartialLineIsReadFromTheStart() {
            File.WriteAllText(_path, "");
            var tail = new JournalTail(_path);

            Append("a long unfinished line without a break");
            Assert.Empty(tail.ReadNewLines());

            File.WriteAllText(_path, "new\n");
            Assert.Equal(new[] { "new" }, tail.ReadNewLines());
        }

        /// <summary>A multi-byte character split across reads is decoded intact.</summary>
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

        /// <summary>A truncated file is read from the start.</summary>
        [Fact]
        public void TruncatedFileIsReadFromTheStart() {
            File.WriteAllText(_path, "a long first generation of journal text\r\n");
            var tail = new JournalTail(_path);

            File.WriteAllText(_path, "fresh\r\n");
            Assert.Equal(new[] { "fresh" }, tail.ReadNewLines());
        }

        /// <summary>A missing file yields nothing and content created later is read from the start.</summary>
        [Fact]
        public void MissingFileYieldsNothingAndPicksUpLaterContent() {
            var tail = new JournalTail(_path);
            Assert.Empty(tail.ReadNewLines());

            Append("late\r\n");
            Assert.Equal(new[] { "late" }, tail.ReadNewLines());
        }
    }
}
