using System.IO;
using System.Text.Json;
using PyRevitLabs.UI.Protocol;

internal static class OutputRequestHandler
{
    public static async Task<UiMessage> HandleAsync(
        UiMessage request,
        OutputWindowManager windows)
    {
        if (request.Payload is null)
            throw new InvalidDataException("Output request payload is required.");

        var payload = request.Payload.Value.Deserialize<OutputRequestPayload>()
            ?? throw new InvalidDataException("Output request payload is invalid.");
        if (string.IsNullOrWhiteSpace(payload.WindowId))
            throw new InvalidDataException("Output window id is required.");

        var windowId = payload.WindowId;
        string? value = null;

        switch (request.Method)
        {
            case "output.create":
                await windows.CreateAsync(
                    windowId,
                    payload.Title ?? "pyRevit",
                    payload.Html ?? "<html><body></body></html>",
                    payload.Width ?? 900,
                    payload.Height ?? 600,
                    payload.Left ?? 100,
                    payload.Top ?? 100);
                break;

            case "output.append":
                await windows.AppendHtmlAsync(windowId, payload.Html ?? string.Empty);
                break;

            case "output.replace_body":
                await windows.ReplaceBodyAsync(windowId, payload.Html ?? string.Empty);
                break;

            case "output.inject":
                await windows.InjectHtmlAsync(
                    windowId,
                    payload.Target ?? "body",
                    payload.Html ?? string.Empty);
                break;
            case "output.set_title":
                await windows.SetTitleAsync(windowId, payload.Title ?? "pyRevit");
                break;

            case "output.set_visibility":
                await windows.SetVisibilityAsync(windowId, payload.Visible ?? true);
                break;

            case "output.set_bounds":
                await windows.SetBoundsAsync(
                    windowId,
                    payload.Width ?? 900,
                    payload.Height ?? 600,
                    payload.Left ?? 100,
                    payload.Top ?? 100);
                break;

            case "output.set_resizable":
                await windows.SetResizableAsync(windowId, payload.Resizable ?? true);
                break;

            case "output.focus":
                await windows.FocusAsync(windowId);
                break;

            case "output.close":
                await windows.CloseAsync(windowId);
                break;
            case "output.navigate":
                await windows.NavigateAsync(windowId, payload.Url ?? "about:blank");
                break;

            case "output.progress":
                await windows.SetProgressAsync(
                    windowId,
                    payload.ProgressValue ?? 0,
                    payload.ProgressMaximum ?? 1,
                    payload.Visible ?? true);
                break;

            case "output.indeterminate":
                await windows.SetIndeterminateAsync(windowId, payload.Indeterminate ?? false);
                break;

            case "output.log":
                await windows.AppendLogAsync(
                    windowId,
                    payload.Level ?? "info",
                    payload.Value ?? string.Empty);
                break;

            case "output.get_html":
                value = await windows.GetHtmlAsync(windowId);
                break;

            case "output.get_text":
                value = await windows.GetTextAsync(windowId);
                break;
            case "output.read_input":
                value = await windows.ReadInputAsync(
                    windowId,
                    payload.InputMode ?? "text",
                    payload.Value);
                break;

            default:
                throw new InvalidOperationException(
                    $"Unsupported output method '{request.Method}'.");
        }

        var response = new OutputResponsePayload(true, value);
        return new UiMessage(
            "response",
            request.Id,
            request.Method,
            JsonSerializer.SerializeToElement(response));
    }
}
