using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Coverage for the exact-path allowlist and the PATH rewriting behind <c>purge-files</c>.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class PurgeTargetsTests {
    private static readonly MachineLocations Locations = new() {
        AppData = @"C:\Users\fake\AppData\Roaming",
        LocalAppData = @"C:\Users\fake\AppData\Local",
        ProgramFiles = @"C:\Program Files",
        ProgramData = @"C:\ProgramData",
        Documents = @"C:\Users\fake\Documents",
    };

    [Fact]
    public void InstallAndDataDirectoriesAreTheDocumentedPaths() {
        Assert.Equal(
            new[] {
                @"C:\Users\fake\AppData\Roaming\pyRevit-Master",
                @"C:\Program Files\pyRevit-Master",
                @"C:\Program Files\pyRevit CLI",
                @"C:\Users\fake\AppData\Local\Programs\pyRevit CLI",
            },
            PurgeTargets.InstallDirectories(Locations));
        Assert.Equal(
            new[] { @"C:\Users\fake\AppData\Roaming\pyRevit", @"C:\ProgramData\pyRevit" },
            PurgeTargets.DataDirectories(Locations));
    }

    /// <summary>
    /// Revit 2027+ reads all-users manifests from Program Files, older years from ProgramData, and
    /// per-user ones from AppData. Program Files folders of earlier years belong to Autodesk.
    /// </summary>
    [Fact]
    public void AddinManifestsFollowTheYearFoldersFoundOnDisk() {
        var folders = new Dictionary<string, string[]> {
            [@"C:\Users\fake\AppData\Roaming\Autodesk\Revit\Addins"] = new[] { @"C:\Users\fake\AppData\Roaming\Autodesk\Revit\Addins\2024", @"C:\Users\fake\AppData\Roaming\Autodesk\Revit\Addins\notayear" },
            [@"C:\ProgramData\Autodesk\Revit\Addins"] = new[] { @"C:\ProgramData\Autodesk\Revit\Addins\2026" },
            [@"C:\Program Files\Autodesk\Revit\Addins"] = new[] { @"C:\Program Files\Autodesk\Revit\Addins\2025", @"C:\Program Files\Autodesk\Revit\Addins\2027" },
        };

        var manifests = PurgeTargets.AddinManifests(Locations, root => folders.GetValueOrDefault(root, Array.Empty<string>()));

        Assert.Equal(
            new[] {
                @"C:\Users\fake\AppData\Roaming\Autodesk\Revit\Addins\2024\pyRevit.addin",
                @"C:\ProgramData\Autodesk\Revit\Addins\2026\pyRevit.addin",
                @"C:\Program Files\Autodesk\Revit\Addins\2027\pyRevit.addin",
            },
            manifests);
    }

    [Theory]
    [InlineData(@"pyRevitfile")]
    [InlineData(@"bin\pyrevit.exe")]
    [InlineData(@"pyRevit_config.ini")]
    public void DirectoryWithAnyMarkerIsAccepted(string markerFile) {
        var marker = Path.Combine(@"C:\target", markerFile);

        Assert.True(PurgeTargets.HasPyRevitMarker(@"C:\target", path => path == marker));
    }

    [Fact]
    public void DirectoryWithoutMarkerIsRefused() {
        Assert.False(PurgeTargets.HasPyRevitMarker(@"C:\target", _ => false));
    }

    [Fact]
    public void OnlyBinEntriesOfTheInstallDirectoriesAreRemovedFromPath() {
        var installs = PurgeTargets.InstallDirectories(Locations);
        var path = string.Join(";",
            @"C:\Windows",
            @"%APPDATA%\pyRevit-Master\bin",
            @"C:\Tools\bin",
            @"c:\program files\pyrevit cli\BIN\",
            @"C:\Program Files\pyRevit CLI\bin\extra",
            "");

        var updated = PurgeTargets.RemoveBinEntries(
            path,
            value => value.Replace("%APPDATA%", Locations.AppData),
            installs,
            out var removed);

        Assert.Equal(@"C:\Windows;C:\Tools\bin;C:\Program Files\pyRevit CLI\bin\extra;", updated);
        Assert.Equal(new[] { @"%APPDATA%\pyRevit-Master\bin", @"c:\program files\pyrevit cli\BIN\" }, removed);
    }

    [Fact]
    public void PathWithoutMatchingEntriesIsReturnedUnchanged() {
        var path = @"C:\Windows;C:\Tools\bin";

        var updated = PurgeTargets.RemoveBinEntries(path, value => value, PurgeTargets.InstallDirectories(Locations), out var removed);

        Assert.Equal(path, updated);
        Assert.Empty(removed);
    }
}
