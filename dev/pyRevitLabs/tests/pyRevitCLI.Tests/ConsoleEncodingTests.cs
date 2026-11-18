using System.Text;

using pyRevitCLI;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class ConsoleEncodingTests {
    [Fact]
    public void RedirectedStreamReceivesUtf8BytesWithoutBom() {
        var stream = new MemoryStream();
        TextWriter installed = null;

        PyRevitCLIConsoleEncoding.ApplyForRedirectedStream(true, () => stream, writer => installed = writer);
        installed.Write("äöü");

        Assert.Equal(new byte[] { 0xC3, 0xA4, 0xC3, 0xB6, 0xC3, 0xBC }, stream.ToArray());
    }

    [Fact]
    public void InteractiveStreamIsLeftUntouched() {
        var opened = false;
        var installed = false;

        PyRevitCLIConsoleEncoding.ApplyForRedirectedStream(false, () => { opened = true; return new MemoryStream(); }, _ => installed = true);

        Assert.False(opened);
        Assert.False(installed);
    }
}
