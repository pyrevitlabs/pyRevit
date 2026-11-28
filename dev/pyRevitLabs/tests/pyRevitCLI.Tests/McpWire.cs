using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using pyRevitCLI;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

/// <summary>
/// Request builders and drivers shared by the MCP protocol and skills extension tests.
/// </summary>
internal static class McpWire {
    public const string ModernVersion = "2026-07-28";
    public const string VersionKey = "io.modelcontextprotocol/protocolVersion";
    public const string CapabilitiesKey = "io.modelcontextprotocol/clientCapabilities";
    public const string ServerInfoKey = "io.modelcontextprotocol/serverInfo";
    public static readonly TimeSpan Patience = TimeSpan.FromSeconds(10);

    public static JObject Meta(string version = ModernVersion) => new JObject {
        [VersionKey] = version,
        [CapabilitiesKey] = new JObject(),
    };

    public static JObject Modern(int id, string method, JObject parameters = null, JObject meta = null) {
        parameters ??= new JObject();
        parameters["_meta"] = meta ?? Meta();
        return new JObject { ["jsonrpc"] = "2.0", ["id"] = id, ["method"] = method, ["params"] = parameters };
    }

    public static JObject Legacy(int id, string method, JObject parameters = null) {
        var request = new JObject { ["jsonrpc"] = "2.0", ["id"] = id, ["method"] = method };
        if (parameters != null)
            request["params"] = parameters;
        return request;
    }

    public static List<JObject> Serve(params JObject[] lines) {
        var output = new StringWriter();
        PyRevitMcpServer.Serve(null, new StringReader(string.Join("\n", lines.Select(line => line.ToString(Formatting.None)))), output);
        return output.ToString().Split('\n', StringSplitOptions.RemoveEmptyEntries).Select(line => JObject.Parse(line)).ToList();
    }

    public static JObject Single(JObject line) => Assert.Single(Serve(line));

    public static string Sha256(byte[] bytes) => "sha256:" + Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    public static void AssertInvalidParams(JObject response) => Assert.Equal(-32602, response["error"].Value<int>("code"));

    public static void AssertComplete(JToken result, bool cached = true) {
        Assert.Equal("complete", result.Value<string>("resultType"));
        if (!cached)
            return;
        Assert.True(result.Value<long>("ttlMs") > 0);
        Assert.Equal("public", result.Value<string>("cacheScope"));
    }
}

/// <summary>
/// A temporary shipped-skills folder, deleted on dispose.
/// </summary>
internal sealed class TempSkills : IDisposable {
    private readonly DirectoryInfo directory = Directory.CreateTempSubdirectory("pyrevit-skills-ext-");

    public string Root => directory.FullName;

    public void Plant(string folder, string skill, params (string Relative, byte[] Bytes)[] extra) {
        Plant(folder, Encoding.UTF8.GetBytes(skill), extra);
    }

    public void Plant(string folder, byte[] skill, params (string Relative, byte[] Bytes)[] extra) {
        var path = Directory.CreateDirectory(Path.Combine(Root, folder)).FullName;
        File.WriteAllBytes(Path.Combine(path, "SKILL.md"), skill);
        foreach (var (relative, bytes) in extra) {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(path, relative)));
            File.WriteAllBytes(Path.Combine(path, relative), bytes);
        }
    }

    public static string Skill(string name, string extraFrontMatter = "") =>
        $"---\nname: {name}\ndescription: Use when testing {name}.\n{extraFrontMatter}---\nBody\n";

    public void Dispose() {
        directory.Delete(recursive: true);
    }
}

internal sealed class QueueReader : TextReader {
    private readonly BlockingCollection<string> lines;
    private string current = string.Empty;
    private int position;

    public QueueReader(BlockingCollection<string> lines) {
        this.lines = lines;
    }

    public override int Read() {
        if (position == current.Length) {
            if (!lines.TryTake(out var line, Timeout.Infinite))
                return -1;
            current = line + '\n';
            position = 0;
        }
        return current[position++];
    }
}

internal sealed class QueueWriter : TextWriter {
    private readonly BlockingCollection<string> lines;

    public QueueWriter(BlockingCollection<string> lines) {
        this.lines = lines;
    }

    public override Encoding Encoding => Encoding.UTF8;

    public override void WriteLine(string value) => lines.Add(value);
}

/// <summary>
/// Redirects the process's standard output and error for the duration of a test.
/// </summary>
internal sealed class ConsoleCapture : IDisposable {
    private readonly TextWriter previousOut = Console.Out;
    private readonly TextWriter previousError = Console.Error;
    private readonly StringWriter standardOut = new StringWriter();
    private readonly StringWriter standardError = new StringWriter();

    public ConsoleCapture() {
        Console.SetOut(standardOut);
        Console.SetError(standardError);
    }

    public string Out => standardOut.ToString();

    public string Error => standardError.ToString();

    public void Dispose() {
        Console.SetOut(previousOut);
        Console.SetError(previousError);
    }
}
