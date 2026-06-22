using System;
using System.Collections.Generic;
using System.IO;
using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Golden-file fidelity corpus: loads real-world config shapes from Fixtures/
/// and asserts read and round-trip behavior. The Acceptance_* tests pin the
/// intended string-encoding contract: string values round-trip decoded, not
/// JSON-quoted.
/// </summary>
public class GoldenFileFidelityTests
{
    private static string FixtureDir => Path.Combine(AppContext.BaseDirectory, "Fixtures");

    private static IConfiguration Load(string name) =>
        IniConfiguration.Create(Path.Combine(FixtureDir, name));

    private static string TempCopy(string name)
    {
        var dst = Path.Combine(Path.GetTempPath(), $"fidelity_{Guid.NewGuid():N}.ini");
        File.Copy(Path.Combine(FixtureDir, name), dst, true);
        return dst;
    }

    // ---- read fidelity, tolerance, and defaults ----

    [Fact]
    public void Bool_ReadsCorrectly()
    {
        var cfg = Load("populated.ini");
        Assert.True(cfg.GetValue<bool>("core", "rocketmode"));
        Assert.False(cfg.GetValue<bool>("core", "checkupdates"));
    }

    [Fact]
    public void Int_ReadsCorrectly()
    {
        var cfg = Load("populated.ini");
        Assert.Equal(10, cfg.GetValue<int>("core", "startuplogtimeout"));
    }

    [Fact]
    public void StringList_ReadsCorrectly()
    {
        var cfg = Load("populated.ini");
        var exts = cfg.GetValue<List<string>>("core", "userextensions");
        Assert.Equal(2, exts.Count);
        Assert.Equal(@"C:\Tools\ext1", exts[0]);
        Assert.Equal(@"D:\ext2", exts[1]);
    }

    [Fact]
    public void CorruptValue_DoesNotThrow_FallsBackToDefault()
    {
        var cfg = Load("corrupted_clones.ini");
        var clones = cfg.GetValueOrDefault(
            "environment", "clones", new Dictionary<string, string>());
        Assert.Empty((Dictionary<string, string>)clones!);
    }

    [Fact]
    public void CorruptFixture_OtherKeysStillReadable()
    {
        var cfg = Load("corrupted_clones.ini");
        Assert.True(cfg.GetValue<bool>("core", "rocketmode"));
    }

    [Fact]
    public void LegacyValues_DoNotThrowOnLoadOrDefaultRead()
    {
        var cfg = Load("legacy_values.ini");
        // bare/non-JSON string read back as raw (tolerated, not crashing)
        Assert.NotNull(cfg.GetValueOrDefault<string>("core", "outputstylesheet", ""));
    }

    [Fact]
    public void MissingKey_OrDefault_ReturnsDefault()
    {
        var cfg = Load("empty.ini");
        Assert.Equal("fallback", cfg.GetValueOrDefault<string>("core", "user_locale", "fallback"));
    }

    // ---- string-encoding contract ----

    [Fact] // GetValue<string> returns the decoded value, not the JSON-quoted raw string.
    public void Acceptance_GetString_ReturnsDecoded()
    {
        var cfg = Load("populated.ini");
        Assert.Equal("en_us", cfg.GetValue<string>("core", "user_locale"));
    }

    [Fact] // Writing then re-reading a string yields the same value, with no quote/escape accumulation.
    public void Acceptance_StringRoundTrip_IsIdempotent()
    {
        var path = TempCopy("populated.ini");
        try
        {
            var cfg = IniConfiguration.Create(path);
            cfg.SetValue("core", "user_locale", "fr_fr");
            cfg.SaveConfiguration();

            var reread = IniConfiguration.Create(path);
            Assert.Equal("fr_fr", reread.GetValue<string>("core", "user_locale"));
        }
        finally
        {
            File.Delete(path);
        }
    }
}
