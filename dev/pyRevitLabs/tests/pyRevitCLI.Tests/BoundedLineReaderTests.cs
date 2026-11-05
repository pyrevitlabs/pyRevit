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
    public async Task AsyncReadsRefuseOverLongLinesToo() {
        var reader = new BoundedLineReader(new StringReader("ok\n" + new string('a', 30000)), 10);

        Assert.Equal("ok", await reader.ReadLineAsync());
        await Assert.ThrowsAsync<InvalidDataException>(() => reader.ReadLineAsync());
        Assert.Null(await reader.ReadLineAsync());
    }
}
