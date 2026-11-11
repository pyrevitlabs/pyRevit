using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Coverage for pyrevitlabs/pyRevit#3978: registry matching must recognise the keys the shipped
/// installers write and must not purge an install that is still on disk.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class UninstallEntryMatcherTests {
    private const string PyRevitAppId = "f2a3da53-6f34-41d5-abbd-389ffa7f4d5f";
    private const string CliAppId = "9557b432-cf79-4ece-91cf-b8f996c88b47";
    private const string InstalledUninstaller = @"C:\Users\fake\AppData\Roaming\pyRevit-Master\unins000.exe";
    private const string InstalledLocation = @"C:\Users\fake\AppData\Roaming\pyRevit-Master\";

    private static readonly IReadOnlyCollection<Product> ShippedProducts = ProductCatalog.Parse(
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Fixtures", "pyrevit-products.json")));

    private static UninstallEntry InnoEntry(string appId, string displayName = "pyRevit") => new() {
        SubKeyName = $"{appId}_is1",
        DisplayName = displayName,
        UninstallString = $"\"{InstalledUninstaller}\"",
        InstallLocation = InstalledLocation,
    };

    private static Func<string, bool> Present(params string[] paths) => path => paths.Contains(path, StringComparer.OrdinalIgnoreCase);

    private static Func<string, bool> InstallOnDisk => Present(InstalledUninstaller, InstalledLocation.TrimEnd('\\'));

    /// <summary>
    /// Guards the original defect: an <c>{AppId}_is1</c> key equals neither the product key nor
    /// <c>"{Name} {Version}"</c>, so the entries of current installers were never purged.
    /// </summary>
    [Theory]
    [InlineData(PyRevitAppId)]
    [InlineData(CliAppId)]
    public void InnoEntryWhoseInstallIsGoneIsPurged(string appId) {
        var verdict = UninstallEntryMatcher.Classify(InnoEntry(appId), ShippedProducts, Present(), force: false);

        Assert.Equal(UninstallVerdict.Purge, verdict);
    }

    /// <summary>
    /// All pyRevit Inno installs share one AppId, so a present install must not be purged on the key alone.
    /// </summary>
    [Theory]
    [InlineData(PyRevitAppId)]
    [InlineData(CliAppId)]
    public void InnoEntryWhoseInstallIsPresentIsSkipped(string appId) {
        var verdict = UninstallEntryMatcher.Classify(InnoEntry(appId), ShippedProducts, InstallOnDisk, force: false);

        Assert.Equal(UninstallVerdict.SkipInstallPresent, verdict);
    }

    [Fact]
    public void InnoEntryWithMissingInstallLocationButPresentUninstallerIsPurged() {
        var verdict = UninstallEntryMatcher.Classify(InnoEntry(PyRevitAppId), ShippedProducts, Present(InstalledUninstaller), force: false);

        Assert.Equal(UninstallVerdict.Purge, verdict);
    }

    [Fact]
    public void ForcePurgesInnoEntryWhoseInstallIsPresent() {
        var verdict = UninstallEntryMatcher.Classify(InnoEntry(PyRevitAppId), ShippedProducts, InstallOnDisk, force: true);

        Assert.Equal(UninstallVerdict.Purge, verdict);
    }

    [Theory]
    [InlineData("{CA372AB6-355A-4270-91DD-144DF75E1B57}")]
    [InlineData("{ca372ab6-355a-4270-91dd-144df75e1b57}")]
    [InlineData("{8E0191BC-C5DB-4F0E-8F52-6DF04C2B8CE8}")]
    public void BracedMsiProductCodeIsPurged(string subKeyName) {
        var entry = new UninstallEntry { SubKeyName = subKeyName };

        Assert.Equal(UninstallVerdict.Purge, UninstallEntryMatcher.Classify(entry, ShippedProducts, Present(), force: false));
    }

    [Fact]
    public void LegacyNameAndVersionSubKeyIsPurged() {
        var entry = new UninstallEntry { SubKeyName = "pyRevit 4.8.8" };

        Assert.Equal(UninstallVerdict.Purge, UninstallEntryMatcher.Classify(entry, ShippedProducts, Present(), force: false));
    }

    /// <summary>
    /// The display-name fallback cannot tell products apart, so it follows the same staleness rule.
    /// </summary>
    [Fact]
    public void UnknownKeyWithPyRevitDisplayNameIsGatedByStaleness() {
        var entry = InnoEntry("0d5b2f7e-3c1a-4b8e-9f60-2a7d4c9e1b35", displayName: "pyRevit CLI 9.9");

        Assert.Equal(UninstallVerdict.Purge, UninstallEntryMatcher.Classify(entry, ShippedProducts, Present(), force: false));
        Assert.Equal(UninstallVerdict.SkipInstallPresent, UninstallEntryMatcher.Classify(entry, ShippedProducts, InstallOnDisk, force: false));
    }

    [Theory]
    [InlineData("Git_is1", "Git")]
    [InlineData("{11111111-2222-3333-4444-555555555555}", "Autodesk Revit 2025")]
    [InlineData("", null)]
    public void UnrelatedEntryIsNotMatched(string subKeyName, string displayName) {
        var entry = new UninstallEntry { SubKeyName = subKeyName, DisplayName = displayName };

        Assert.Equal(UninstallVerdict.NotPyRevit, UninstallEntryMatcher.Classify(entry, ShippedProducts, Present(), force: true));
    }

    /// <summary>
    /// <c>MsiExec.exe</c> has no folder, so it cannot be probed and must not make a live entry look stale.
    /// </summary>
    [Fact]
    public void EntryWithoutVerifiablePathCountsAsPresent() {
        var entry = new UninstallEntry { SubKeyName = $"{PyRevitAppId}_is1", DisplayName = "pyRevit", UninstallString = "MsiExec.exe /X{ABC}" };

        Assert.False(UninstallEntryMatcher.IsStale(entry, Present()));
    }

    [Theory]
    [InlineData("\"C:\\Program Files\\pyRevit\\unins000.exe\" /SILENT", "C:\\Program Files\\pyRevit\\unins000.exe")]
    [InlineData("C:\\pyRevit\\unins000.exe /SILENT", "C:\\pyRevit\\unins000.exe")]
    [InlineData("C:\\pyRevit\\unins000.exe", "C:\\pyRevit\\unins000.exe")]
    [InlineData("", null)]
    [InlineData(null, null)]
    public void ExecutablePathIsExtractedFromUninstallString(string uninstallString, string expected) {
        Assert.Equal(expected, UninstallEntryMatcher.ExtractExecutablePath(uninstallString));
    }
}
