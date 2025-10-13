using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

public enum LogLevels
{
    Quiet,
    Verbose,
    Debug
}

[SectionName("core")]
public sealed record CoreSection
{
    [KeyName("bincache")]
    public bool? BinCache { get; set; }

    [KeyName("loadbeta")]
    public bool? LoadBeta { get; set; }
    
    [KeyName("autoupdate")]
    public bool? AutoUpdate { get; set; }
    
    [KeyName("checkupdates")]
    public bool? CheckUpdates { get; set; }

    [KeyName("usercanupdate")]
    public bool? UserCanUpdate { get; set; } = true;

    [KeyName("usercanextend")]
    public bool? UserCanExtend { get; set; } = true;
    
    [KeyName("usercanconfig")]
    public bool? UserCanConfig { get; set; } = true;

    [KeyName("rocketmode")]
    public bool? RocketMode { get; set; } = true;
    
    [KeyName("user_locale")]
    public string? UserLocale { get; set; } = "en_us";
    
    [KeyName("debug")]
    public bool? Debug { get; set; }
    
    [KeyName("verbose")]
    public bool? Verbose { get; set; }
    
    [KeyName("filelogging")]
    public bool? FileLogging { get; set; }
    
    [KeyName("startuplogtimeout")]
    public int? StartupLogTimeout { get; set; } = 10;

    [KeyName("cpyengine")]
    public int? CpythonEngineVersion { get; set; }
    
    [KeyName("requiredhostbuild")]
    public string? RequiredHostBuild { get; set; }
    
    [KeyName("minhostdrivefreespace")]
    public long? MinHostDriveFreeSpace { get; set; }

    [KeyName("colorize_docs")]
    public bool? ColorizeDocs { get; set; }
    
    [KeyName("tooltip_debug_info")]
    public bool? TooltipDebugInfo { get; set; }
    
    [KeyName("outputstylesheet")]
    public string? OutputStyleSheet { get; set; }
    
    [KeyName("userextensions")]
    public List<string> UserExtensions { get; set; } = new();
}