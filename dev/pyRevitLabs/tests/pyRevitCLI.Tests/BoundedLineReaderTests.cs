using pyRevitLabs.Common;

namespace pyRevitCLI.Tests;

/// <summary>Line limits on the agent pipe and the MCP stdio stream (issue #3922).</summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class BoundedLineReaderTests {
    private static List<string> ReadAll(BoundedLineReader reader) {
        var lines = new List<string>();
        string line;
        while ((line = reader.ReadLine()) != null)
            lines.Add(line);
        return lines;
    }

    [Fact]
    public void LinesMatchTextReaderForNewlineDelimitedInput() {
        var reader = new BoundedLineReader(new StringReader("first\r\n\nsecond\nlast"), 16);

        Assert.Equal(new[] { "first", "", "second", "last" }, ReadAll(reader));
    }

    [Fact]
    public void LinesAcrossBufferBoundariesAreJoined() {
        var longLine = new string('a', 20000);
        var reader = new BoundedLineReader(new StringReader(longLine + "\nnext\n"), 20000);

        Assert.Equal(new[] { longLine, "next" }, ReadAll(reader));
    }

    [Fact]
    public void OverLongLineIsRefusedAndSkipped() {
        var reader = new BoundedLineReader(new StringReader(new string('a', 30000) + "\nnext\n"), 10);

        Assert.Throws<InvalidDataException>(() => reader.ReadLine());
        Assert.Equal("next", reader.ReadLine());
        Assert.Null(reader.ReadLine());
    }

    [Fact]
    public void LineAtTheLimitIsKept() {
        var reader = new BoundedLineReader(new StringReader("abcde\r\nabcdef\n"), 5);

        Assert.Equal("abcde", reader.ReadLine());
        Assert.Throws<InvalidDataException>(() => reader.ReadLine());
    }

    [Fact]
    public async Task LineFillingWholeStreamBuffersIsReturnedWithoutWaitingForMore() {
        var bytes = System.Text.Encoding.UTF8.GetBytes(new string('a', 2047) + "\n");

        Assert.Equal(2047, new BoundedLineReader(new StreamReader(new StreamThatFailsWhenDrained(bytes))).ReadLine().Length);
        Assert.Equal(2047, (await new BoundedLineReader(new StreamReader(new StreamThatFailsWhenDrained(bytes))).ReadLineAsync()).Length);
    }

    private sealed class StreamThatFailsWhenDrained : MemoryStream {
        public StreamThatFailsWhenDrained(byte[] bytes) : base(bytes) { }

        public override int Read(byte[] buffer, int offset, int count) {
            if (Position == Length)
                throw new IOException("Read past the request, like a pipe waiting for the next line.");
            return base.Read(buffer, offset, count);
        }

        public override int Read(Span<byte> buffer) {
            if (Position == Length)
                throw new IOException("Read past the request, like a pipe waiting for the next line.");
            return base.Read(buffer);
        }

        public override Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken) =>
            Task.FromResult(Read(buffer, offset, count));

        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default) =>
            new ValueTask<int>(Read(buffer.Span));
    }

    [Fact]
    public async Task AsyncReadsRefuseOverLongLinesToo() {
        var reader = new BoundedLineReader(new StringReader("ok\n" + new string('a', 30000)), 10);

        Assert.Equal("ok", await reader.ReadLineAsync());
        await Assert.ThrowsAsync<InvalidDataException>(() => reader.ReadLineAsync());
        Assert.Null(await reader.ReadLineAsync());
    }
}
