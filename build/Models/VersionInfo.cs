namespace Build.Models;

/// <summary>
/// Version strings for one build, all derived from the stamped build version.
/// </summary>
/// <param name="BuildVersion">Full version with build metadata, such as <c>7.1.0.26319+1907</c>; used for tags.</param>
/// <param name="InstallVersion">Version without the <c>+HHmm</c> metadata, such as <c>7.1.0.26319</c>; used for installer names.</param>
/// <param name="BuildVersionUrlSafe"><paramref name="BuildVersion"/> with <c>+</c> encoded for URLs.</param>
/// <param name="IsWip">True for WIP channel builds.</param>
/// <param name="SemanticVersion"><c>major.minor.patch</c> only, such as <c>7.1.0</c>; the public release title uses it.</param>
public sealed record VersionInfo(
    string BuildVersion,
    string InstallVersion,
    string BuildVersionUrlSafe,
    bool IsWip,
    string SemanticVersion);
