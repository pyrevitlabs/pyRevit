namespace pyRevitLabs.Configurations;

internal record TelemetrySection
{
    public bool UtcTimeStamps { get; set; }
    public bool Status { get; set; }
    public string? FileDir { get; set; }
    public string? ServerUrl { get; set; }
    public bool IncludeHooks { get; set; }

    public bool AppTelemetryStatus { get; set; }
    public string? AppTelemetryServerUrl { get; set; }
    public int AppTelemetryEventFlags { get; set; }
}