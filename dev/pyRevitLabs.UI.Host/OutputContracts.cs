using System.Text.Json.Serialization;

internal sealed record OutputRequestPayload(
    [property: JsonPropertyName("windowId")] string? WindowId = null,
    [property: JsonPropertyName("title")] string? Title = null,
    [property: JsonPropertyName("html")] string? Html = null,
    [property: JsonPropertyName("target")] string? Target = null,
    [property: JsonPropertyName("url")] string? Url = null,
    [property: JsonPropertyName("value")] string? Value = null,
    [property: JsonPropertyName("inputMode")] string? InputMode = null,
    [property: JsonPropertyName("level")] string? Level = null,
    [property: JsonPropertyName("width")] double? Width = null,
    [property: JsonPropertyName("height")] double? Height = null,
    [property: JsonPropertyName("left")] double? Left = null,
    [property: JsonPropertyName("top")] double? Top = null,
    [property: JsonPropertyName("progressValue")] double? ProgressValue = null,
    [property: JsonPropertyName("progressMaximum")] double? ProgressMaximum = null,
    [property: JsonPropertyName("visible")] bool? Visible = null,
    [property: JsonPropertyName("resizable")] bool? Resizable = null,
    [property: JsonPropertyName("indeterminate")] bool? Indeterminate = null);

internal sealed record OutputResponsePayload(
    [property: JsonPropertyName("ok")] bool Ok = true,
    [property: JsonPropertyName("value")] string? Value = null);
