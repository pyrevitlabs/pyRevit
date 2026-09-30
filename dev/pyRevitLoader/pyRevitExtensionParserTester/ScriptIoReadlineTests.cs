using System.Collections.Generic;
using System.Text;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// The contract <c>readline</c> owes an interactive interpreter: the line it read, an empty
    /// string at end of input, and a size limit that neither drops nor splits input.
    ///
    /// It drove <c>pdb</c> under CPython. A line came back padded with NULs, which pdb could not
    /// compile, and a closed output window returned 1024 NULs instead of an empty string, so pdb
    /// never saw end-of-input and looped until Revit died. #3686.
    /// </summary>
    [TestFixture]
    public class ScriptIoReadlineTests
    {
        /// <summary>
        /// Stands in for the output window: hands out queued lines, or <c>null</c> once the queue
        /// drains. Overriding only the line source means the stream's own handshake, size
        /// handling and leftover buffering all run for real.
        /// </summary>
        private sealed class ScriptIoWithQueuedInput : ScriptIO
        {
            private readonly Queue<string> _pending = new Queue<string>();

            public ScriptIoWithQueuedInput(params string[] lines)
                : base((ScriptRuntime)null)
            {
                foreach (string line in lines)
                {
                    _pending.Enqueue(line);
                }
            }

            protected override string ReadNextLine()
            {
                return _pending.Count == 0 ? null : _pending.Dequeue();
            }
        }

        [Test]
        public void Readline_ReturnsTheLineWithoutPadding()
        {
            var io = new ScriptIoWithQueuedInput("p x = 1");

            Assert.That(io.readline(), Is.EqualTo("p x = 1"));
        }

        [Test]
        public void Readline_ReturnsTheLineExactly_NotTheWholeBuffer()
        {
            var io = new ScriptIoWithQueuedInput("n");
            string line = io.readline();

            Assert.That(line, Is.EqualTo("n"));
            Assert.That(line, Has.Length.EqualTo(1));
        }

        [Test]
        public void Readline_ReadsEachQueuedLineOnce()
        {
            var io = new ScriptIoWithQueuedInput("first", "second");

            Assert.Multiple(() => {
                Assert.That(io.readline(), Is.EqualTo("first"));
                Assert.That(io.readline(), Is.EqualTo("second"));
            });
        }

        [Test]
        public void Readline_ReturnsEmptyStringAtEndOfInput()
        {
            var io = new ScriptIoWithQueuedInput();

            Assert.That(io.readline(), Is.Empty);
        }

        [Test]
        public void Readline_ReturnsEmptyStringAfterTheLastLine()
        {
            var io = new ScriptIoWithQueuedInput("disconnect");

            Assert.Multiple(() => {
                Assert.That(io.readline(), Is.EqualTo("disconnect"));
                Assert.That(io.readline(), Is.Empty);
            });
        }

        [Test]
        public void Readline_NeverReturnsNulCharacters()
        {
            var io = new ScriptIoWithQueuedInput("p self.args", "", "q");

            string first = io.readline();
            string empty = io.readline();
            string last = io.readline();

            Assert.Multiple(() => {
                Assert.That(first, Does.Not.Contain('\0'));
                Assert.That(empty, Does.Not.Contain('\0'));
                Assert.That(last, Does.Not.Contain('\0'));
            });
        }

        [Test]
        public void Readline_HandlesNonAsciiInput()
        {
            var io = new ScriptIoWithQueuedInput("réponse");

            Assert.That(io.readline(), Is.EqualTo("réponse"));
        }

        [Test]
        public void Readline_WithASizeLargerThanTheLineIsUnaffected()
        {
            var io = new ScriptIoWithQueuedInput("hi");

            Assert.That(io.readline(4096), Is.EqualTo("hi"));
        }

        [Test]
        public void Readline_ZeroSizeReturnsEmptyAndConsumesNothing()
        {
            var io = new ScriptIoWithQueuedInput("abcdefghij");

            Assert.Multiple(() => {
                Assert.That(io.readline(0), Is.Empty);
                Assert.That(io.readline(), Is.EqualTo("abcdefghij"));
            });
        }

        [Test]
        public void Readline_SizeLimitsTheCharactersReturned()
        {
            var io = new ScriptIoWithQueuedInput("abcdefghij");

            Assert.That(io.readline(4), Is.EqualTo("abcd"));
        }

        [Test]
        public void Readline_SizeLimitedReadKeepsTheRemainderForTheNextCall()
        {
            var io = new ScriptIoWithQueuedInput("abcdefghij", "next line");

            Assert.Multiple(() => {
                Assert.That(io.readline(4), Is.EqualTo("abcd"));
                Assert.That(io.readline(3), Is.EqualTo("efg"));
                Assert.That(io.readline(), Is.EqualTo("hij"));
                Assert.That(io.readline(), Is.EqualTo("next line"));
            });
        }

        [Test]
        public void Readline_SizeNeverSplitsAMultiByteCharacter()
        {
            var io = new ScriptIoWithQueuedInput("éé");

            Assert.Multiple(() => {
                Assert.That(io.readline(1), Is.EqualTo("é"));
                Assert.That(io.readline(), Is.EqualTo("é"));
            });
        }

        [Test]
        public void Readline_MixesWithRawReads()
        {
            var io = new ScriptIoWithQueuedInput("abcdefghij");
            var buffer = new byte[64];

            Assert.That(io.readline(4), Is.EqualTo("abcd"));

            int read = io.Read(buffer, 0, buffer.Length);
            Assert.That(Encoding.UTF8.GetString(buffer, 0, read), Is.EqualTo("efghij"));
        }

        [Test]
        public void Readline_HandlesALineLongerThanOneChunk()
        {
            string longLine = new string('x', 5000);
            var io = new ScriptIoWithQueuedInput(longLine, "after");

            Assert.Multiple(() => {
                Assert.That(io.readline(), Is.EqualTo(longLine));
                Assert.That(io.readline(), Is.EqualTo("after"));
            });
        }

        [Test]
        public void Readline_LongLineKeepsWorkingAfterASizeLimitedRead()
        {
            string longLine = new string('y', 3000);
            var io = new ScriptIoWithQueuedInput(longLine, "after");

            Assert.Multiple(() => {
                Assert.That(io.readline(10), Is.EqualTo(new string('y', 10)));
                Assert.That(io.readline(10), Is.EqualTo(new string('y', 10)));
                Assert.That(io.readline(), Is.EqualTo(new string('y', 2980)));
                Assert.That(io.readline(), Is.EqualTo("after"));
            });
        }

        /// <summary>
        /// A raw read that truncates must report what it copied, not the length of the line it
        /// took from: a consumer reads up to the return value and would otherwise read its own
        /// stale buffer, then get the same bytes again on the next read.
        /// </summary>
        [Test]
        public void Read_ThenReadline_PreserveTheUnreadBytesExactly()
        {
            var io = new ScriptIoWithQueuedInput("héllo wörld");
            var oneByte = new byte[1];

            int read = io.Read(oneByte, 0, 1);

            Assert.Multiple(() => {
                Assert.That(read, Is.EqualTo(1));
                Assert.That(io.readline(), Is.EqualTo("éllo wörld"),
                    "the byte consumed by Read was lost from the line");
            });
        }

        /// <summary>
        /// Pinning the count the <see cref="ScriptIO.Read"/> contract promises: the number of
        /// bytes written, never the size of the line behind them.
        /// </summary>
        [Test]
        public void Read_TruncatedByCount_ReportsOnlyTheBytesItCopied()
        {
            var io = new ScriptIoWithQueuedInput("abcdefghij");
            var buffer = new byte[64];

            int read = io.Read(buffer, 0, 4);

            Assert.Multiple(() => {
                Assert.That(read, Is.EqualTo(4));
                Assert.That(Encoding.UTF8.GetString(buffer, 0, read), Is.EqualTo("abcd"));
                Assert.That(io.readline(), Is.EqualTo("efghij"));
            });
        }

        /// <summary>
        /// A raw read that would cut a multi-byte character in half stops short of the cut
        /// instead, so the line it leaves behind still decodes whole.
        /// </summary>
        [Test]
        public void Read_StoppingInsideACharacter_LeavesTheLineDecodable()
        {
            var io = new ScriptIoWithQueuedInput("aéb");
            var buffer = new byte[64];

            int read = io.Read(buffer, 0, 2);

            Assert.Multiple(() => {
                Assert.That(read, Is.EqualTo(1));
                Assert.That(Encoding.UTF8.GetString(buffer, 0, read), Is.EqualTo("a"));
                Assert.That(io.readline(), Is.EqualTo("éb"));
            });
        }

        /// <summary>
        /// A buffer too narrow for the first character cannot take it without overrunning, so
        /// the read takes nothing and keeps the line rather than splitting the character.
        /// </summary>
        [Test]
        public void Read_WithNoRoomForTheFirstCharacter_KeepsTheLineBuffered()
        {
            var io = new ScriptIoWithQueuedInput("é");
            var oneByte = new byte[1];

            int read = io.Read(oneByte, 0, 1);

            Assert.Multiple(() => {
                Assert.That(read, Is.EqualTo(0));
                Assert.That(io.readline(), Is.EqualTo("é"));
            });
        }

        [Test]
        public void Read_IsReadline()
        {
            var io = new ScriptIoWithQueuedInput("input()");

            Assert.That(io.read(), Is.EqualTo("input()"));
        }

        /// <summary>
        /// A line taken by <c>readline</c> settles the pending raw-read handshake. If the flag
        /// survived, the next raw read would report end of input and the line after it would
        /// never be delivered.
        /// </summary>
        [Test]
        public void Read_AfterReadline_DeliversTheFollowingLine()
        {
            var io = new ScriptIoWithQueuedInput("first", "second", "third");
            var buffer = new byte[64];

            int firstRead = io.Read(buffer, 0, buffer.Length);

            Assert.Multiple(() => {
                Assert.That(Encoding.UTF8.GetString(buffer, 0, firstRead), Is.EqualTo("first"));
                Assert.That(io.readline(), Is.EqualTo("second"));
            });

            int thirdLineByteCount = io.Read(buffer, 0, buffer.Length);
            string thirdLine = Encoding.UTF8.GetString(buffer, 0, thirdLineByteCount);

            Assert.Multiple(() => {
                Assert.That(thirdLineByteCount, Is.EqualTo(5), "returns the bytes actually copied");
                Assert.That(thirdLine, Is.EqualTo("third"),
                    "the handshake swallowed a line the user had already entered");
            });
        }

        /// <summary>
        /// The reverse order: <c>readline</c> takes a line, and the raw read that follows
        /// reports end of input rather than skipping the line behind it.
        /// </summary>
        [Test]
        public void Read_AfterReadline_WithoutARawReadFirst_EndsCleanly()
        {
            var io = new ScriptIoWithQueuedInput("first", "second");
            var buffer = new byte[64];

            string first = io.readline();

            Assert.Multiple(() => {
                Assert.That(first, Is.EqualTo("first"));
                Assert.That(io.Read(buffer, 0, buffer.Length), Is.EqualTo(6));
                Assert.That(Encoding.UTF8.GetString(buffer, 0, 6), Is.EqualTo("second"));
            });
        }
    }
}
