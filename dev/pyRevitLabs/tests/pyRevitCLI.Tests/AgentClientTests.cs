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

    /// <summary>Dead process registrations are excluded and removed without rejecting corrupt files.</summary>
    [Fact]
    public void RegistrationsOfDeadProcessesAndCorruptFilesAreSkipped() {
        host.Register("2085", 2147483000, DateTime.UtcNow, fileName: "dead.json");
        File.WriteAllText(Path.Combine(host.AgentDir, "instances", "garbage.json"), "{ not json");

        var versions = PyRevitAgentClient.GetInstances().Select(instance => instance.RevitVersion).ToList();

        Assert.Equal(new[] { "2090" }, versions);
        Assert.False(File.Exists(Path.Combine(host.AgentDir, "instances", "dead.json")));
    }

    /// <summary>A reused PID belonging to a non-Revit process is excluded even with a recent timestamp.</summary>
    [Fact]
    public void RegistrationsOfNonRevitProcessesAreSkippedAndRemoved() {
        PyRevitAgentClient.ProcessNameReader = process => process.ProcessName;
        host.Register("2086", Environment.ProcessId, DateTime.UtcNow, fileName: "non-revit.json", pipeName: "pyrevit-missing-" + Guid.NewGuid().ToString("N"));

        Assert.Empty(PyRevitAgentClient.GetInstances());
        Assert.False(File.Exists(Path.Combine(host.AgentDir, "instances", "non-revit.json")));
    }

    /// <summary>A Revit process started after an old registration cannot inherit its session.</summary>
    [Fact]
    public void RegistrationsPredatingTheRevitProcessAreSkippedAndRemoved() {
        using var process = Process.GetCurrentProcess();
        host.Register("2087", Environment.ProcessId, process.StartTime.ToUniversalTime().AddSeconds(-10),
            fileName: "reused.json", pipeName: "pyrevit-missing-" + Guid.NewGuid().ToString("N"));

        Assert.Equal("2090", Assert.Single(PyRevitAgentClient.GetInstances()).RevitVersion);
        Assert.False(File.Exists(Path.Combine(host.AgentDir, "instances", "reused.json")));
    }

    /// <summary>Timestamp precision differences within two seconds preserve a matching Revit registration.</summary>
    [Fact]
    public void RegistrationStartTimeAllowsASmallTolerance() {
        using var process = Process.GetCurrentProcess();
        PyRevitAgentClient.ProcessNameReader = registeredProcess => "rEvIt";
        host.Register("2088", Environment.ProcessId, process.StartTime.ToUniversalTime().AddSeconds(-1),
            fileName: "tolerated.json", pipeName: "pyrevit-missing-" + Guid.NewGuid().ToString("N"));

        Assert.Equal("2088", PyRevitAgentClient.Resolve("2088").RevitVersion);
        Assert.True(File.Exists(Path.Combine(host.AgentDir, "instances", "tolerated.json")));
    }

    /// <summary>An existing host pipe preserves a Revit registration whose timestamp cannot establish liveness.</summary>
    [Fact]
    public void AnExistingPipeKeepsARevitRegistrationWithAnOldTimestamp() {
        Assert.True(SpinWait.SpinUntil(() => File.Exists(@"\\.\pipe\" + host.PipeName), TimeSpan.FromSeconds(5)));
        host.Register("2089", Environment.ProcessId, DateTime.UnixEpoch, fileName: "existing-pipe.json");

        Assert.Equal("2089", PyRevitAgentClient.Resolve("2089").RevitVersion);
        Assert.Empty(host.Requests);
    }

    /// <summary>Unavailable process metadata falls back to an existing pipe without connecting.</summary>
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void AccessDeniedReadingProcessMetadataKeepsARegistrationWithAnExistingPipe(bool denyStartTime) {
        Assert.True(SpinWait.SpinUntil(() => File.Exists(@"\\.\pipe\" + host.PipeName), TimeSpan.FromSeconds(5)));
        if (denyStartTime)
            PyRevitAgentClient.ProcessStartTimeReader = process => throw new System.ComponentModel.Win32Exception(5);
        else
            PyRevitAgentClient.ProcessNameReader = process => throw new System.ComponentModel.Win32Exception(5);

        Assert.Equal("2090", PyRevitAgentClient.Resolve(null).RevitVersion);
        Assert.Empty(host.Requests);
    }

    /// <summary>Unavailable process metadata does not preserve a registration whose pipe is absent.</summary>
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void AccessDeniedReadingProcessMetadataRemovesARegistrationWithoutAPipe(bool denyStartTime) {
        if (denyStartTime)
            PyRevitAgentClient.ProcessStartTimeReader = process => throw new System.ComponentModel.Win32Exception(5);
        else
            PyRevitAgentClient.ProcessNameReader = process => throw new System.ComponentModel.Win32Exception(5);
        host.Register("2089", Environment.ProcessId, DateTime.UtcNow, fileName: "denied.json",
            pipeName: "pyrevit-missing-" + Guid.NewGuid().ToString("N"));

        Assert.DoesNotContain(PyRevitAgentClient.GetInstances(), instance => instance.RevitVersion == "2089");
        Assert.False(File.Exists(Path.Combine(host.AgentDir, "instances", "denied.json")));
    }

    /// <summary>A registration with an unreadable timestamp and no pipe cannot describe a live host.</summary>
    [Fact]
    public void RegistrationsWithoutAValidTimestampOrPipeAreSkippedAndRemoved() {
        var path = Path.Combine(host.AgentDir, "instances", "invalid-started.json");
        File.WriteAllText(path, new JObject {
            ["pid"] = Environment.ProcessId,
            ["pipe"] = "pyrevit-missing-" + Guid.NewGuid().ToString("N"),
            ["revit_version"] = "2089",
            ["started"] = "invalid",
        }.ToString());

        Assert.Equal("2090", Assert.Single(PyRevitAgentClient.GetInstances()).RevitVersion);
        Assert.False(File.Exists(path));
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

    /// <summary>A live fake host registration resolves without requiring a real Revit process.</summary>
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

    private static readonly AgentInstance[] Sessions = {
        new AgentInstance { ProcessId = 2024, RevitVersion = "2026" },
        new AgentInstance { ProcessId = 9000, RevitVersion = "2024" },
        new AgentInstance { ProcessId = 9004, RevitVersion = "2025" },
    };

    [Fact]
    public void AProcessIdInTheYearRangeWinsOverTheYear() {
        var match = Assert.Single(PyRevitAgentClient.Match(Sessions, "2024"));

        Assert.Equal(2024, match.ProcessId);
    }

    [Fact]
    public void AYearSelectsWhenNoProcessIdMatches() {
        Assert.Equal(9004, Assert.Single(PyRevitAgentClient.Match(Sessions, "2025")).ProcessId);
        Assert.Equal(2024, Assert.Single(PyRevitAgentClient.Match(Sessions, "2026")).ProcessId);
    }

    [Fact]
    public void APaddedYearSelectsLikeTheCanonicalYear() {
        Assert.Equal(9004, Assert.Single(PyRevitAgentClient.Match(Sessions, " 2025 ")).ProcessId);
        Assert.Equal(9004, Assert.Single(PyRevitAgentClient.Match(Sessions, "02025")).ProcessId);
    }

    [Fact]
    public void AProcessIdOutsideTheYearRangeSelectsOnlyByProcessId() {
        Assert.Equal("2024", Assert.Single(PyRevitAgentClient.Match(Sessions, "9000")).RevitVersion);
        Assert.Empty(PyRevitAgentClient.Match(Sessions, "9008"));
    }

    [Fact]
    public void AYearThatMatchesNoSessionMatchesNothing() {
        Assert.Empty(PyRevitAgentClient.Match(Sessions, "2077"));
    }

    [Fact]
    public void ABlankSelectorKeepsEverySession() {
        Assert.Equal(3, PyRevitAgentClient.Match(Sessions, " ").Count);
    }

    /// <summary>Ambiguity reports only live registrations, excluding dead and reused process IDs.</summary>
    [Fact]
    public void SeveralHostsWithoutASelectorAreAmbiguousAndNamed() {
        host.Register("2091", Environment.ProcessId, DateTime.UtcNow);
        host.Register("2085", 2147483000, DateTime.UtcNow);
        using var process = Process.GetCurrentProcess();
        host.Register("2086", Environment.ProcessId, process.StartTime.ToUniversalTime().AddMinutes(-1),
            pipeName: "pyrevit-missing-" + Guid.NewGuid().ToString("N"));

        var error = Assert.Throws<AgentClientException>(() => PyRevitAgentClient.Resolve(null));

        Assert.Equal("ambiguous_revit", error.Code);
        Assert.Contains("2090", error.Message);
        Assert.Contains("2091", error.Message);
        Assert.DoesNotContain("2085", error.Message);
        Assert.DoesNotContain("2086", error.Message);
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
