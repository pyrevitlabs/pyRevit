using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations;

[SectionName("telemetry")]
public record TelemetrySection
{
    [KeyName("active")]
    public bool? TelemetryStatus { get; set; }
    
    [KeyName("utc_timestamps")]
    public bool? TelemetryUseUtcTimeStamps { get; set; }
    
    [KeyName("telemetry_file_dir")]
    public string? TelemetryFileDir { get; set; }
    
    [KeyName("telemetry_server_url")]
    public string? TelemetryServerUrl { get; set; }
    
    [KeyName("include_hooks")]
    public bool? TelemetryIncludeHooks { get; set; }

    [KeyName("active_app")]
    public bool? AppTelemetryStatus { get; set; }
    
    [KeyName("apptelemetry_server_url")]
    public string? AppTelemetryServerUrl { get; set; }
    
    [KeyName("apptelemetry_event_flags")]
    public int? AppTelemetryEventFlags { get; set; }
}