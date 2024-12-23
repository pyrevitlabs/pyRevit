namespace pyRevitLabs.Configurations;

public record TelemetrySection
{
    public bool TelemetryStatus { get; set; }
    
    public bool TelemetryUseUtcTimeStamps { get; set; }
    public string? TelemetryFileDir { get; set; }
    public string? TelemetryServerUrl { get; set; }
    public bool TelemetryIncludeHooks { get; set; }

    public bool AppTelemetryStatus { get; set; }
    public string? AppTelemetryServerUrl { get; set; }
    public int AppTelemetryEventFlags { get; set; }
}