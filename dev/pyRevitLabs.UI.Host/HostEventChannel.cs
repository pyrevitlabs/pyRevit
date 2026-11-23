using System.IO.Pipes;
using System.Text.Json;
using PyRevitLabs.UI.Protocol;

internal sealed class HostEventChannel : IAsyncDisposable
{
    private readonly NamedPipeClientStream _pipe;
    private readonly SemaphoreSlim _writeLock = new(1, 1);

    private HostEventChannel(NamedPipeClientStream pipe)
    {
        _pipe = pipe;
    }

    public static async Task<HostEventChannel> ConnectAsync(string pipeName)
    {
        var pipe = new NamedPipeClientStream(
            ".",
            pipeName,
            PipeDirection.Out,
            PipeOptions.Asynchronous);
        await pipe.ConnectAsync(5000);
        return new HostEventChannel(pipe);
    }

    public async Task SendAsync(string method, string windowId, string? value = null)
    {
        var message = new UiMessage(
            "event",
            Method: method,
            Payload: JsonSerializer.SerializeToElement(
                new UiEventPayload { WindowId = windowId, Value = value }));
        var payload = JsonSerializer.SerializeToUtf8Bytes(message);
        var length = BitConverter.GetBytes(payload.Length);

        await _writeLock.WaitAsync();
        try
        {
            await _pipe.WriteAsync(length);
            await _pipe.WriteAsync(payload);
            await _pipe.FlushAsync();
        }
        finally
        {
            _writeLock.Release();
        }
    }

    public async ValueTask DisposeAsync()
    {
        _pipe.Dispose();
        _writeLock.Dispose();
        await Task.CompletedTask;
    }
}
