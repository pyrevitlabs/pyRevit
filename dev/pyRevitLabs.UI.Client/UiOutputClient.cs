using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace PyRevitLabs.UI.Client;

/// <summary>
/// Event raised by the isolated UI host for an output window.
/// </summary>
public sealed class UiHostEventArgs : EventArgs
{
    internal UiHostEventArgs(string method, string windowId, string? value)
    {
        Method = method;
        WindowId = windowId;
        Value = value;
    }

    public string Method { get; }
    public string WindowId { get; }
    public string? Value { get; }
}

public sealed partial class UiHostSession
{
    private readonly SemaphoreSlim _requestLock = new SemaphoreSlim(1, 1);

    public event EventHandler<UiHostEventArgs>? EventReceived;
    public Task CreateOutputWindowAsync(
        string windowId,
        string title,
        string html,
        double width,
        double height,
        double left,
        double top)
    {
        return SendOutputCommandAsync(
            "output.create",
            new UiOutputPayload
            {
                WindowId = windowId,
                Title = title,
                Html = html,
                Width = width,
                Height = height,
                Left = left,
                Top = top,
            });
    }

    public Task AppendOutputHtmlAsync(string windowId, string html) =>
        SendOutputCommandAsync("output.append", Payload(windowId, html: html));

    public Task ReplaceOutputBodyAsync(string windowId, string html) =>
        SendOutputCommandAsync("output.replace_body", Payload(windowId, html: html));
    public Task InjectOutputHtmlAsync(string windowId, string target, string html) =>
        SendOutputCommandAsync(
            "output.inject",
            new UiOutputPayload { WindowId = windowId, Target = target, Html = html });

    public Task SetOutputTitleAsync(string windowId, string title) =>
        SendOutputCommandAsync("output.set_title", Payload(windowId, title: title));

    public Task SetOutputVisibilityAsync(string windowId, bool visible) =>
        SendOutputCommandAsync(
            "output.set_visibility",
            new UiOutputPayload { WindowId = windowId, Visible = visible });

    public Task SetOutputBoundsAsync(
        string windowId,
        double width,
        double height,
        double left,
        double top) =>
        SendOutputCommandAsync(
            "output.set_bounds",
            new UiOutputPayload {
                WindowId = windowId,
                Width = width,
                Height = height,
                Left = left,
                Top = top,
            });
    public Task SetOutputResizableAsync(string windowId, bool resizable) =>
        SendOutputCommandAsync(
            "output.set_resizable",
            new UiOutputPayload { WindowId = windowId, Resizable = resizable });

    public Task FocusOutputAsync(string windowId) =>
        SendOutputCommandAsync("output.focus", Payload(windowId));

    public Task CloseOutputAsync(string windowId) =>
        SendOutputCommandAsync("output.close", Payload(windowId));

    public Task NavigateOutputAsync(string windowId, string url) =>
        SendOutputCommandAsync(
            "output.navigate",
            new UiOutputPayload { WindowId = windowId, Url = url });

    public Task SetOutputProgressAsync(
        string windowId,
        double current,
        double maximum,
        bool visible) =>
        SendOutputCommandAsync(
            "output.progress",
            new UiOutputPayload {
                WindowId = windowId,
                ProgressValue = current,
                ProgressMaximum = maximum,
                Visible = visible,
            });
    public Task SetOutputIndeterminateAsync(string windowId, bool state) =>
        SendOutputCommandAsync(
            "output.indeterminate",
            new UiOutputPayload { WindowId = windowId, Indeterminate = state });

    public Task AppendOutputLogAsync(string windowId, string level, string message) =>
        SendOutputCommandAsync(
            "output.log",
            new UiOutputPayload { WindowId = windowId, Level = level, Value = message });

    public async Task<string> GetOutputHtmlAsync(string windowId)
    {
        var response = await SendOutputRequestAsync(
            "output.get_html",
            Payload(windowId)).ConfigureAwait(false);
        return response.Value ?? string.Empty;
    }

    public async Task<string> GetOutputTextAsync(string windowId)
    {
        var response = await SendOutputRequestAsync(
            "output.get_text",
            Payload(windowId)).ConfigureAwait(false);
        return response.Value ?? string.Empty;
    }
    public async Task<string> ReadOutputInputAsync(
        string windowId,
        string mode,
        string? value = null)
    {
        var response = await SendOutputRequestAsync(
            "output.read_input",
            new UiOutputPayload { WindowId = windowId, InputMode = mode, Value = value })
            .ConfigureAwait(false);
        return response.Value ?? string.Empty;
    }

    private static UiOutputPayload Payload(
        string windowId,
        string? title = null,
        string? html = null) =>
        new UiOutputPayload { WindowId = windowId, Title = title, Html = html };

    private async Task SendOutputCommandAsync(string method, UiOutputPayload payload)
    {
        await SendOutputRequestAsync(method, payload).ConfigureAwait(false);
    }

    private async Task<UiOutputResponsePayload> SendOutputRequestAsync(
        string method,
        UiOutputPayload payload)
    {
        ThrowIfDisposed();
        await _requestLock.WaitAsync().ConfigureAwait(false);
        try
        {
            var request = new UiOutputRequestMessage
            {
                Id = Guid.NewGuid().ToString("N"),
                Method = method,
                Payload = payload,
            };
            await WireCodec.WriteAsync(_pipe, request).ConfigureAwait(false);
            var response = await WireCodec.ReadAsync<UiOutputResponseMessage>(_pipe)
                .ConfigureAwait(false);

            if (string.Equals(response.Type, "error", StringComparison.Ordinal))
                throw new InvalidOperationException(
                    response.Error?.Message ?? $"UI host request '{method}' failed.");
            if (!string.Equals(response.Type, "response", StringComparison.Ordinal))
                throw new InvalidDataException(
                    $"Expected response for '{method}', got '{response.Type}'.");
            if (!string.Equals(response.Method, method, StringComparison.Ordinal))
                throw new InvalidDataException(
                    $"Expected method '{method}', got '{response.Method}'.");
            return response.Payload ?? new UiOutputResponsePayload { Ok = true };
        }
        finally
        {
            _requestLock.Release();
        }
    }
    private async Task ListenForEventsAsync()
    {
        try
        {
            while (!_eventCancellation.IsCancellationRequested)
            {
                var message = await WireCodec.ReadAsync<UiEventMessage>(_eventPipe)
                    .ConfigureAwait(false);
                if (!string.Equals(message.Type, "event", StringComparison.Ordinal))
                    continue;
                var payload = message.Payload;
                if (payload == null || string.IsNullOrWhiteSpace(payload.WindowId))
                    continue;
                EventReceived?.Invoke(
                    this,
                    new UiHostEventArgs(
                        message.Method ?? string.Empty,
                        payload.WindowId,
                        payload.Value));
            }
        }
        catch (ObjectDisposedException)
        {
        }
        catch (IOException) when (_eventCancellation.IsCancellationRequested)
        {
        }
        catch (Exception ex)
        {
            Trace.WriteLine($"[UI-CLIENT] event loop stopped: {ex.Message}");
        }
    }
}
[DataContract]
internal sealed class UiOutputRequestMessage
{
    [DataMember(Name = "type")]
    public string Type { get; set; } = "request";

    [DataMember(Name = "id")]
    public string Id { get; set; } = string.Empty;

    [DataMember(Name = "method")]
    public string Method { get; set; } = string.Empty;

    [DataMember(Name = "payload")]
    public UiOutputPayload Payload { get; set; } = new UiOutputPayload();
}

[DataContract]
internal sealed class UiOutputResponseMessage
{
    [DataMember(Name = "type")]
    public string? Type { get; set; }

    [DataMember(Name = "id")]
    public string? Id { get; set; }

    [DataMember(Name = "method")]
    public string? Method { get; set; }
    [DataMember(Name = "payload")]
    public UiOutputResponsePayload? Payload { get; set; }

    [DataMember(Name = "error")]
    public UiOutputErrorPayload? Error { get; set; }
}

[DataContract]
internal sealed class UiOutputPayload
{
    [DataMember(Name = "windowId", EmitDefaultValue = false)]
    public string? WindowId { get; set; }

    [DataMember(Name = "title", EmitDefaultValue = false)]
    public string? Title { get; set; }

    [DataMember(Name = "html", EmitDefaultValue = false)]
    public string? Html { get; set; }

    [DataMember(Name = "target", EmitDefaultValue = false)]
    public string? Target { get; set; }

    [DataMember(Name = "url", EmitDefaultValue = false)]
    public string? Url { get; set; }

    [DataMember(Name = "value", EmitDefaultValue = false)]
    public string? Value { get; set; }
    [DataMember(Name = "inputMode", EmitDefaultValue = false)]
    public string? InputMode { get; set; }

    [DataMember(Name = "level", EmitDefaultValue = false)]
    public string? Level { get; set; }

    [DataMember(Name = "width", EmitDefaultValue = false)]
    public double? Width { get; set; }

    [DataMember(Name = "height", EmitDefaultValue = false)]
    public double? Height { get; set; }

    [DataMember(Name = "left", EmitDefaultValue = false)]
    public double? Left { get; set; }

    [DataMember(Name = "top", EmitDefaultValue = false)]
    public double? Top { get; set; }

    [DataMember(Name = "progressValue", EmitDefaultValue = false)]
    public double? ProgressValue { get; set; }

    [DataMember(Name = "progressMaximum", EmitDefaultValue = false)]
    public double? ProgressMaximum { get; set; }
    [DataMember(Name = "visible", EmitDefaultValue = false)]
    public bool? Visible { get; set; }

    [DataMember(Name = "resizable", EmitDefaultValue = false)]
    public bool? Resizable { get; set; }

    [DataMember(Name = "indeterminate", EmitDefaultValue = false)]
    public bool? Indeterminate { get; set; }
}

[DataContract]
internal sealed class UiOutputResponsePayload
{
    [DataMember(Name = "ok")]
    public bool Ok { get; set; }

    [DataMember(Name = "value", EmitDefaultValue = false)]
    public string? Value { get; set; }
}

[DataContract]
internal sealed class UiOutputErrorPayload
{
    [DataMember(Name = "code")]
    public string? Code { get; set; }

    [DataMember(Name = "message")]
    public string? Message { get; set; }
}
[DataContract]
internal sealed class UiEventMessage
{
    [DataMember(Name = "type")]
    public string? Type { get; set; }

    [DataMember(Name = "method")]
    public string? Method { get; set; }

    [DataMember(Name = "payload")]
    public UiEventPayload? Payload { get; set; }
}

[DataContract]
internal sealed class UiEventPayload
{
    [DataMember(Name = "windowId")]
    public string WindowId { get; set; } = string.Empty;

    [DataMember(Name = "value", EmitDefaultValue = false)]
    public string? Value { get; set; }
}
