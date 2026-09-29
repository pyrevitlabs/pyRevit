using System.Text;

using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester;

/// <summary>
/// Covers the contract <c>readline</c> owes an interactive interpreter: a line with no trailing
/// padding, and an empty string at end of input.
///
/// It drove <c>pdb</c> under CPython: a line came back padded with NULs, which pdb could not
/// compile, and a closed output window returned 1024 NULs instead of "" - so pdb never saw
/// end-of-input and looped until Revit died. #3686.
/// </summary>
[TestFixture]
public class ScriptIoReadlineTests {
    /// <summary>
    /// Stands in for the output window. Mirrors the real <c>Read</c> handshake: a read that
    /// returns a line raises a flag, and the next read consumes that flag and returns nothing.
    /// <c>readline</c> depends on that handshake to consume one line per call.
    /// </summary>
    private sealed class ScriptIoWithQueuedInput : ScriptIO {
        private readonly Queue<string> _pending = new();
        private readonly int _eofResult;
        private bool _inputReceived;

        public ScriptIoWithQueuedInput(int eofResult, params string[] lines)
            : base((ScriptRuntime)null) {
            _eofResult = eofResult;
            foreach (string line in lines) {
                _pending.Enqueue(line);
            }
        }

        public override int Read(byte[] buffer, int offset, int count) {
            if (_inputReceived) {
                _inputReceived = false;
                return 0;
            }

            if (_pending.Count == 0)
                return _eofResult;

            byte[] bytes = OutputEncoding.GetBytes(_pending.Dequeue());
            _inputReceived = true;
            int copyCount = Math.Min(bytes.Length, count);
            Buffer.BlockCopy(bytes, 0, buffer, offset, copyCount);
            return bytes.Length;
        }
    }

    [Test]
    public void Readline_ReturnsTheLineWithoutPadding() {
        var io = new ScriptIoWithQueuedInput(0, "p x = 1");

        Assert.That(io.readline(), Is.EqualTo("p x = 1"));
    }

    [Test]
    public void Readline_ReturnsTheLineExactly_NotTheWholeBuffer() {
        var io = new ScriptIoWithQueuedInput(0, "n");

        // A 1024-byte buffer is always allocated, so anything past the line is still NUL.
        string line = io.readline();

        Assert.That(line, Is.EqualTo("n"));
        Assert.That(line, Has.Length.EqualTo(1));
    }

    [Test]
    public void Readline_ReadsEachQueuedLineOnce() {
        var io = new ScriptIoWithQueuedInput(0, "first", "second");

        Assert.Multiple(() => {
            Assert.That(io.readline(), Is.EqualTo("first"));
            Assert.That(io.readline(), Is.EqualTo("second"));
        });
    }

    [Test]
    public void Readline_ReturnsEmptyStringAtEndOfInput() {
        var io = new ScriptIoWithQueuedInput(0);

        // Only "" reads as end-of-input; anything else keeps an interactive prompt spinning.
        Assert.That(io.readline(), Is.Empty);
    }

    [Test]
    public void Readline_ReturnsEmptyStringAfterAClosedOutputWindow() {
        var io = new ScriptIoWithQueuedInput(0, "disconnect");

        Assert.Multiple(() => {
            Assert.That(io.readline(), Is.EqualTo("disconnect"));
            Assert.That(io.readline(), Is.Empty);
        });
    }

    [Test]
    public void Readline_TreatsANegativeReadAsEndOfInput() {
        var io = new ScriptIoWithQueuedInput(-1);

        Assert.That(io.readline(), Is.Empty);
    }

    [Test]
    public void Readline_NeverReturnsNulCharacters() {
        var io = new ScriptIoWithQueuedInput(0, "p self.args", "", "q");

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
    public void Readline_HandlesNonAsciiInput() {
        var io = new ScriptIoWithQueuedInput(0, "réponse");

        string line = io.readline();

        Assert.That(line, Is.EqualTo("réponse"));
    }

    [Test]
    public void Readline_HonoursTheRequestedSize() {
        var io = new ScriptIoWithQueuedInput(0, "abcdefghij");

        Assert.That(io.readline(4), Is.EqualTo("abcd"));
    }

    [Test]
    public void Readline_WithASizeLargerThanTheLineIsUnaffected() {
        var io = new ScriptIoWithQueuedInput(0, "hi");

        Assert.That(io.readline(4096), Is.EqualTo("hi"));
    }

    [Test]
    public void Read_IsReadline() {
        var io = new ScriptIoWithQueuedInput(0, "input()");

        Assert.That(io.read(), Is.EqualTo("input()"));
    }
}
