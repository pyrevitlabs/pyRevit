using System.ComponentModel;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

[SectionName("telemetry")]
public record TelemetrySection
{
    [KeyName("active")]
    [DefaultValue(false)]
    public bool? TelemetryStatus { get; set; }

    [KeyName("utc_timestamps")]
    [DefaultValue(true)]
    public bool? TelemetryUseUtcTimeStamps { get; set; }

    [KeyName("telemetry_file_dir")]
    [DefaultValue("")]
    public string? TelemetryFileDir { get; set; }

    [KeyName("telemetry_server_url")]
    [DefaultValue("")]
    public string? TelemetryServerUrl { get; set; }

    [KeyName("include_hooks")]
    [DefaultValue(false)]
    public bool? TelemetryIncludeHooks { get; set; }

    [KeyName("active_app")]
    [DefaultValue(false)]
    public bool? AppTelemetryStatus { get; set; }

    [KeyName("apptelemetry_server_url")]
    public string? AppTelemetryServerUrl { get; set; }

    [KeyName("apptelemetry_event_flags")]
    [DefaultValue("")]
    public string? AppTelemetryEventFlags { get; set; }
}
