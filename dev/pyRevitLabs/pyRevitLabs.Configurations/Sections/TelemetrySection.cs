using System.ComponentModel;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

/// <summary>
/// The <c>[telemetry]</c> section: usage reporting for script runs and Revit
/// application events. The two are configured independently — script telemetry
/// through the <c>Telemetry*</c> properties, application-event telemetry through
/// the <c>AppTelemetry*</c> ones. Null means "not set in the file"; see
/// <see cref="CoreSection"/> for how nulls resolve on read.
/// </summary>
[SectionName("telemetry")]
public record TelemetrySection
{
    /// <summary>Whether script-execution telemetry is recorded. Default false.</summary>
    [KeyName("active")]
    [DefaultValue(false)]
    public bool? TelemetryStatus { get; set; }

    /// <summary>
    /// Whether telemetry timestamps are recorded in UTC rather than local time.
    /// Default true.
    /// </summary>
    [KeyName("utc_timestamps")]
    [DefaultValue(true)]
    public bool? TelemetryUseUtcTimeStamps { get; set; }

    /// <summary>
    /// Directory that receives telemetry log files. Default empty, which
    /// disables file output; the directory must already exist.
    /// </summary>
    [KeyName("telemetry_file_dir")]
    [DefaultValue("")]
    public string? TelemetryFileDir { get; set; }

    /// <summary>
    /// URL of the telemetry server receiving script records. Default empty,
    /// which disables server reporting. Independent of
    /// <see cref="TelemetryFileDir"/>; either, both, or neither may be set.
    /// </summary>
    [KeyName("telemetry_server_url")]
    [DefaultValue("")]
    public string? TelemetryServerUrl { get; set; }

    /// <summary>
    /// Whether hook script executions are reported alongside command runs.
    /// Default false.
    /// </summary>
    [KeyName("include_hooks")]
    [DefaultValue(false)]
    public bool? TelemetryIncludeHooks { get; set; }

    /// <summary>Whether Revit application-event telemetry is recorded. Default false.</summary>
    [KeyName("active_app")]
    [DefaultValue(false)]
    public bool? AppTelemetryStatus { get; set; }

    /// <summary>
    /// URL of the server receiving application-event records. No default:
    /// unset disables reporting.
    /// </summary>
    [KeyName("apptelemetry_server_url")]
    public string? AppTelemetryServerUrl { get; set; }

    /// <summary>
    /// Which Revit events are reported, as a bitmask. Stored as a string (a hex
    /// literal such as <c>"0x8000000"</c> is accepted) because the flag set
    /// exceeds what a 32-bit integer can carry. Default empty, meaning no events.
    /// </summary>
    [KeyName("apptelemetry_event_flags")]
    [DefaultValue("")]
    public string? AppTelemetryEventFlags { get; set; }
}
