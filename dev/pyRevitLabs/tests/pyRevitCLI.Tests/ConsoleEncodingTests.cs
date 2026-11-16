using System.Text;

using pyRevitCLI;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class ConsoleEncodingTests {
    [Fact]
    public void RedirectedOutputIsSwitchedToUtf8WithoutBom() {
        Encoding chosen = null;

        PyRevitCLIConsoleEncoding.ApplyForRedirectedOutput(true, encoding => chosen = encoding);

        Assert.NotNull(chosen);
        Assert.Equal(65001, chosen.CodePage);
        Assert.Empty(chosen.GetPreamble());
        Assert.Equal("äöü", chosen.GetString(chosen.GetBytes("äöü")));
    }

    [Fact]
    public void InteractiveOutputKeepsTheConsoleEncoding() {
        var changed = false;

        PyRevitCLIConsoleEncoding.ApplyForRedirectedOutput(false, _ => changed = true);

        Assert.False(changed);
    }
}
