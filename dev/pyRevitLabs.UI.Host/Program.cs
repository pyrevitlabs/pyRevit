using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text.Json;
using PyRevitLabs.UI.Protocol;

const string defaultPipeName = "pyrevit-ui-poc";
var pipeName = GetArgument(args, "--pipe") ?? defaultPipeName;
var parentProcessId = GetIntArgument(args, "--parent-pid");
var eventPipeName = GetArgument(args, "--event-pipe") ?? pipeName + "-events";

var log = new HostLog();
using var hostCancellation = new CancellationTokenSource();
log.Write($"starting host pid={Environment.ProcessId} pipe={pipeName} protocol={UiProtocol.Version} parentPid={parentProcessId?.ToString() ?? "-"}");
var parentWatchTask = parentProcessId.HasValue
    ? WatchParentAsync(parentProcessId.Value, hostCancellation, log)
    : Task.CompletedTask;
await using var eventChannel = await HostEventChannel.ConnectAsync(eventPipeName);
using var outputWindows = new OutputWindowManager(log.Write, eventChannel);
var services = new UiServiceRegistry();
services.Register(new OutputServiceHandler(outputWindows));
log.Write($"event channel connected pipe={eventPipeName}");

try
{
    while (!hostCancellation.IsCancellationRequested)
    {
        log.Write("waiting for client");
        await using var pipe = new NamedPipeServerStream(
            pipeName,
            PipeDirection.InOut,
            1,
            PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous);

        await pipe.WaitForConnectionAsync(hostCancellation.Token);
        log.Write("client connected");

        try
        {
            await HandleClientAsync(pipe, log, services);
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
finally
{
    hostCancellation.Cancel();
    await parentWatchTask;
}

return 0;

static async Task WatchParentAsync(int parentProcessId, CancellationTokenSource hostCancellation, HostLog log)
{
    try
    {
        using var parentProcess = Process.GetProcessById(parentProcessId);
        log.Write($"watching parent pid={parentProcessId}");
        await parentProcess.WaitForExitAsync(hostCancellation.Token);
        log.Write($"parent exited pid={parentProcessId}");
        hostCancellation.Cancel();
    }
    catch (ArgumentException)
    {
        log.Write($"parent not running pid={parentProcessId}");
        hostCancellation.Cancel();
    }
    catch (OperationCanceledException)
    {
    }
    catch (Exception ex)
    {
        log.Write($"parent watch failed pid={parentProcessId}: {ex.Message}");
    }
}

static async Task HandleClientAsync(Stream stream, HostLog log, UiServiceRegistry services)
{
    while (true)
    {
        var message = await ReadMessageAsync(stream);
        IUiServiceHandler? serviceHandler = null;
        if (string.Equals(message.Type, "request", StringComparison.Ordinal))
            services.TryResolve(message.Method, out serviceHandler);
        var logWireMessage = serviceHandler?.LogWireMessages ?? true;
        if (logWireMessage)
            log.Write($"received type={message.Type} id={message.Id ?? "-"} method={message.Method ?? "-"}");

        UiMessage response;
        try
        {
            if (message.Type == "hello")
                response = HandleHello(message, log);
            else if (message.Type == "request" && message.Method == UiMethods.HostInfo)
                response = CreateHostInfoResponse(message);
            else if (message.Type == "request" && serviceHandler != null)
                response = await serviceHandler.HandleAsync(message);
            else
                response = CreateErrorResponse(message, "unsupported_message", "Message type or method is not supported.");
        }
        catch (Exception ex)
        {
            log.Write($"request failed method={message.Method ?? "-"}: {ex}");
            response = CreateErrorResponse(message, "request_failed", ex.Message);
        }

        await WriteMessageAsync(stream, response);
        if (logWireMessage)
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

static int? GetIntArgument(string[] values, string name)
{
    var value = GetArgument(values, name);
    return int.TryParse(value, out var result) && result > 0 ? result : null;
}

static string? GetArgument(string[] values, string name)
{
    for (var i = 0; i < values.Length - 1; i++)
        if (string.Equals(values[i], name, StringComparison.OrdinalIgnoreCase))
            return values[i + 1];
    return null;
}

sealed class HostLog
{

    public void Write(string message)
    {
        Console.WriteLine($"[UI-HOST] {message}");
    }
}
