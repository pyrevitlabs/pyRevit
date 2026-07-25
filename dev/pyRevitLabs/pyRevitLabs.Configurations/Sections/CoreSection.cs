using System.ComponentModel;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

[SectionName("core")]
public sealed record CoreSection
{
    [KeyName("bincache")]
    public bool? BinCache { get; set; }

    [KeyName("loadbeta")]
    public bool? LoadBeta { get; set; }

    [KeyName("closeotheroutputs")]
    public bool? CloseOtherOutputs { get; set; }

    [KeyName("closeoutputmode")]
    public string? CloseOutputMode { get; set; }

    [KeyName("new_loader")]
    [DefaultValue(true)]
    public bool? NewLoader { get; set; }

    [KeyName("read_script_metadata")]
    [DefaultValue(true)]
    public bool? ReadScriptMetadata { get; set; }

    [KeyName("autoupdate")]
    public bool? AutoUpdate { get; set; }

    [KeyName("checkupdates")]
    public bool? CheckUpdates { get; set; }

    [KeyName("usercanupdate")]
    [DefaultValue(true)]
    public bool? UserCanUpdate { get; set; }

    [KeyName("usercanextend")]
    [DefaultValue(true)]
    public bool? UserCanExtend { get; set; }

    [KeyName("usercanconfig")]
    [DefaultValue(true)]
    public bool? UserCanConfig { get; set; }

    [KeyName("rocketmode")]
    [DefaultValue(true)]
    public bool? RocketMode { get; set; }

    [KeyName("user_locale")]
    public string? UserLocale { get; set; }

    [KeyName("debug")]
    public bool? Debug { get; set; }

    [KeyName("verbose")]
    public bool? Verbose { get; set; }

    [KeyName("filelogging")]
    public bool? FileLogging { get; set; }

    [KeyName("startuplogtimeout")]
    [DefaultValue(10)]
    public int? StartupLogTimeout { get; set; }

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

    // No initializer: an unset value stays null so a sparse-section save does not
    // rewrite (and clobber) this key. CreateSection supplies an empty list on read.
    [KeyName("userextensions")]
    public List<string>? UserExtensions { get; set; }
}
