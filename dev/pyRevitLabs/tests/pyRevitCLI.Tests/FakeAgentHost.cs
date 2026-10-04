using System.IO.Pipes;
using System.Text;
using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

/// <summary>
/// A stand-in for the in-Revit agent host: a registration file in a temporary agent folder and a
/// named pipe in this process that answers JSON-RPC lines, one connection at a time like the
/// real host. Never touches the user's profile.
/// </summary>
internal sealed class FakeAgentHost : IDisposable {
    private static readonly Encoding Utf8 = new UTF8Encoding(false);
    private readonly CancellationTokenSource stop = new CancellationTokenSource();
    private readonly object sync = new object();
    private readonly List<JObject> requests = new List<JObject>();
    private readonly string previousAgentDir = PyRevitAgentClient.AgentDirOverride;
    private readonly int previousConnectTimeout = PyRevitAgentClient.ConnectTimeoutMs;
    private readonly Task serving;

    public FakeAgentHost(string revitVersion = "2090", bool register = true) {
        AgentDir = Directory.CreateTempSubdirectory("pyrevit-agent-fake-").FullName;
        PyRevitAgentClient.AgentDirOverride = AgentDir;
        PipeName = "pyrevit-fake-" + Guid.NewGuid().ToString("N");
        if (register)
            Register(revitVersion, Environment.ProcessId, DateTime.UtcNow);
        serving = Task.Run(Serve);
    }

    public string AgentDir { get; }

    public string PipeName { get; }

    public Func<JObject, JObject> Handler { get; set; } = request => Result(request, new JObject());

    public string RawResponse { get; set; }

    public IReadOnlyList<JObject> Requests {
        get {
            lock (sync)
                return requests.ToList();
        }
    }

    public IReadOnlyList<JObject> RequestsFor(string method) {
        return Requests.Where(request => request.Value<string>("method") == method).ToList();
    }

    public static JObject Result(JObject request, JToken result) {
        return new JObject { ["jsonrpc"] = "2.0", ["id"] = request["id"], ["result"] = result };
    }

    public static JObject Failure(JObject request, string type, string message) {
        return new JObject {
            ["jsonrpc"] = "2.0",
            ["id"] = request["id"],
            ["error"] = new JObject { ["code"] = -32000, ["message"] = message, ["data"] = new JObject { ["type"] = type } },
        };
    }

    public void Register(string revitVersion, int processId, DateTime started, string fileName = null) {
        var instances = Directory.CreateDirectory(Path.Combine(AgentDir, "instances")).FullName;
        File.WriteAllText(
            Path.Combine(instances, fileName ?? (revitVersion + "-" + processId + ".json")),
            new JObject {
                ["pid"] = processId,
                ["pipe"] = PipeName,
                ["revit_version"] = revitVersion,
                ["revit_build"] = "build-" + revitVersion,
                ["started"] = started.ToString("O"),
            }.ToString());
    }

    public string AddRun(string runId, string response = null, string script = null, string result = null, string stamp = "20260101-000000") {
        var directory = Directory.CreateDirectory(Path.Combine(AgentDir, "runs", stamp + "-" + runId)).FullName;
        if (response != null)
            File.WriteAllText(Path.Combine(directory, "response.json"), response);
        if (script != null)
            File.WriteAllText(Path.Combine(directory, "script.py"), script);
        if (result != null)
            File.WriteAllText(Path.Combine(directory, "result.json"), result);
        return directory;
    }

    private async Task Serve() {
        while (!stop.IsCancellationRequested) {
            try {
                using var server = new NamedPipeServerStream(PipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
                await server.WaitForConnectionAsync(stop.Token);
                var reader = new StreamReader(server, Utf8);
                var writer = new StreamWriter(server, Utf8) { AutoFlush = true, NewLine = "\n" };
                var line = await reader.ReadLineAsync();
                if (line == null)
                    continue;
                var request = JObject.Parse(line);
                lock (sync)
                    requests.Add(request);
                if (RawResponse != null) {
                    await writer.WriteLineAsync(RawResponse);
                    continue;
                }
                var response = Handler(request);
                if (response != null)
                    await writer.WriteLineAsync(response.ToString(pyRevitLabs.Json.Formatting.None));
            }
            catch (OperationCanceledException) {
                return;
            }
            catch (IOException) {
            }
        }
    }

    public void Dispose() {
        stop.Cancel();
        try {
            serving.Wait(TimeSpan.FromSeconds(5));
        }
        catch (AggregateException) {
        }
        stop.Dispose();
        PyRevitAgentClient.AgentDirOverride = previousAgentDir;
        PyRevitAgentClient.ConnectTimeoutMs = previousConnectTimeout;
        Directory.Delete(AgentDir, recursive: true);
    }
}
