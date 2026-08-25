namespace Build.Models;

public sealed record VersionInfo(
    string BuildVersion,
    string InstallVersion,
    string BuildVersionUrlSafe,
    bool IsWip);
