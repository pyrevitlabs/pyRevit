using System.Diagnostics;
using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
public class AgentClientTests : IDisposable {
    private readonly FakeAgentHost host = new FakeAgentHost();

    public void Dispose() {
        host.Dispose();
    }

    private AgentInstance ThisHost() => PyRevitAgentClient.Resolve("2090");

    [Fact]
    public void RegisteredHostsAreListedNewestFirst() {
        host.Register("2091", Environment.ProcessId, new DateTime(2098, 1, 1, 0, 0, 0, DateTimeKind.Utc));
        host.Register("2092", Environment.ProcessId, new DateTime(2099, 1, 1, 0, 0, 0, DateTimeKind.Utc));

        var versions = PyRevitAgentClient.GetInstances().Select(instance => instance.RevitVersion).ToList();

        Assert.Equal(new[] { "2092", "2091", "2090" }, versions);
    }

    [Fact]
    public void RegistrationsOfDeadProcessesAndCorruptFilesAreSkipped() {
        host.Register("2085", 2147483000, DateTime.UtcNow);
        File.WriteAllText(Path.Combine(host.AgentDir, "instances", "garbage.json"), "{ not json");

        var versions = PyRevitAgentClient.GetInstances().Select(instance => instance.RevitVersion).ToList();

        Assert.Equal(new[] { "2090" }, versions);
    }

    [Fact]
    public void WithoutAnInstancesFolderThereAreNoHosts() {
        Directory.Delete(Path.Combine(host.AgentDir, "instances"), recursive: true);

        Assert.Empty(PyRevitAgentClient.GetInstances());
    }

    [Fact]
    public void ResolvingWithoutAnyHostIsNoRevit() {
        Directory.Delete(Path.Combine(host.AgentDir, "instances"), recursive: true);

        Assert.Equal("no_revit", Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Resolve(null)).Code);
    }

    [Fact]
    public void AnUnselectedSingleHostIsPicked() {
        Assert.Equal("2090", PyRevitAgentClient.Resolve(null).RevitVersion);
    }

    [Fact]
    public void AYearOrAProcessIdSelectsTheHost() {
        Assert.Equal("2090", PyRevitAgentClient.Resolve("2090").RevitVersion);
        Assert.Equal(Environment.ProcessId, PyRevitAgentClient.Resolve(Environment.ProcessId.ToString()).ProcessId);
    }

    [Fact]
    public void ASelectorThatMatchesNothingIsNoRevit() {
        Assert.Equal("no_revit", Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Resolve("2077")).Code);
        Assert.Equal("no_revit", Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Resolve("4242")).Code);
    }

    [Fact]
    public void ASelectorThatIsNotANumberIsInvalid() {
        Assert.Equal("invalid_params", Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Resolve("latest")).Code);
    }

    [Fact]
    public void SeveralHostsWithoutASelectorAreAmbiguousAndNamed() {
        host.Register("2091", Environment.ProcessId, DateTime.UtcNow);

        var error = Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Resolve(null));

        Assert.Equal("ambiguous_revit", error.Code);
        Assert.Contains("2090", error.Message);
        Assert.Contains("2091", error.Message);
    }

    [Fact]
    public void ACallReturnsTheResultOfTheHost() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["pong"] = true });

        var result = PyRevitAgentClient.Call(ThisHost(), "ping", new JObject { ["x"] = 1 });

        Assert.True(result.Value<bool>("pong"));
        var received = Assert.Single(host.Requests);
        Assert.Equal("ping", received.Value<string>("method"));
        Assert.Equal(1, received["params"].Value<int>("x"));
        Assert.Equal("2.0", received.Value<string>("jsonrpc"));
    }

    [Fact]
    public void AHostErrorBecomesAnExceptionWithItsTypeAndMessage() {
        host.Handler = request => FakeAgentHost.Failure(request, "revit_busy", "Revit did not become idle");

        var error = Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Call(ThisHost(), "run"));

        Assert.Equal("revit_busy", error.Code);
        Assert.Equal("Revit did not become idle", error.Message);
    }

    [Fact]
    public void AHostThatClosesWithoutAnsweringIsAPipeError() {
        host.Handler = request => null;

        var error = Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Call(ThisHost(), "ping"));

        Assert.Equal("pipe_error", error.Code);
    }

    [Fact]
    public void APipeServedByAnotherProcessIsRefusedBeforeAnythingIsSent() {
        var other = Process.GetProcesses().First(process => process.Id != Environment.ProcessId && process.Id > 4).Id;
        var instance = new AgentInstance { ProcessId = other, Pipe = host.PipeName, RevitVersion = "2090" };

        var error = Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Call(instance, "run", new JObject { ["script"] = "secret" }));

        Assert.Equal("pipe_error", error.Code);
        Assert.Contains("served by another process", error.Message);
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void NobodyListeningIsReportedAsBusy() {
        PyRevitAgentClient.ConnectTimeoutMs = 200;
        var instance = new AgentInstance { ProcessId = Environment.ProcessId, Pipe = "pyrevit-nobody-" + Guid.NewGuid().ToString("N"), RevitVersion = "2090" };

        var error = Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Call(instance, "ping"));

        Assert.Equal("revit_busy", error.Code);
    }

    [Fact]
    public void ARunFolderIsFoundByTheEndOfItsName() {
        var directory = host.AddRun("abc123def456");

        Assert.Equal(directory, PyRevitAgentClient.FindRunDir("abc123def456"));
        Assert.Equal(directory, PyRevitAgentClient.FindRunDir("  abc123def456  "));
    }

    [Fact]
    public void AnUnknownOrEmptyRunIdFindsNothing() {
        host.AddRun("abc123def456");

        Assert.Null(PyRevitAgentClient.FindRunDir("000000000000"));
        Assert.Null(PyRevitAgentClient.FindRunDir(""));
        Assert.Null(PyRevitAgentClient.FindRunDir(null));
    }

    [Theory]
    [InlineData("*")]
    [InlineData("a?c")]
    [InlineData("..\\..\\x")]
    [InlineData("abc/def")]
    [InlineData("abc-def")]
    public void ARunIdThatIsNotLettersAndDigitsFindsNothing(string runId) {
        host.AddRun("abc123def456");

        Assert.Null(PyRevitAgentClient.FindRunDir(runId));
    }

    [Fact]
    public void RecentRunsComeNewestFirstAndAreLimited() {
        host.AddRun("aaaaaaaaaaaa", stamp: "20260101-000001");
        host.AddRun("bbbbbbbbbbbb", stamp: "20260101-000003");
        host.AddRun("cccccccccccc", stamp: "20260101-000002");

        var recent = PyRevitAgentClient.GetRecentRunDirs(2).Select(Path.GetFileName).ToList();

        Assert.Equal(new[] { "20260101-000003-bbbbbbbbbbbb", "20260101-000002-cccccccccccc" }, recent);
    }

    [Fact]
    public void WithoutARunsFolderThereAreNoRuns() {
        Assert.Empty(PyRevitAgentClient.GetRecentRunDirs(5));
        Assert.Null(PyRevitAgentClient.FindRunDir("abc123def456"));
    }
}
