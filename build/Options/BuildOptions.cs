namespace Build.Options;

public sealed class BuildOptions
{
    public string MainRepository { get; set; } = "pyrevitlabs/pyRevit";

    public string Configuration { get; set; } = "Release";

    /// <summary>Build channel: none, wip, or release.</summary>
    public string Channel { get; set; } = "none";

    public bool SkipStamping { get; set; }

    public string TimestampUrl { get; set; } = "http://timestamp.acs.microsoft.com";

    public string? HeadSha { get; set; }

    public string? NotifyUrl { get; set; }

    public string? CiRunId { get; set; }

    /// <summary>When true, validate installer tooling such as MSBuild (pack/sign/publish paths).</summary>
    public bool RequireInstallerTooling { get; set; }
}
