using System;
using System.IO;
using System.Runtime.Serialization;
using System.Threading.Tasks;
using PyRevitLabs.UI.Protocol;

namespace PyRevitLabs.UI.Client;

/// <summary>
/// Output-window API composed over a transport-only <see cref="UiHostSession"/>.
/// </summary>
public sealed class UiOutputClient
{
    private readonly UiHostSession _session;

    public UiOutputClient(UiHostSession session)
    {
        _session = session ?? throw new ArgumentNullException(nameof(session));
    }

    public Task CreateWindowAsync(
        string windowId,
        string title,
        string html,
        double width,
        double height,
        double left,
        double top)
    {
        return SendCommandAsync(
            UiMethods.Output.Create,
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

    public Task AppendHtmlAsync(string windowId, string html) =>
        SendCommandAsync(UiMethods.Output.Append, Payload(windowId, html: html));

    public Task ReplaceBodyAsync(string windowId, string html) =>
        SendCommandAsync(UiMethods.Output.ReplaceBody, Payload(windowId, html: html));

    public Task InjectHtmlAsync(string windowId, string target, string html) =>
        SendCommandAsync(
            UiMethods.Output.Inject,
            new UiOutputPayload { WindowId = windowId, Target = target, Html = html });

    public Task SetTitleAsync(string windowId, string title) =>
        SendCommandAsync(UiMethods.Output.SetTitle, Payload(windowId, title: title));
    public Task SetVisibilityAsync(string windowId, bool visible) =>
        SendCommandAsync(
            UiMethods.Output.SetVisibility,
            new UiOutputPayload { WindowId = windowId, Visible = visible });

    public Task SetBoundsAsync(
        string windowId,
        double width,
        double height,
        double left,
        double top) =>
        SendCommandAsync(
            UiMethods.Output.SetBounds,
            new UiOutputPayload
            {
                WindowId = windowId,
                Width = width,
                Height = height,
                Left = left,
                Top = top,
            });

    public Task SetResizableAsync(string windowId, bool resizable) =>
        SendCommandAsync(
            UiMethods.Output.SetResizable,
            new UiOutputPayload { WindowId = windowId, Resizable = resizable });
    public Task FocusAsync(string windowId) =>
        SendCommandAsync(UiMethods.Output.Focus, Payload(windowId));

    public Task CloseAsync(string windowId) =>
        SendCommandAsync(UiMethods.Output.Close, Payload(windowId));

    public Task NavigateAsync(string windowId, string url) =>
        SendCommandAsync(
            UiMethods.Output.Navigate,
            new UiOutputPayload { WindowId = windowId, Url = url });

    public Task SetProgressAsync(
        string windowId,
        double current,
        double maximum,
        bool visible) =>
        SendCommandAsync(
            UiMethods.Output.Progress,
            new UiOutputPayload
            {
                WindowId = windowId,
                ProgressValue = current,
                ProgressMaximum = maximum,
                Visible = visible,
            });

    public Task SetIndeterminateAsync(string windowId, bool state) =>
        SendCommandAsync(
            UiMethods.Output.Indeterminate,
            new UiOutputPayload { WindowId = windowId, Indeterminate = state });

    public Task AppendLogAsync(string windowId, string level, string message) =>
        SendCommandAsync(
            UiMethods.Output.Log,
            new UiOutputPayload { WindowId = windowId, Level = level, Value = message });

    public async Task<string> GetHtmlAsync(string windowId)
    {
        var response = await SendRequestAsync(
            UiMethods.Output.GetHtml,
            Payload(windowId)).ConfigureAwait(false);
        return response.Value ?? string.Empty;
    }

    public async Task<string> GetTextAsync(string windowId)
    {
        var response = await SendRequestAsync(
            UiMethods.Output.GetText,
            Payload(windowId)).ConfigureAwait(false);
        return response.Value ?? string.Empty;
    }

    public async Task<string> ReadInputAsync(
        string windowId,
        string mode,
        string? value = null)
    {
        var response = await SendRequestAsync(
            UiMethods.Output.ReadInput,
            new UiOutputPayload { WindowId = windowId, InputMode = mode, Value = value })
            .ConfigureAwait(false);
        return response.Value ?? string.Empty;
    }

    private static UiOutputPayload Payload(
        string windowId,
        string? title = null,
        string? html = null) =>
        new UiOutputPayload { WindowId = windowId, Title = title, Html = html };

    private async Task SendCommandAsync(string method, UiOutputPayload payload)
    {
        await SendRequestAsync(method, payload).ConfigureAwait(false);
    }

    private async Task<UiOutputResponsePayload> SendRequestAsync(
        string method,
        UiOutputPayload payload)
    {
        var request = new UiOutputRequestMessage
        {
            Id = Guid.NewGuid().ToString("N"),
            Method = method,
            Payload = payload,
        };
        var response = await _session
            .RequestAsync<UiOutputRequestMessage, UiOutputResponseMessage>(request)
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
internal sealed class UiOutputErrorPayload
{
    [DataMember(Name = "code")]
    public string? Code { get; set; }

    [DataMember(Name = "message")]
    public string? Message { get; set; }
}
