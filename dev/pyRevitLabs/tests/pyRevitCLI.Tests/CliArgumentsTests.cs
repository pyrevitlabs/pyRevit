using DocoptNet;
using pyRevitCLI;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that options left off the command line fall back to their defaults: <c>pyrevit env path</c>
///     without <c>--scope</c> failed with "Unknown PATH scope" instead of using <c>user</c>.
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class CliArgumentsTests {
    private static IDictionary<string, ValueObject> Parse(params string[] argv) {
        var usage = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UsagePatterns.txt"));
        return new Docopt().Apply(usage, argv, help: false, exit: false);
    }

    [Theory]
    [InlineData("env", "path", "list")]
    [InlineData("env", "path", "ensure", @"C:\tools\bin")]
    [InlineData("env", "path", "ensure", @"C:\tools\bin", "--first")]
    [InlineData("env", "path", "remove", @"C:\tools\bin")]
    public void EnvPathWithoutScopeUsesTheUserScope(params string[] argv) {
        Assert.Equal("user", PyRevitCLIArguments.Value(Parse(argv), "--scope", "user"));
    }

    [Theory]
    [InlineData("user")]
    [InlineData("machine")]
    public void EnvPathKeepsAnExplicitScope(string scope) {
        var arguments = Parse("env", "path", "list", "--scope=" + scope);

        Assert.Equal(scope, PyRevitCLIArguments.Value(arguments, "--scope", "user"));
    }

    [Fact]
    public void OptionNotGivenWithoutADefaultIsNull() {
        Assert.Null(PyRevitCLIArguments.Value(Parse("env", "path", "list"), "--scope"));
    }

    [Fact]
    public void KeyMissingFromTheArgumentsUsesTheDefault() {
        Assert.Equal("fallback", PyRevitCLIArguments.Value(new Dictionary<string, ValueObject>(), "--nope", "fallback"));
        Assert.Equal("fallback", PyRevitCLIArguments.Value(null, "--nope", "fallback"));
    }
}
