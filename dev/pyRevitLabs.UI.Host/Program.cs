using System.Diagnostics;
using System.IO.Pipes;
using System.Text;
using System.Text.Json;
using PyRevitLabs.UI.Protocol;

const string defaultPipeName = "pyrevit-ui-poc";
var pipeName = GetArgument(args, "--pipe") ?? defaultPipeName;
var logPath = GetArgument(args, "--log") ?? Path.Combine(Path.GetTempPath(), "pyrevit-ui-host.log");

using var log = new HostLog(logPath);
log.Write($"starting host pid={Environment.ProcessId} pipe={pipeName} protocol={UiProtocol.Version}");

try
{
    while (true)
    {
        log.Write("waiting for client");
        await using var pipe = new NamedPipeServerStream(
            pipeName,
            PipeDirection.InOut,
            1,
            PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous);

        await pipe.WaitForConnectionAsync();
        log.Write("client connected");

        try
        {
            await HandleClientAsync(pipe, log);
        }
        catch (EndOfStreamException)
        {
            log.Write("client disconnected");
        }
        catch (IOException ex)
        {
            log.Write($"client io error: {ex.Message}");
        }
    }
}
catch (OperationCanceledException)
{
    log.Write("host cancelled");
}
catch (Exception ex)
{
    log.Write($"fatal: {ex}");
    return 1;
}

return 0;

static async Task HandleClientAsync(Stream stream, HostLog log)
{
    while (true)
    {
        var message = await ReadMessageAsync(stream);
        log.Write($"received type={message.Type} id={message.Id ?? "-"} method={message.Method ?? "-"}");

        UiMessage response = message.Type switch
        {
            "hello" => HandleHello(message, log),
            "request" when message.Method == "host.info" => CreateHostInfoResponse(message),
            _ => CreateErrorResponse(message, "unsupported_message", "Message type or method is not supported.")
        };

        await WriteMessageAsync(stream, response);
        log.Write($"sent type={response.Type} id={response.Id ?? "-"}");
    }
}

static UiMessage HandleHello(UiMessage message, HostLog log)
{
    if (message.Payload is null)
        return CreateErrorResponse(message, "invalid_hello", "Hello payload is required.");

    var hello = message.Payload.Value.Deserialize<HelloPayload>();
    if (hello is null)
        return CreateErrorResponse(message, "invalid_hello", "Hello payload is invalid.");

    log.Write($"hello client={hello.ClientName} pid={hello.ProcessId} protocol={hello.ProtocolVersion}");

    if (hello.ProtocolVersion != UiProtocol.Version)
        return CreateErrorResponse(message, "protocol_mismatch", $"Host protocol is {UiProtocol.Version}.");

    return new UiMessage("hello.ok", message.Id, Payload: JsonSerializer.SerializeToElement(CreateHostInfo()));
}

static UiMessage CreateHostInfoResponse(UiMessage request) =>
    new("response", request.Id, request.Method, JsonSerializer.SerializeToElement(CreateHostInfo()));

static HostInfo CreateHostInfo() => new(
    UiProtocol.Version,
    Environment.ProcessId,
    typeof(HostInfo).Assembly.GetName().Version?.ToString() ?? "unknown");

static UiMessage CreateErrorResponse(UiMessage request, string code, string message) =>
    new("error", request.Id, request.Method, JsonSerializer.SerializeToElement(new { code, message }));

static async Task<UiMessage> ReadMessageAsync(Stream stream)
{
    var lengthBuffer = new byte[4];
    await ReadExactlyAsync(stream, lengthBuffer);
    var length = BitConverter.ToInt32(lengthBuffer, 0);
    if (length <= 0 || length > 1024 * 1024)
        throw new InvalidDataException($"Invalid message length: {length}");

    var payload = new byte[length];
    await ReadExactlyAsync(stream, payload);
    return JsonSerializer.Deserialize<UiMessage>(payload)
        ?? throw new InvalidDataException("Message JSON is empty.");
}

static async Task WriteMessageAsync(Stream stream, UiMessage message)
{
    var payload = JsonSerializer.SerializeToUtf8Bytes(message);
    var length = BitConverter.GetBytes(payload.Length);
    await stream.WriteAsync(length);
    await stream.WriteAsync(payload);
    await stream.FlushAsync();
}

static async Task ReadExactlyAsync(Stream stream, byte[] buffer)
{
    var offset = 0;
    while (offset < buffer.Length)
    {
        var read = await stream.ReadAsync(buffer.AsMemory(offset));
        if (read == 0)
            throw new EndOfStreamException();
        offset += read;
    }
}

static string? GetArgument(string[] values, string name)
{
    for (var i = 0; i < values.Length - 1; i++)
        if (string.Equals(values[i], name, StringComparison.OrdinalIgnoreCase))
            return values[i + 1];
    return null;
}

sealed class HostLog : IDisposable
{
    private readonly StreamWriter _writer;

    public HostLog(string path)
    {
        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory))
            Directory.CreateDirectory(directory);
        _writer = new StreamWriter(path, append: true, Encoding.UTF8) { AutoFlush = true };
    }

    public void Write(string message)
    {
        var line = $"{DateTimeOffset.Now:O} [UI-HOST] {message}";
        Console.WriteLine(line);
        _writer.WriteLine(line);
    }

    public void Dispose() => _writer.Dispose();
}
