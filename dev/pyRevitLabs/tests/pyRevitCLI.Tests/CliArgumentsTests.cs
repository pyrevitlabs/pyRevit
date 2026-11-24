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

    [Theory]
    [InlineData(null, "configs", "--help")]
    [InlineData(null, "configs", "-h")]
    [InlineData("bincache", "configs", "bincache", "--help")]
    [InlineData("some:option", "configs", "some:option", "--help")]
    [InlineData("routes", "configs", "routes", "--help")]
    [InlineData("routes", "configs", "routes", "port", "--help")]
    [InlineData("agent", "configs", "agent", "--help")]
    [InlineData("agent", "configs", "agent", "policy", "--help")]
    [InlineData("telemetry", "configs", "telemetry", "-h")]
    [InlineData("telemetry", "configs", "telemetry", "utc", "--help")]
    [InlineData("apptelemetry", "configs", "apptelemetry", "--help")]
    [InlineData("apptelemetry", "configs", "apptelemetry", "flags", "--help")]
    public void HelpAfterAnyConfigsWordIsParsedWithTheFirstWordOfTheGroup(string expectedFirstWord, params string[] argv) {
        var arguments = Parse(argv);

        Assert.True(arguments["--help"].IsTrue || arguments["-h"].IsTrue);
        Assert.Equal(expectedFirstWord, PyRevitCLIArguments.Values(arguments, "<config_words>").FirstOrDefault());
    }

    [Theory]
    [InlineData("configs", "apptelemetry", "flags", "ALL")]
    [InlineData("configs", "agent", "policy", "ask")]
    [InlineData("configs", "bincache", "enable")]
    public void ConfigsCommandsWithoutHelpAreNotTakenForHelp(params string[] argv) {
        var arguments = Parse(argv);

        Assert.False(arguments["--help"].IsTrue);
        Assert.False(arguments["-h"].IsTrue);
    }
}
