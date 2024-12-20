namespace pyRevitLabs.Configurations;

public enum LogLevels
{
    Quiet,
    Verbose,
    Debug
}

internal sealed record CoreSection
{
    public bool BinCache { get; set; }

    public bool LoadBeta { get; set; }
    public bool AutoUpdate { get; set; }
    public bool CheckUpdates { get; set; }

    public bool UserCanUpdate { get; set; } = true;
    public bool UserCanExtend { get; set; } = true;
    public bool UserCanConfig { get; set; } = true;

    public bool RocketMode { get; set; } = true;
    public string UserLocale { get; set; } = "en_us";

    public LogLevels LogLevel { get; set; }
    public bool FileLogging { get; set; }
    public int StartupLogTimeout { get; set; } = 10;

    public int CpythonEngineVersion { get; set; }
    public bool RequiredHostBuild { get; set; }
    public long MinHostDriveFreeSpace { get; set; }

    public bool ColorizeDocs { get; set; }
    public bool TooltipDebugInfo { get; set; }
    public string? OutputStylesheet { get; set; }
}