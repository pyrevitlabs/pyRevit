using System.Text.Json;
using System.Text.Json.Serialization;

namespace PyRevitLabs.UI.Protocol;

public static class UiProtocol
{
    public const int Version = 1;
}

public sealed record UiMessage(
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("id")] string? Id = null,
    [property: JsonPropertyName("method")] string? Method = null,
    [property: JsonPropertyName("payload")] JsonElement? Payload = null);

public sealed record HelloPayload(
    [property: JsonPropertyName("protocolVersion")] int ProtocolVersion,
    [property: JsonPropertyName("clientName")] string ClientName,
    [property: JsonPropertyName("processId")] int ProcessId);

public sealed record HostInfo(
    [property: JsonPropertyName("protocolVersion")] int ProtocolVersion,
    [property: JsonPropertyName("hostProcessId")] int HostProcessId,
    [property: JsonPropertyName("hostVersion")] string HostVersion);
