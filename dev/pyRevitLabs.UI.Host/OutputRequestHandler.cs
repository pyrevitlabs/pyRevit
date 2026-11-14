using System.IO;
using System.Text.Json;
using PyRevitLabs.UI.Protocol;

internal sealed class OutputServiceHandler : IUiServiceHandler
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    };

    private readonly OutputWindowManager _windows;

    public OutputServiceHandler(OutputWindowManager windows)
    {
        _windows = windows ?? throw new ArgumentNullException(nameof(windows));
    }

    public string ServiceName => UiServices.Output;
    public bool LogWireMessages => false;

    public async Task<UiMessage> HandleAsync(UiMessage request)
    {
        if (request.Payload is null)
            throw new InvalidDataException("Output request payload is required.");

        var payload = request.Payload.Value.Deserialize<UiOutputPayload>(JsonOptions)
            ?? throw new InvalidDataException("Output request payload is invalid.");
        if (string.IsNullOrWhiteSpace(payload.WindowId))
            throw new InvalidDataException("Output window id is required.");

        var windowId = payload.WindowId;
        string? value = null;

        switch (request.Method)
        {
            case UiMethods.Output.Create:
                await _windows.CreateAsync(
                    windowId,
                    payload.Title ?? "pyRevit",
                    payload.Html ?? "<html><body></body></html>",
                    payload.Width ?? 900,
                    payload.Height ?? 600,
                    payload.Left ?? 100,
                    payload.Top ?? 100);
                break;

            case UiMethods.Output.Append:
                await _windows.AppendHtmlAsync(windowId, payload.Html ?? string.Empty);
                break;

            case UiMethods.Output.ReplaceBody:
                await _windows.ReplaceBodyAsync(windowId, payload.Html ?? string.Empty);
                break;

            case UiMethods.Output.Inject:
                await _windows.InjectHtmlAsync(
                    windowId,
                    payload.Target ?? "body",
                    payload.Html ?? string.Empty);
                break;

            case UiMethods.Output.SetTitle:
                await _windows.SetTitleAsync(windowId, payload.Title ?? "pyRevit");
                break;

            case UiMethods.Output.SetVisibility:
                await _windows.SetVisibilityAsync(windowId, payload.Visible ?? true);
                break;

            case UiMethods.Output.SetBounds:
                await _windows.SetBoundsAsync(
                    windowId,
                    payload.Width ?? 900,
                    payload.Height ?? 600,
                    payload.Left ?? 100,
                    payload.Top ?? 100);
                break;

            case UiMethods.Output.SetResizable:
                await _windows.SetResizableAsync(windowId, payload.Resizable ?? true);
                break;

            case UiMethods.Output.Focus:
                await _windows.FocusAsync(windowId);
                break;

            case UiMethods.Output.Close:
                await _windows.CloseAsync(windowId);
                break;

            case UiMethods.Output.Navigate:
                await _windows.NavigateAsync(windowId, payload.Url ?? "about:blank");
                break;

            case UiMethods.Output.Progress:
                await _windows.SetProgressAsync(
                    windowId,
                    payload.ProgressValue ?? 0,
                    payload.ProgressMaximum ?? 1,
                    payload.Visible ?? true);
                break;

            case UiMethods.Output.Indeterminate:
                await _windows.SetIndeterminateAsync(windowId, payload.Indeterminate ?? false);
                break;

            case UiMethods.Output.Log:
                await _windows.AppendLogAsync(
                    windowId,
                    payload.Level ?? "info",
                    payload.Value ?? string.Empty);
                break;

            case UiMethods.Output.GetHtml:
                value = await _windows.GetHtmlAsync(windowId);
                break;

            case UiMethods.Output.GetText:
                value = await _windows.GetTextAsync(windowId);
                break;

            case UiMethods.Output.ReadInput:
                value = await _windows.ReadInputAsync(
                    windowId,
                    payload.InputMode ?? "text",
                    payload.Value);
                break;

            default:
                throw new InvalidOperationException(
                    $"Unsupported output method '{request.Method}'.");
        }

        var response = new UiOutputResponsePayload { Ok = true, Value = value };
        return new UiMessage(
            "response",
            request.Id,
            request.Method,
            JsonSerializer.SerializeToElement(response, JsonOptions));
    }
}
