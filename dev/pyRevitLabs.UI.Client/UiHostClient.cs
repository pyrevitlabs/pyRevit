using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Text;
using System.Threading.Tasks;

namespace PyRevitLabs.UI.Client;

/// <summary>
/// Starts and owns one out-of-process UI host session using only framework-provided APIs.
/// </summary>
public static class UiHostLauncher
{
    /// <summary>
    /// Starts the host process, connects to its named pipe, validates the protocol handshake, and returns an owned session.
    /// </summary>
    public static async Task<UiHostSession> StartAsync(
        string hostPath,
        string pipeName,
        string logPath,
        string clientName,
        int timeoutMilliseconds = 5000)
    {
        if (string.IsNullOrWhiteSpace(hostPath))
            throw new ArgumentException("Host path is required.", nameof(hostPath));
        if (!File.Exists(hostPath))
            throw new FileNotFoundException("UI host executable was not found.", hostPath);
        if (string.IsNullOrWhiteSpace(pipeName))
            throw new ArgumentException("Pipe name is required.", nameof(pipeName));
        if (string.IsNullOrWhiteSpace(clientName))
            throw new ArgumentException("Client name is required.", nameof(clientName));

        var process = StartHostProcess(hostPath, pipeName, logPath);
        NamedPipeClientStream? pipe = null;

        try
        {
            pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
            await pipe.ConnectAsync(timeoutMilliseconds).ConfigureAwait(false);

            var helloId = Guid.NewGuid().ToString("N");
            var hello = new HelloMessage
            {
                Id = helloId,
                Payload = new HelloPayload
                {
                    ProtocolVersion = UiHostSession.ProtocolVersion,
                    ClientName = clientName,
                    ProcessId = Process.GetCurrentProcess().Id,
                },
            };

            await WireCodec.WriteAsync(pipe, hello).ConfigureAwait(false);
            var helloResponse = await WireCodec.ReadAsync<HelloResponseMessage>(pipe).ConfigureAwait(false);
            if (!string.Equals(helloResponse.Type, "hello.ok", StringComparison.Ordinal))
                throw new InvalidDataException($"UI host handshake failed with message type '{helloResponse.Type}'.");
            if (helloResponse.Payload == null)
                throw new InvalidDataException("UI host handshake response did not include host information.");
            if (helloResponse.Payload.ProtocolVersion != UiHostSession.ProtocolVersion)
                throw new InvalidDataException(
                    $"UI host protocol mismatch. Client={UiHostSession.ProtocolVersion}, Host={helloResponse.Payload.ProtocolVersion}.");

            Trace.WriteLine($"[UI-CLIENT] connected hostPid={helloResponse.Payload.HostProcessId} pipe={pipeName}");
            return new UiHostSession(process, pipe, helloResponse.Payload);
        }
        catch
        {
            if (pipe != null)
                pipe.Dispose();
            StopProcess(process);
            throw;
        }
    }

    private static Process StartHostProcess(string hostPath, string pipeName, string logPath)
    {
        var isDll = string.Equals(Path.GetExtension(hostPath), ".dll", StringComparison.OrdinalIgnoreCase);
        var arguments = new StringBuilder();
        if (isDll)
        {
            arguments.Append(Quote(hostPath));
            arguments.Append(' ');
        }

        arguments.Append("--pipe ");
        arguments.Append(Quote(pipeName));
        arguments.Append(" --log ");
        arguments.Append(Quote(logPath));

        var startInfo = new ProcessStartInfo
        {
            FileName = isDll ? "dotnet" : hostPath,
            Arguments = arguments.ToString(),
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        var process = Process.Start(startInfo);
        if (process == null)
            throw new InvalidOperationException("Failed to start UI host process.");

        Trace.WriteLine($"[UI-CLIENT] started host pid={process.Id} path={hostPath}");
        return process;
    }

    private static string Quote(string value) => "\"" + value.Replace("\"", "\\\"") + "\"";

    private static void StopProcess(Process process)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill();
                process.WaitForExit(3000);
            }
        }
        finally
        {
            process.Dispose();
        }
    }

    internal static void StopOwnedProcess(Process process) => StopProcess(process);
}

/// <summary>
/// Represents an active connection to one UI host process and owns that process lifetime.
/// </summary>
public sealed class UiHostSession : IDisposable
{
    private readonly Process _process;
    private readonly NamedPipeClientStream _pipe;
    private bool _disposed;

    internal UiHostSession(Process process, NamedPipeClientStream pipe, HostInfoPayload hostInfo)
    {
        _process = process;
        _pipe = pipe;
        HostInfo = new UiHostInfo(hostInfo.ProtocolVersion, hostInfo.HostProcessId, hostInfo.HostVersion ?? "unknown");
    }

    /// <summary>
    /// Current wire protocol version supported by this client.
    /// </summary>
    public const int ProtocolVersion = 1;

    /// <summary>
    /// Information returned by the host during handshake.
    /// </summary>
    public UiHostInfo HostInfo { get; }

    /// <summary>
    /// Requests the current host information over the live pipe connection.
    /// </summary>
    public async Task<UiHostInfo> GetHostInfoAsync()
    {
        ThrowIfDisposed();

        var request = new HostInfoRequestMessage { Id = Guid.NewGuid().ToString("N") };
        await WireCodec.WriteAsync(_pipe, request).ConfigureAwait(false);
        var response = await WireCodec.ReadAsync<HostInfoResponseMessage>(_pipe).ConfigureAwait(false);

        if (!string.Equals(response.Type, "response", StringComparison.Ordinal))
            throw new InvalidDataException($"Expected host.info response, got '{response.Type}'.");
        if (!string.Equals(response.Method, "host.info", StringComparison.Ordinal))
            throw new InvalidDataException($"Expected host.info method, got '{response.Method}'.");
        if (response.Payload == null)
            throw new InvalidDataException("host.info response did not include a payload.");

        return new UiHostInfo(
            response.Payload.ProtocolVersion,
            response.Payload.HostProcessId,
            response.Payload.HostVersion ?? "unknown");
    }

    /// <summary>
    /// Closes the pipe and terminates the owned host process.
    /// </summary>
    public void Dispose()
    {
        if (_disposed)
            return;

        _disposed = true;
        _pipe.Dispose();
        UiHostLauncher.StopOwnedProcess(_process);
        Trace.WriteLine("[UI-CLIENT] host session disposed");
    }

    private void ThrowIfDisposed()
    {
        if (_disposed)
            throw new ObjectDisposedException(nameof(UiHostSession));
    }
}

/// <summary>
/// Immutable information describing the connected UI host instance.
/// </summary>
public sealed class UiHostInfo
{
    internal UiHostInfo(int protocolVersion, int hostProcessId, string hostVersion)
    {
        ProtocolVersion = protocolVersion;
        HostProcessId = hostProcessId;
        HostVersion = hostVersion;
    }

    /// <summary>Gets the negotiated protocol version.</summary>
    public int ProtocolVersion { get; }

    /// <summary>Gets the operating-system process identifier of the host.</summary>
    public int HostProcessId { get; }

    /// <summary>Gets the host assembly version reported by the host.</summary>
    public string HostVersion { get; }
}

internal static class WireCodec
{
    internal static async Task WriteAsync<T>(Stream stream, T message)
    {
        var serializer = new DataContractJsonSerializer(typeof(T));
        byte[] payload;
        using (var memory = new MemoryStream())
        {
            serializer.WriteObject(memory, message);
            payload = memory.ToArray();
        }

        var length = BitConverter.GetBytes(payload.Length);
        await stream.WriteAsync(length, 0, length.Length).ConfigureAwait(false);
        await stream.WriteAsync(payload, 0, payload.Length).ConfigureAwait(false);
        await stream.FlushAsync().ConfigureAwait(false);
    }

    internal static async Task<T> ReadAsync<T>(Stream stream)
    {
        var lengthBytes = new byte[4];
        await ReadExactlyAsync(stream, lengthBytes).ConfigureAwait(false);
        var length = BitConverter.ToInt32(lengthBytes, 0);
        if (length <= 0 || length > 1024 * 1024)
            throw new InvalidDataException($"Invalid UI host message length: {length}.");

        var payload = new byte[length];
        await ReadExactlyAsync(stream, payload).ConfigureAwait(false);

        var serializer = new DataContractJsonSerializer(typeof(T));
        using (var memory = new MemoryStream(payload))
        {
            var value = serializer.ReadObject(memory);
            if (value is T typed)
                return typed;
        }

        throw new InvalidDataException($"Unable to deserialize UI host message as {typeof(T).Name}.");
    }

    private static async Task ReadExactlyAsync(Stream stream, byte[] buffer)
    {
        var offset = 0;
        while (offset < buffer.Length)
        {
            var read = await stream.ReadAsync(buffer, offset, buffer.Length - offset).ConfigureAwait(false);
            if (read == 0)
                throw new EndOfStreamException();
            offset += read;
        }
    }
}

[DataContract]
internal sealed class HelloMessage
{
    [DataMember(Name = "type")]
    public string Type { get; set; } = "hello";

    [DataMember(Name = "id")]
    public string Id { get; set; } = string.Empty;

    [DataMember(Name = "payload")]
    public HelloPayload Payload { get; set; } = new HelloPayload();
}

[DataContract]
internal sealed class HelloPayload
{
    [DataMember(Name = "protocolVersion")]
    public int ProtocolVersion { get; set; }

    [DataMember(Name = "clientName")]
    public string ClientName { get; set; } = string.Empty;

    [DataMember(Name = "processId")]
    public int ProcessId { get; set; }
}

[DataContract]
internal sealed class HelloResponseMessage
{
    [DataMember(Name = "type")]
    public string? Type { get; set; }

    [DataMember(Name = "id")]
    public string? Id { get; set; }

    [DataMember(Name = "payload")]
    public HostInfoPayload? Payload { get; set; }
}

[DataContract]
internal sealed class HostInfoRequestMessage
{
    [DataMember(Name = "type")]
    public string Type { get; set; } = "request";

    [DataMember(Name = "id")]
    public string Id { get; set; } = string.Empty;

    [DataMember(Name = "method")]
    public string Method { get; set; } = "host.info";
}

[DataContract]
internal sealed class HostInfoResponseMessage
{
    [DataMember(Name = "type")]
    public string? Type { get; set; }

    [DataMember(Name = "id")]
    public string? Id { get; set; }

    [DataMember(Name = "method")]
    public string? Method { get; set; }

    [DataMember(Name = "payload")]
    public HostInfoPayload? Payload { get; set; }
}

[DataContract]
internal sealed class HostInfoPayload
{
    [DataMember(Name = "protocolVersion")]
    public int ProtocolVersion { get; set; }

    [DataMember(Name = "hostProcessId")]
    public int HostProcessId { get; set; }

    [DataMember(Name = "hostVersion")]
    public string? HostVersion { get; set; }
}
