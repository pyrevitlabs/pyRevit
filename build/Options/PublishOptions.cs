namespace Build.Options;

public sealed class PublishOptions
{
    public string Repository { get; set; } = "pyrevitlabs/pyRevit";

    public string ChocoSource { get; set; } = "https://push.chocolatey.org/";

    public string ChocoToken { get; set; } = string.Empty;

    public string WingetCreateExe { get; set; } = "wingetcreate.exe";

    public string WingetToken { get; set; } = string.Empty;

    public bool DraftRelease { get; set; } = true;

    public bool SubmitWinget { get; set; } = true;

    /// <summary>
    /// Previous catalog version to replace when submitting a newer version (wingetcreate submit -r).
    /// Must differ from the version being submitted. Not used for same-version resubmits.
    /// </summary>
    public string WingetReplaceVersion { get; set; } = string.Empty;
}
