namespace Build.Models;

/// <summary>
/// One Chocolatey package built from <c>release/choco</c>: the package files and the signed admin installer it wraps.
/// </summary>
/// <param name="Id">Chocolatey package id, also the prefix of the <c>.nupkg</c> file name.</param>
/// <param name="Nuspec">Path of the <c>.nuspec</c> that <c>choco pack</c> reads.</param>
/// <param name="InstallScript">Path of <c>chocolateyinstall.ps1</c>, whose download URL and checksum are rewritten at pack time.</param>
/// <param name="InstallerNameFormat">File name format (without extension) of the signed installer, taking the install version.</param>
public sealed record ChocoPackage(string Id, string Nuspec, string InstallScript, string InstallerNameFormat)
{
    /// <summary>File name of the packed <c>.nupkg</c> for the given install version.</summary>
    public string NupkgName(string installVersion) => $"{Id}.{installVersion}.nupkg";
}
