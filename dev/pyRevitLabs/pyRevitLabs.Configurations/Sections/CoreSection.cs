using System.ComponentModel;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Attributes;

namespace pyRevitLabs.Configurations.Sections;

/// <summary>
/// The <c>[core]</c> section: session-wide pyRevit behavior.
/// <para>
/// Every property is nullable and null means "not set in the file". Reading a
/// section through <see cref="IConfigurationService.Core"/> replaces a null with
/// the property's declared default, so a null survives only on a record the
/// caller constructed for a write, where it means "leave this key alone".
/// </para>
/// </summary>
[SectionName("core")]
public sealed record CoreSection
{
    /// <summary>Whether extension metadata is cached in binary form between sessions. Default true.</summary>
    [KeyName("bincache")]
    [DefaultValue(true)]
    public bool? BinCache { get; set; }

    /// <summary>Whether commands marked beta are loaded into the UI. Default false.</summary>
    [KeyName("loadbeta")]
    [LegacyKeyName("load_beta")]
    [DefaultValue(false)]
    public bool? LoadBeta { get; set; }

    /// <summary>
    /// Whether closing an output window also closes the others. Interpreted
    /// together with <see cref="CloseOutputMode"/>. Default false.
    /// </summary>
    [KeyName("closeotheroutputs")]
    [DefaultValue(false)]
    public bool? CloseOtherOutputs { get; set; }

    /// <summary>
    /// Which output windows the close action applies to: <c>"currentcommand"</c>
    /// (the default when unset or unrecognized) or <c>"closeall"</c>. Compared
    /// case-insensitively.
    /// </summary>
    [KeyName("closeoutputmode")]
    public string? CloseOutputMode { get; set; }

    /// <summary>
    /// Whether script metadata dunders (<c>__title__</c>, <c>__author__</c>, …)
    /// are read from .py files at startup. Disabling speeds up load at the cost
    /// of bundle.yaml being the only metadata source. Default true.
    /// </summary>
    [KeyName("read_script_metadata")]
    [DefaultValue(true)]
    public bool? ReadScriptMetadata { get; set; }

    /// <summary>Whether pyRevit updates itself on startup. Default false.</summary>
    [KeyName("autoupdate")]
    [DefaultValue(false)]
    public bool? AutoUpdate { get; set; }

    /// <summary>Whether pyRevit checks for available updates on startup. Default false.</summary>
    [KeyName("checkupdates")]
    [DefaultValue(false)]
    public bool? CheckUpdates { get; set; }

    /// <summary>Whether the user is allowed to update the pyRevit clone. Default true.</summary>
    [KeyName("usercanupdate")]
    [DefaultValue(true)]
    public bool? UserCanUpdate { get; set; }

    /// <summary>Whether the user is allowed to install and enable extensions. Default true.</summary>
    [KeyName("usercanextend")]
    [DefaultValue(true)]
    public bool? UserCanExtend { get; set; }

    /// <summary>Whether the user is allowed to change settings. Default true.</summary>
    [KeyName("usercanconfig")]
    [DefaultValue(true)]
    public bool? UserCanConfig { get; set; }

    /// <summary>
    /// Whether all scripts share one engine per session instead of getting a
    /// fresh engine per run. Faster, but leaks state between scripts. Default true.
    /// </summary>
    [KeyName("rocketmode")]
    [DefaultValue(true)]
    public bool? RocketMode { get; set; }

    /// <summary>
    /// Preferred UI language as a locale code (e.g. <c>"en_us"</c>). No default:
    /// when unset the language is detected from the Revit UI.
    /// </summary>
    [KeyName("user_locale")]
    public string? UserLocale { get; set; }

    /// <summary>
    /// Whether debug-level logging is enabled. Implies <see cref="Verbose"/>.
    /// No default: unset is treated as off.
    /// </summary>
    [KeyName("debug")]
    public bool? Debug { get; set; }

    /// <summary>
    /// Whether verbose logging is enabled. No default: unset is treated as off.
    /// </summary>
    [KeyName("verbose")]
    public bool? Verbose { get; set; }

    /// <summary>Whether log output is also written to a file. Default false.</summary>
    [KeyName("filelogging")]
    [DefaultValue(false)]
    public bool? FileLogging { get; set; }

    /// <summary>
    /// Seconds the startup log window stays open before closing on its own.
    /// Default 10.
    /// </summary>
    [KeyName("startuplogtimeout")]
    [DefaultValue(10)]
    public int? StartupLogTimeout { get; set; }

    /// <summary>
    /// CPython engine to run scripts with, as its version number (e.g. 312).
    /// Default 0, meaning no specific engine is pinned and the newest engine
    /// available in the clone is used.
    /// </summary>
    [KeyName("cpyengine")]
    [DefaultValue(0)]
    public int? CpythonEngineVersion { get; set; }

    /// <summary>
    /// Revit build number this deployment expects (e.g. <c>"20240118_1515(x64)"</c>).
    /// A mismatch logs a startup warning; it does not block loading. Default
    /// empty, meaning no build is required.
    /// </summary>
    [KeyName("requiredhostbuild")]
    [DefaultValue("")]
    public string? RequiredHostBuild { get; set; }

    /// <summary>
    /// Minimum free space, in gigabytes, on the drive Revit runs from. Falling
    /// below it logs a startup warning; it does not block loading. Default 0,
    /// which disables the check.
    /// </summary>
    [KeyName("minhostdrivefreespace")]
    [DefaultValue(0L)]
    public long? MinHostDriveFreeSpace { get; set; }

    /// <summary>Whether open documents are color-coded in the Revit tab bar. Default false.</summary>
    [KeyName("colorize_docs")]
    [DefaultValue(false)]
    public bool? ColorizeDocs { get; set; }

    /// <summary>
    /// Whether button tooltips include the script path and other debug details.
    /// Default false.
    /// </summary>
    [KeyName("tooltip_debug_info")]
    [DefaultValue(false)]
    public bool? TooltipDebugInfo { get; set; }

    /// <summary>
    /// Path to a CSS file styling output windows. Default empty, meaning the
    /// built-in stylesheet is used. Removing the key (rather than storing an
    /// empty string) is what reverts a customized deployment to the built-in one.
    /// </summary>
    [KeyName("outputstylesheet")]
    [DefaultValue("")]
    public string? OutputStyleSheet { get; set; }

    // No initializer: an unset value stays null so a sparse-section save does not
    // rewrite (and clobber) this key. CreateSection supplies an empty list on read.

    /// <summary>
    /// Directories searched for user extensions, in order. Read back as an empty
    /// list when unset.
    /// </summary>
    [KeyName("userextensions")]
    public List<string>? UserExtensions { get; set; }
}
